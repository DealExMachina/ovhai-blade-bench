"""
End-to-end OVH AI Deploy smoke test: L4 + vLLM, chat completion, wait for STANDBY.

Typical flow:
  1. Deploy (STANDBY, no GPU clock) — optional if OVHAI_VLLM_APP_ID is set
  2. HTTP request wakes the app (GPU billing starts)
  3. Poll until RUNNING, then /v1/chat/completions
  4. Poll until STANDBY (scale to zero after cooldown)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

from bench.config import ovhai_deploy_token
from bench.deploy_smoke import probe_app
from bench.ovhai_cli import get_app, parse_ovhai_json, run_ovhai, wait_for_app_state

_ROOT = Path(__file__).resolve().parents[1]


def deploy_vllm_app() -> dict:
    script = _ROOT / "deploy" / "ovh-vllm-l4-scale-zero.sh"
    if not script.is_file():
        raise SystemExit(f"Missing deploy script: {script}")
    result = subprocess.run([str(script)], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise SystemExit((result.stderr or result.stdout or "deploy failed").strip())
    return parse_ovhai_json(result.stdout)  # type: ignore[return-value]


def resolve_app_id(args: argparse.Namespace) -> tuple[str, str]:
    app_id = (args.app_id or os.environ.get("OVHAI_VLLM_APP_ID", "")).strip()
    if args.deploy or not app_id:
        print("deploy: creating vLLM app (initial state should be STANDBY)...")
        created = deploy_vllm_app()
        app_id = created["id"]
        url = created.get("status", {}).get("url", "")
        print(f"created app_id={app_id} url={url}")
        return app_id, url

    app = get_app(app_id)
    url = app.get("status", {}).get("url", "")
    return app_id, url


def wake_and_chat(
    base_url: str,
    token: str,
    prompt: str,
    *,
    app_id: str,
    wake_timeout: float,
) -> None:
    """First request may sit in queue while the GPU replica cold-starts."""
    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.monotonic() + wake_timeout
    last_error = ""
    poll_app_every = 0.0

    while time.monotonic() < deadline:
        poll_app_every += 20
        if poll_app_every >= 60:
            poll_app_every = 0.0
            state = get_app(app_id).get("status", {}).get("state", "")
            if state == "FAILED":
                info = get_app(app_id).get("status", {}).get("info", {})
                raise SystemExit(f"App entered FAILED during wake: {info}")

        try:
            with httpx.Client(timeout=120.0, headers=headers) as client:
                models = client.get(f"{base_url.rstrip('/')}/v1/models")
                if models.status_code in (502, 503, 504):
                    last_error = f"models HTTP {models.status_code}"
                    time.sleep(20)
                    continue
                models.raise_for_status()
            probe_app(base_url, token, prompt)
            return
        except httpx.HTTPError as exc:
            last_error = str(exc)
            time.sleep(20)

    raise SystemExit(f"Could not reach vLLM within {wake_timeout:.0f}s: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="OVH AI Deploy L4 vLLM smoke + scale to zero")
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Run deploy/ovh-vllm-l4-scale-zero.sh before testing",
    )
    parser.add_argument("--app-id", help="Existing app UUID (or set OVHAI_VLLM_APP_ID)")
    parser.add_argument(
        "--prompt",
        default="Reply with exactly one word: ok",
    )
    parser.add_argument(
        "--running-timeout",
        type=float,
        default=1200.0,
        help="Seconds to wait for RUNNING after wake (default 20 min)",
    )
    parser.add_argument(
        "--standby-timeout",
        type=float,
        default=600.0,
        help="Seconds to wait for STANDBY after chat (default 10 min)",
    )
    args = parser.parse_args()

    token = ovhai_deploy_token()
    app_id, url = resolve_app_id(args)
    if not url:
        raise SystemExit(f"App {app_id} has no status.url")

    initial = get_app(app_id)
    print(f"step=start state={initial.get('status', {}).get('state')} url={url}")

    print("step=wake_and_chat (first request starts the L4 replica)")
    wake_and_chat(
        url,
        token,
        args.prompt,
        app_id=app_id,
        wake_timeout=args.running_timeout,
    )

    print("step=wait_standby (scale to zero after idle cooldown)")
    final = wait_for_app_state(
        app_id,
        {"STANDBY"},
        timeout_seconds=args.standby_timeout,
        poll_seconds=15.0,
    )
    print(f"done app_id={app_id} final_state={final['status']['state']}")


if __name__ == "__main__":
    main()
