#!/usr/bin/env bash
# Copies the repo's Info.plist (with CFBundleIdentifier and required keys) into
# your Xcode project folder. Use this if you build from a project outside this
# repo (e.g. on Desktop) and get "not a valid bundle" / CFBundleIdentifier missing.
#
# Usage (from repo root):
#   bash ios/scripts/copy-info-plist.sh "/path/to/your/Neuroion One"
#
# The path must be the folder that contains the NeuroionApp directory (your
# Xcode project root, e.g. the "Neuroion One" folder).

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_IOS="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST_SRC="$REPO_IOS/NeuroionApp/Info.plist"
DEST_DIR="${1:-}"

if [[ -z "$DEST_DIR" || ! -d "$DEST_DIR" ]]; then
  echo "Usage: bash ios/scripts/copy-info-plist.sh \"/path/to/your/Neuroion One\""
  echo "The path must be the folder that contains the NeuroionApp directory."
  exit 1
fi

DEST_PLIST="$DEST_DIR/NeuroionApp/Info.plist"
if [[ ! -d "$DEST_DIR/NeuroionApp" ]]; then
  echo "Error: $DEST_DIR/NeuroionApp not found. Pass the folder that contains NeuroionApp."
  exit 1
fi

if [[ ! -f "$PLIST_SRC" ]]; then
  echo "Error: Source plist not found: $PLIST_SRC"
  exit 1
fi

cp "$PLIST_SRC" "$DEST_PLIST"
echo "Copied Info.plist to $DEST_PLIST"
echo "In Xcode: Product → Clean Build Folder, then build and run on device."
