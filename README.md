# Simple Software Distribution

A simple way to distribute your own software.

The web UI is a single static, no-JavaScript site titled **Available Software**.
It lists every distribution source on a landing page, and each source has its own
subpage with setup instructions and the full list of artifacts.

## Distributions

### [Android App Store](app-store/)

A self-hosted, F-Droid-compatible Android app store. A Docker image builds a
signed F-Droid repository from a folder of APKs and serves it with a static,
no-JavaScript web UI. Android apps are listed under the **Android** source on
the site, with F-Droid repository setup instructions on the `/android/` subpage.
