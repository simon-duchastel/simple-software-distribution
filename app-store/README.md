# App Store

A self-hosted, F-Droid-compatible Android app store. A small Docker image turns
a folder of APKs into a signed F-Droid repository and serves it with nginx,
plus a static, no-JavaScript web UI for browsing apps.

## Layout

```
app-store/
├── image/      # the Docker image (Dockerfile, entrypoint, web UI generator)
├── deploy/     # docker-compose deployment and runtime config
└── scripts/    # keystore setup, fingerprint printing, and APK publishing
```

## Quick start

1. Generate the repo signing keystore:

   ```bash
   ./scripts/init-keystore.sh
   ```

2. Start the service:

   ```bash
   cd deploy
   cp .env.example .env
   docker compose up -d --build
   ```

3. Publish an APK:

   ```bash
   ./scripts/add-apk.sh /path/to/my-app-1.2.0.apk
   ```

See [`deploy/README.md`](deploy/README.md) for the full NAS layout and
configuration, and [`image/README.md`](image/README.md) for the image's
environment variables.
