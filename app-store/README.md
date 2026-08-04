# App Store

A self-hosted software distribution site. A small Docker image turns a folder
of APKs into a signed F-Droid repository and serves it with nginx, plus a
static, no-JavaScript web UI.

The site has a landing page titled **Available Software** that lists every
distribution source as a section. Each source has its own subpage at
`/<source>/` with setup instructions, the artifact list, and a back arrow to
the landing page. Today the site lists the **Android** (F-Droid app store) and
**Docker** (local registry) sources; additional sources can be added by
extending `image/generate_site.py`.

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
