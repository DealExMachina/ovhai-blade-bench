"""
Ensure OVH AI Deploy apps use min replicas 0 and return to STANDBY (no compute bill).

Run after tests or before leaving the desk:
  python -m bench.ensure_standby
  python -m bench.ensure_standby --wait --timeout 900
"""

from __future__ import annotations

import argparse
import os

from bench.deploy_smoke import list_apps
from bench.ovhai_cli import get_app, run_ovhai, wait_for_app_state

_ACTIVE = frozenset({"RUNNING", "SCALING", "INITIALIZING", "QUEUED", "PENDING"})


def _cooldown_for_app(app: dict) -> tuple[int, int]:
    """Return (cooldown_seconds, scale_down_window_seconds) from env or app flavor."""
    resources = app.get("spec", {}).get("resources", {})
    if resources.get("gpu"):
        cooldown = int(os.environ.get("OVHAI_VLLM_COOLDOWN_SECONDS", "120"))
        window = int(os.environ.get("OVHAI_VLLM_SCALE_DOWN_WINDOW_SECONDS", "60"))
        return cooldown, window
    cooldown = int(os.environ.get("OVHAI_IDLE_COOLDOWN_SECONDS", "300"))
    window = int(os.environ.get("OVHAI_IDLE_SCALE_DOWN_WINDOW_SECONDS", "300"))
    return cooldown, window


def apply_scale_to_zero(app_id: str, app: dict) -> None:
    cooldown, window = _cooldown_for_app(app)
    auto = app.get("spec", {}).get("scalingStrategy", {}).get("automatic", {})
    threshold = int(auto.get("averageUsageTarget", 80))
    resource = auto.get("resourceType", "CPU")
    result = run_ovhai(
        "app",
        "scale",
        app_id,
        "--auto-min-replicas",
        "0",
        "--auto-max-replicas",
        "1",
        "--auto-cooldown-period-seconds",
        str(cooldown),
        "--auto-scale-down-stabilization-window-seconds",
        str(window),
        "--auto-resource-type",
        resource,
        "--auto-resource-usage-threshold",
        str(threshold),
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise SystemExit(f"ovhai app scale failed for {app_id}: {err}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-apply scale-to-zero and optionally wait until STANDBY",
    )
    parser.add_argument(
        "--app-id",
        action="append",
        dest="app_ids",
        help="App UUID (default: all apps from ovhai app list)",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Poll until every app is STANDBY (do not send HTTP traffic meanwhile)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=900.0,
        help="Max seconds to wait per app when --wait (default 15 min)",
    )
    parser.add_argument(
        "--skip-scale",
        action="store_true",
        help="Only list/wait; do not re-run ovhai app scale",
    )
    args = parser.parse_args()

    apps = list_apps()
    if args.app_ids:
        wanted = set(args.app_ids)
        apps = [a for a in apps if a.get("id") in wanted]
        missing = wanted - {a.get("id") for a in apps}
        if missing:
            raise SystemExit(f"Unknown app id(s): {', '.join(sorted(missing))}")

    if not apps:
        print("no_apps")
        return

    for app in apps:
        app_id = app["id"]
        name = app.get("spec", {}).get("name", "")
        state = app.get("status", {}).get("state", "?")
        print(f"app id={app_id} name={name!r} state={state}")

        fresh = get_app(app_id)
        if not args.skip_scale:
            apply_scale_to_zero(app_id, fresh)
            print(f"  scale_to_zero applied (min=0, cooldown={_cooldown_for_app(fresh)[0]}s)")

        if args.wait:
            current = fresh.get("status", {}).get("state", "")
            if current == "STANDBY":
                print("  already STANDBY (no compute bill)")
                continue
            if current in _ACTIVE:
                cooldown, _ = _cooldown_for_app(fresh)
                print(
                    f"  waiting for STANDBY — no HTTP probes for ~{cooldown}s cooldown "
                    f"+ stabilization (timeout {args.timeout:.0f}s)"
                )
            wait_for_app_state(
                app_id,
                {"STANDBY"},
                timeout_seconds=args.timeout,
                poll_seconds=15.0,
            )
            print("  STANDBY reached")
        elif state in _ACTIVE:
            cooldown, _ = _cooldown_for_app(fresh)
            print(
                f"  WARNING: still {state} — avoid traffic; expect STANDBY after "
                f"~{cooldown}s idle. Re-run with --wait to poll."
            )
        elif state == "STANDBY":
            print("  STANDBY (no compute bill)")


if __name__ == "__main__":
    main()
