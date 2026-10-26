#!/usr/bin/env bash
# vLLM on NVIDIA L4 with scale-to-zero (min replicas 0). Starts in STANDBY until first HTTP request.
#
# OVH AI Deploy: mount rw volumes for /hub and /workspace (see OVH Llama 3 + vLLM guide).
set -eo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
set -a && source "$ROOT/.env" && set +a

: "${OVHAI_DEPLOY_TOKEN:?Set OVHAI_DEPLOY_TOKEN in .env}"

IMAGE="${OVHAI_VLLM_IMAGE:-vllm/vllm-openai:latest}"
FLAVOR="${OVHAI_VLLM_FLAVOR:-l4-1-gpu}"
MODEL="${OVHAI_VLLM_MODEL:-Qwen/Qwen2.5-1.5B-Instruct}"
NAME="${OVHAI_VLLM_APP_NAME:-ovhai-blade-vllm-l4}"
PORT="${OVHAI_VLLM_PORT:-8000}"
COOLDOWN="${OVHAI_VLLM_COOLDOWN_SECONDS:-120}"
MAX_MODEL_LEN="${OVHAI_VLLM_MAX_MODEL_LEN:-4096}"

EXTRA_ENV=(
  --env "HF_HOME=/hub"
  --env "HF_HUB_CACHE=/hub/hub"
  --env "TRANSFORMERS_CACHE=/hub/transformers"
  --env "VLLM_CACHE_ROOT=/hub/vllm"
  --env "OUTLINES_CACHE_DIR=/tmp/.outlines"
  --env "FLASHINFER_WORKSPACE_DIR=/tmp/flashinfer"
  --env "TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor"
  --env "HF_HUB_ENABLE_HF_TRANSFER=0"
  --env "HF_DATASETS_TRUST_REMOTE_CODE=1"
)
if [[ -n "${HF_TOKEN:-}" ]]; then
  EXTRA_ENV+=(--env "HF_TOKEN=${HF_TOKEN}")
fi

VOLUMES=(
  -v "standalone:/hub:rw"
  -v "standalone:/workspace:rw"
)

exec ovhai app run "$IMAGE" \
  --token "$OVHAI_DEPLOY_TOKEN" \
  --name "$NAME" \
  --flavor "$FLAVOR" \
  --gpu 1 \
  --default-http-port "$PORT" \
  --probe-path /health \
  --probe-port "$PORT" \
  --initial-delay-seconds 900 \
  --auto-min-replicas 0 \
  --auto-max-replicas 1 \
  --auto-resource-type CPU \
  --auto-resource-usage-threshold 80 \
  --auto-scale-down-stabilization-window-seconds 60 \
  --auto-cooldown-period-seconds "$COOLDOWN" \
  --label "bench=ovhai-blade-bench" \
  "${VOLUMES[@]}" \
  "${EXTRA_ENV[@]}" \
  --output json \
  -- vllm serve "${MODEL}" --host 0.0.0.0 --port "${PORT}" --trust-remote-code \
  --max-model-len "${MAX_MODEL_LEN}" \
  "$@"
