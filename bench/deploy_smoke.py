"""Verify OVH AI Deploy token and optionally probe a deployed app URL."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time

import httpx

from bench.config import ovhai_deploy_app_url, ovhai_deploy_token


def _ovhai(*args: str) -> subprocess.CompletedProcess[str]:
    binary = shutil.which("ovhai")
    if not binary:
        raise SystemExit("ovhai not found on PATH. Install from https://cli.gra.ai.cloud.ovh.net/")
    token = ovhai_deploy_token()
    cmd = [binary, *args, "--token", token]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def list_apps() -> list[dict]:
    result = _ovhai("app", "list", "--output", "json")
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise SystemExit(f"ovhai app list failed: {err}")

    raw = result.stdout.strip()
    # CLI may prepend ANSI banners; find JSON array.
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        raise SystemExit(f"Could not parse app list JSON from ovhai output:\n{raw[:500]}")
    return json.loads(raw[start : end + 1])


def probe_app(base_url: str, token: str, prompt: str) -> None:
    base = base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {token}"}

    started = time.perf_counter()
    with httpx.Client(timeout=120.0, headers=headers) as client:
        models_url = f"{base}/v1/models"
        models = client.get(models_url)
        if models.status_code == 404:
            health = client.get(f"{base}/health")
            health.raise_for_status()
            print(f"endpoint={base}")
            print("note=non-OpenAI app; /v1/models not found, /health ok")
            return

        models.raise_for_status()
        model_ids = [m["id"] for m in models.json().get("data", [])]
        if not model_ids:
            raise SystemExit(f"No models at {models_url}")
        model = model_ids[0]

        chat = client.post(
            f"{base}/v1/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 64,
            },
        )
        chat.raise_for_status()
        body = chat.json()

    elapsed_ms = (time.perf_counter() - started) * 1000
    reply = body["choices"][0]["message"]["content"]
    print(f"endpoint={base}")
    print(f"model={model}")
    print(f"latency_ms={elapsed_ms:.1f}")
    print(f"reply={reply.strip()!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="OVH AI Deploy token / app smoke test")
    parser.add_argument(
        "--list-apps",
        action="store_true",
        help="List apps visible to OVHAI_DEPLOY_TOKEN (requires operator scope)",
    )
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Call OVHAI_DEPLOY_APP_URL (OpenAI /v1/* or /health)",
    )
    parser.add_argument(
        "--prompt",
        default="Reply with exactly one word: ok",
    )
    args = parser.parse_args()

    if not args.list_apps and not args.probe:
        args.list_apps = True

    token = ovhai_deploy_token()

    if args.list_apps:
        apps = list_apps()
        print(f"app_count={len(apps)}")
        for app in apps:
            app_id = app.get("id", "?")
            name = app.get("spec", {}).get("name", "")
            state = app.get("status", {}).get("state", "?")
            url = app.get("status", {}).get("url", "")
            print(f"id={app_id} state={state} name={name!r} url={url}")

    if args.probe:
        url = ovhai_deploy_app_url()
        if not url:
            print(
                "Set OVHAI_DEPLOY_APP_URL in .env (e.g. https://<uuid>.app.gra.ai.cloud.ovh.net)",
                file=sys.stderr,
            )
            raise SystemExit(1)
        probe_app(url, token, args.prompt)


if __name__ == "__main__":
    main()
