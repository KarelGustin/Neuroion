#!/usr/bin/env bash
#
# Automated Neuroion onboarding wizard script for CI/automation
# Runs the `neuroion onboard` wizard non-interactively and validates the resulting config file.

set -euo pipefail

# Ensure required environment variables are set
: "${API_KEY:?Environment variable API_KEY must be set}"  # API key for your chosen auth provider

# Optional: enable web search if you supply a Brave Search API key
# : "${BRAVE_API_KEY:?Environment variable BRAVE_API_KEY must be set to enable web_search}"

# Configuration defaults (override by exporting these before running the script)
MODE="${MODE:-local}"
AUTH_CHOICE="${AUTH_CHOICE:-apiKey}"
GATEWAY_PORT="${GATEWAY_PORT:-18789}"
GATEWAY_BIND="${GATEWAY_BIND:-loopback}"
DAEMON_RUNTIME="${DAEMON_RUNTIME:-node}"
INSTALL_DAEMON=true
SKIP_SKILLS=true
ACCEPT_RISK=true

# Run the Neuroion onboarding wizard non-interactively
neuroion onboard \
  --non-interactive \
  --mode "${MODE}" \
  --auth-choice "${AUTH_CHOICE}" \
  --api-key "${API_KEY}" \
  --gateway-port "${GATEWAY_PORT}" \
  --gateway-bind "${GATEWAY_BIND}" \
  --install-daemon \
  --daemon-runtime "${DAEMON_RUNTIME}" \
  $( [ "$SKIP_SKILLS" = true ] && echo "--skip-skills" ) \
  --accept-risk

# Locate the generated config file (default: ~/.neuroion/neuroion.json)
CONFIG_PATH="${NEUROION_STATE_DIR:-$HOME/.neuroion}/neuroion.json"

echo "Validating generated config at $CONFIG_PATH..."

# Validate JSON syntax using Python3 (requires a standard JSON5-to-JSON conversion if you store JSON5)
python3 - <<EOF
import json, sys
try:
    with open(r"$CONFIG_PATH") as f:
        json.load(f)
except Exception as e:
    print(f"ERROR: Failed to parse config file: {e}", file=sys.stderr)
    sys.exit(1)
EOF

echo "Config file is valid JSON and wizard completed successfully."