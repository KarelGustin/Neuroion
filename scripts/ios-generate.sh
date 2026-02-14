#!/usr/bin/env bash
# Generate Neuroion.xcodeproj from ios/project.yml.
# Uses xcodegen if available, otherwise mint run yonaskolb/XcodeGen (requires: brew install mint).
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT/ios"

if command -v xcodegen >/dev/null 2>&1; then
  xcodegen generate
elif command -v mint >/dev/null 2>&1; then
  mint run yonaskolb/XcodeGen xcodegen generate
else
  echo ""
  echo "XcodeGen is required to generate the iOS project. Install one of:"
  echo "  brew install xcodegen"
  echo "  brew install mint   # then run again (Mint will fetch XcodeGen)"
  echo ""
  exit 1
fi
