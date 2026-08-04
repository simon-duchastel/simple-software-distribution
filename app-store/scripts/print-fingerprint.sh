#!/usr/bin/env bash
#
# Print the SHA-256 fingerprint of the F-Droid repo signing certificate.

set -euo pipefail

KEYSTORE_DIR="${APPSTORE_SECRETS_DIR:-/mnt/bob-storage/code/binaries/android/appstore/secrets}"
KEYSTORE="$KEYSTORE_DIR/keystore.p12"
ALIAS="${APPSTORE_KEY_ALIAS:-simon-appstore}"
STOREPASS_FILE="$KEYSTORE_DIR/keystorepass"

ensure_keytool() {
    if command -v keytool >/dev/null 2>&1; then
        return
    fi
    echo "keytool not found. Installing OpenJDK..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y default-jre-headless
    else
        echo "Error: no supported package manager found. Install a JRE with keytool and re-run." >&2
        exit 1
    fi
}

ensure_keytool

if [ ! -f "$KEYSTORE" ]; then
    echo "Keystore not found at $KEYSTORE." >&2
    echo "Run scripts/init-keystore.sh first." >&2
    exit 1
fi

if [ ! -f "$STOREPASS_FILE" ]; then
    echo "Store password file not found at $STOREPASS_FILE." >&2
    exit 1
fi

storepass=$(cat "$STOREPASS_FILE")
keytool -list -v \
    -keystore "$KEYSTORE" \
    -alias "$ALIAS" \
    -storepass "$storepass" \
    | grep 'SHA256:' \
    | awk '{print $2}'
