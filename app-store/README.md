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
└── scripts/    # keystore setup, fingerprint printing, and APK publishing
```

Deployment wiring (docker-compose, runtime environment) lives outside this
repository. See [`image/README.md`](image/README.md) for the image's required
and optional environment variables, then run the image with those variables
set and the APK, metadata, secrets, and F-Droid data directories mounted.

## Quick start

1. Generate the repo signing keystore:

   ```bash
   ./scripts/init-keystore.sh
   ```

2. Build and run the image, mounting your APKs, metadata, secrets, and
   F-Droid data, and setting the environment variables from
   [`image/README.md`](image/README.md).

3. Publish an APK:

   ```bash
   ./scripts/add-apk.sh /path/to/my-app-1.2.0.apk
   ```
