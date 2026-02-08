#!/usr/bin/env bash
set -euo pipefail

cd /repo

export NEUROION_STATE_DIR="/tmp/neuroion-test"
export NEUROION_CONFIG_PATH="${NEUROION_STATE_DIR}/neuroion.json"

echo "==> Build"
pnpm build

echo "==> Seed state"
mkdir -p "${NEUROION_STATE_DIR}/credentials"
mkdir -p "${NEUROION_STATE_DIR}/agents/main/sessions"
echo '{}' >"${NEUROION_CONFIG_PATH}"
echo 'creds' >"${NEUROION_STATE_DIR}/credentials/marker.txt"
echo 'session' >"${NEUROION_STATE_DIR}/agents/main/sessions/sessions.json"

echo "==> Reset (config+creds+sessions)"
pnpm neuroion reset --scope config+creds+sessions --yes --non-interactive

test ! -f "${NEUROION_CONFIG_PATH}"
test ! -d "${NEUROION_STATE_DIR}/credentials"
test ! -d "${NEUROION_STATE_DIR}/agents/main/sessions"

echo "==> Recreate minimal config"
mkdir -p "${NEUROION_STATE_DIR}/credentials"
echo '{}' >"${NEUROION_CONFIG_PATH}"

echo "==> Uninstall (state only)"
pnpm neuroion uninstall --state --yes --non-interactive

test ! -d "${NEUROION_STATE_DIR}"

echo "OK"
