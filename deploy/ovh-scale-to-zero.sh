#!/usr/bin/env bash
# Deploy an AI Deploy app that stays at 0 replicas until the first HTTP request (STANDBY).
# Billing: no GPU/CPU while status is STANDBY; pay per minute only during SCALING/RUNNING.
#
# Requires: ovhai on PATH, OVHAI_DEPLOY_TOKEN in .env (or environment).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
set -a && source "$ROOT/.env" && set +a

: "${OVHAI_DEPLOY_TOKEN:?Set OVHAI_DEPLOY_TOKEN in .env}"

IMAGE="${OVHAI_DEPLOY_IMAGE:-ovhcom/ai-deploy-hello-world}"
NAME="${OVHAI_DEPLOY_NAME:-ovhai-blade-bench-idle}"

exec ovhai app run "$IMAGE" \
  --token "$OVHAI_DEPLOY_TOKEN" \
  --name "$NAME" \
  --cpu 1 \
  --default-http-port 8080 \
  --auto-min-replicas 0 \
  --auto-max-replicas 1 \
  --auto-resource-type CPU \
  --auto-resource-usage-threshold 50 \
  --auto-scale-down-stabilization-window-seconds 300 \
  --auto-cooldown-period-seconds 300 \
  --label "bench=ovhai-blade-bench" \
  --output json \
  "$@"
