# App Store deploy

Compose deployment for the [app-store image](../image). It builds a signed
F-Droid repository from APKs on disk and serves it over HTTP.

## NAS layout

APKs, metadata, and signing secrets are kept on the NAS under
`/mnt/bob-storage/code/binaries/android/` by default:

```
/mnt/bob-storage/code/binaries/android/
├── apks/
│   └── <package-name>/
│       └── <version-code>/
│           └── <artifact>.apk
├── appstore/
│   ├── metadata/
│   │   └── <package-name>.yml
│   └── secrets/
│       ├── keystore.p12
│       ├── keystorepass
│       └── keypass
```

- `apks/` — drop APKs here, organized by package and version code.
- `appstore/metadata/` — optional F-Droid metadata YAML files per app.
- `appstore/secrets/` — F-Droid repo signing keystore and passwords.

All host paths are configurable via the `APK_DIR`, `METADATA_DIR`,
`SECRETS_DIR`, and `FDROID_DATA_DIR` environment variables (see
`.env.example`).

## First-time setup

1. Generate the repo signing keystore:

   ```bash
   ./scripts/init-keystore.sh
   ```

2. Print the fingerprint:

   ```bash
   ./scripts/print-fingerprint.sh
   ```

3. Start the service:

   ```bash
   cd deploy
   cp .env.example .env
   # edit .env if needed
   docker compose up -d --build
   ```

## Publishing a new APK

```bash
./scripts/add-apk.sh /path/to/my-app-1.2.0.apk
```

Then wait for the next scan interval or restart the container.

## App metadata

Create a YAML file in
`/mnt/bob-storage/code/binaries/android/appstore/metadata/<package-name>.yml`
to override names, summaries, descriptions, and icons. See the [F-Droid Build
Metadata Reference](https://f-droid.org/docs/Build_Metadata_Reference/) for
supported fields. If no metadata file is provided, `fdroid update` builds a
skeleton from the APK itself.
