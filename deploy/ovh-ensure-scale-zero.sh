#!/usr/bin/env bash
# Re-apply min replicas 0 and wait until all listed apps are STANDBY (no GPU/CPU bill).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/.venv/bin/python" -m bench.ensure_standby --wait "$@"
