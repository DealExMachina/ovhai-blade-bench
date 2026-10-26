"""Thin wrapper around the ovhai CLI (JSON parsing, app polling)."""

from __future__ import annotations

import json
import shutil
import subprocess
import time

from bench.config import ovhai_deploy_token


def run_ovhai(*args: str) -> subprocess.CompletedProcess[str]:
    binary = shutil.which("ovhai")
    if not binary:
        raise SystemExit("ovhai not found on PATH. Install from https://cli.gra.ai.cloud.ovh.net/")
    token = ovhai_deploy_token()
    return subprocess.run(
        [binary, *args, "--token", token],
        capture_output=True,
        text=True,
        check=False,
    )


def parse_ovhai_json(raw: str) -> dict | list:
    stripped = raw.strip()
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(stripped):
        if ch not in "{[":
            continue
        try:
            value, _end = decoder.raw_decode(stripped[idx:])
            return value
        except json.JSONDecodeError:
            continue
    raise SystemExit(f"Could not parse ovhai JSON:\n{stripped[:800]}")


def get_app(app_id: str) -> dict:
    result = run_ovhai("app", "get", app_id, "--output", "json")
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise SystemExit(f"ovhai app get failed: {err}")
    payload = parse_ovhai_json(result.stdout)
    if isinstance(payload, list):
        if not payload:
            raise SystemExit("ovhai app get returned empty list")
        payload = payload[0]
    return payload


def wait_for_app_state(
    app_id: str,
    target_states: set[str],
    *,
    timeout_seconds: float,
    poll_seconds: float = 15.0,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last: dict | None = None
    while time.monotonic() < deadline:
        last = get_app(app_id)
        state = last.get("status", {}).get("state", "")
        print(f"poll app_id={app_id} state={state}")
        if state in target_states:
            return last
        time.sleep(poll_seconds)
    state = (last or {}).get("status", {}).get("state", "?")
    raise SystemExit(
        f"Timed out after {timeout_seconds:.0f}s waiting for {sorted(target_states)}; last state={state}"
    )
