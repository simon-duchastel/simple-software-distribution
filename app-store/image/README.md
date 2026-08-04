# app-store image

A small Docker image that turns a folder of APKs into a signed F-Droid
repository and serves it with nginx, plus a static, no-JavaScript web UI.

`generate_site.py` renders the site. It produces a landing page
(`/`, titled **Available Software**) listing every distribution source, and one
subpage per source at `/<source>/` with setup instructions and the artifact
list. Sources are pluggable: today only the **Android** (F-Droid) source is
implemented. Add a source by creating a class with `landing_section()`,
`instructions()`, and `write(base_dir)` methods and appending it to the
`sources` list in `main()`.

## Required environment variables

The container will refuse to start unless these are set:

- `APPSTORE_REPO_URL` — public URL of the F-Droid repo.
- `APPSTORE_KEYSTORE` — path to the PKCS12 signing keystore inside the container.
- `APPSTORE_KEY_ALIAS` — alias of the signing key in the keystore.
- `APPSTORE_KEYSTORE_PASS_CMD` — shell command that prints the keystore password.
- `APPSTORE_KEY_PASS_CMD` — shell command that prints the key password.

## Optional environment variables

- `APPSTORE_REPO_NAME` — display name of the repo (default: `App Store`).
- `APPSTORE_REPO_DESCRIPTION` — short description (default: `F-Droid app store`).
- `APPSTORE_SCAN_INTERVAL` — how often to re-scan for new APKs (default: `15m`).

See `.env.example` for a concrete configuration.
