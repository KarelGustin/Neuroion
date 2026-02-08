#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${NEUROION_IMAGE:-${NEUROIONBOT_IMAGE:-neuroion:local}}"
CONFIG_DIR="${NEUROION_CONFIG_DIR:-${NEUROIONBOT_CONFIG_DIR:-$HOME/.neuroion}}"
WORKSPACE_DIR="${NEUROION_WORKSPACE_DIR:-${NEUROIONBOT_WORKSPACE_DIR:-$HOME/.neuroion/workspace}}"
PROFILE_FILE="${NEUROION_PROFILE_FILE:-${NEUROIONBOT_PROFILE_FILE:-$HOME/.profile}}"

PROFILE_MOUNT=()
if [[ -f "$PROFILE_FILE" ]]; then
  PROFILE_MOUNT=(-v "$PROFILE_FILE":/home/node/.profile:ro)
fi

echo "==> Build image: $IMAGE_NAME"
docker build -t "$IMAGE_NAME" -f "$ROOT_DIR/Dockerfile" "$ROOT_DIR"

echo "==> Run live model tests (profile keys)"
docker run --rm -t \
  --entrypoint bash \
  -e COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
  -e HOME=/home/node \
  -e NODE_OPTIONS=--disable-warning=ExperimentalWarning \
  -e NEUROION_LIVE_TEST=1 \
  -e NEUROION_LIVE_MODELS="${NEUROION_LIVE_MODELS:-${NEUROIONBOT_LIVE_MODELS:-all}}" \
  -e NEUROION_LIVE_PROVIDERS="${NEUROION_LIVE_PROVIDERS:-${NEUROIONBOT_LIVE_PROVIDERS:-}}" \
  -e NEUROION_LIVE_MODEL_TIMEOUT_MS="${NEUROION_LIVE_MODEL_TIMEOUT_MS:-${NEUROIONBOT_LIVE_MODEL_TIMEOUT_MS:-}}" \
  -e NEUROION_LIVE_REQUIRE_PROFILE_KEYS="${NEUROION_LIVE_REQUIRE_PROFILE_KEYS:-${NEUROIONBOT_LIVE_REQUIRE_PROFILE_KEYS:-}}" \
  -v "$CONFIG_DIR":/home/node/.neuroion \
  -v "$WORKSPACE_DIR":/home/node/.neuroion/workspace \
  "${PROFILE_MOUNT[@]}" \
  "$IMAGE_NAME" \
  -lc "set -euo pipefail; [ -f \"$HOME/.profile\" ] && source \"$HOME/.profile\" || true; cd /app && pnpm test:live"
