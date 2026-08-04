#!/bin/bash
#
# Build and serve a signed F-Droid repo from APKs stored on the NAS.

set -euo pipefail

REPO_DIR="/data/fdroid"
APKS_DIR="/data/apks"
METADATA_SRC="/data/metadata"
METADATA_DIR="$REPO_DIR/metadata"
WEBUI_DIR="/data/webui"

APPSTORE_REPO_URL="${APPSTORE_REPO_URL:-}"
APPSTORE_REPO_NAME="${APPSTORE_REPO_NAME:-App Store}"
APPSTORE_REPO_DESCRIPTION="${APPSTORE_REPO_DESCRIPTION:-F-Droid app store}"
APPSTORE_KEY_ALIAS="${APPSTORE_KEY_ALIAS:-}"
APPSTORE_KEYSTORE="${APPSTORE_KEYSTORE:-}"
APPSTORE_KEYSTORE_PASS_CMD="${APPSTORE_KEYSTORE_PASS_CMD:-}"
APPSTORE_KEY_PASS_CMD="${APPSTORE_KEY_PASS_CMD:-}"
APPSTORE_SCAN_INTERVAL="${APPSTORE_SCAN_INTERVAL:-15m}"

require_env() {
    local var_name="$1"
    local value="${!var_name:-}"
    if [ -z "$value" ]; then
        echo "Error: $var_name must be set." >&2
        exit 1
    fi
}

require_env APPSTORE_REPO_URL
require_env APPSTORE_KEYSTORE
require_env APPSTORE_KEY_ALIAS
require_env APPSTORE_KEYSTORE_PASS_CMD
require_env APPSTORE_KEY_PASS_CMD

mkdir -p "$REPO_DIR" "$METADATA_DIR" "$REPO_DIR/repo" "$WEBUI_DIR"

keystorepass=$(bash -c "$APPSTORE_KEYSTORE_PASS_CMD")
keypass=$(bash -c "$APPSTORE_KEY_PASS_CMD")

cat > "$REPO_DIR/config.yml" <<EOF
repo_url: $APPSTORE_REPO_URL
repo_name: $APPSTORE_REPO_NAME
repo_description: $APPSTORE_REPO_DESCRIPTION
repo_keyalias: $APPSTORE_KEY_ALIAS
keystore: $APPSTORE_KEYSTORE
keystorepass: $keystorepass
keypass: $keypass
EOF
chmod 600 "$REPO_DIR/config.yml"

generate_site() {
    python3 /app/generate_site.py
}

write_fingerprint() {
    keytool -list -v \
        -keystore "$APPSTORE_KEYSTORE" \
        -alias "$APPSTORE_KEY_ALIAS" \
        -storepass "$keystorepass" \
        | grep 'SHA256:' \
        | awk '{print $2}' > "$WEBUI_DIR/fingerprint.txt"
}

update_repo() {
    # Clear the fdroid APK cache so that removed, renamed, or previously
    # broken APKs are always rescanned instead of silently reused.
    rm -f "$REPO_DIR/tmp/apkcache.json"

    if [ -d "$METADATA_SRC" ] && [ -n "$(ls -A "$METADATA_SRC" 2>/dev/null)" ]; then
        cp -r "$METADATA_SRC"/* "$METADATA_DIR/"
    fi

    while IFS= read -r -d '' apk; do
        rel="${apk#$APKS_DIR/}"
        name="${rel//\//_}"
        name="${name#_}"
        ln -sf "$apk" "$REPO_DIR/repo/$name"
    done < <(find "$APKS_DIR" -type f -name '*.apk' -print0)

    find -L "$REPO_DIR/repo" -maxdepth 1 -type l -name '*.apk' -delete

    (cd "$REPO_DIR" && fdroid update --create-metadata)
}

update_repo
write_fingerprint
generate_site
nginx -c /app/nginx.conf

while true; do
    sleep "$APPSTORE_SCAN_INTERVAL"
    update_repo
    write_fingerprint
    generate_site
done
