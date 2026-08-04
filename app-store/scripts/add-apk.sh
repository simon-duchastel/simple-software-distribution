#!/usr/bin/env bash
#
# Copy a new APK into the NAS appstore folder and trigger a repo rebuild.

set -euo pipefail

APK_PATH="${1:-}"
if [ -z "$APK_PATH" ]; then
    echo "Usage: $0 <path-to.apk>" >&2
    exit 1
fi

if [ ! -f "$APK_PATH" ]; then
    echo "APK not found: $APK_PATH" >&2
    exit 1
fi

DEST_DIR="${APK_DIR:-/mnt/bob-storage/code/binaries/android/apks}"
mkdir -p "$DEST_DIR"

cp "$APK_PATH" "$DEST_DIR/"
echo "Copied $(basename "$APK_PATH") to $DEST_DIR"
echo "Restart the appstore container to publish the new APK."
