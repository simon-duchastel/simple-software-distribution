#!/usr/bin/env bash
#
# Generate the F-Droid repo signing keystore on the NAS.
# Run once before starting the appstore container.

set -euo pipefail

KEYSTORE_DIR="${APPSTORE_SECRETS_DIR:-/mnt/bob-storage/code/binaries/android/appstore/secrets}"
KEYSTORE="$KEYSTORE_DIR/keystore.p12"
ALIAS="${APPSTORE_KEY_ALIAS:-simon-appstore}"
DNAME="${APPSTORE_DNAME:-CN=Simon Duchastel, O=Simon Duchastel}"
STOREPASS_FILE="$KEYSTORE_DIR/keystorepass"
KEYPASS_FILE="$KEYSTORE_DIR/keypass"

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

mkdir -p "$KEYSTORE_DIR"
chmod 700 "$KEYSTORE_DIR"

if [ -f "$KEYSTORE" ]; then
    echo "Keystore already exists at $KEYSTORE"
    echo "Run scripts/print-fingerprint.sh to view its fingerprint."
    exit 0
fi

pass=$(openssl rand -hex 32)
printf '%s' "$pass" > "$STOREPASS_FILE"
chmod 600 "$STOREPASS_FILE"
printf '%s' "$pass" > "$KEYPASS_FILE"
chmod 600 "$KEYPASS_FILE"

keytool -genkey -v \
    -keystore "$KEYSTORE" \
    -alias "$ALIAS" \
    -keyalg RSA \
    -keysize 4096 \
    -sigalg SHA256withRSA \
    -validity 10000 \
    -storetype PKCS12 \
    -dname "$DNAME" \
    -storepass "$(cat "$STOREPASS_FILE")" \
    -keypass "$(cat "$KEYPASS_FILE")"

chmod 600 "$KEYSTORE"

echo "Keystore created: $KEYSTORE"
echo "Run scripts/print-fingerprint.sh to view its fingerprint."
