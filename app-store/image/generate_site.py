#!/usr/bin/env python3
#
# Generate a static, no-JavaScript web UI for the software distribution site.
#
# The site has a single landing page ("Available Software") that lists every
# distribution source as a section. Each source also gets its own subpage at
# /<slug>/ with setup instructions and the full list of artifacts. Subpages
# carry a back arrow to the landing page.
#
# Sources are pluggable: each Source subclass knows how to load its data,
# render its landing-page section, and write its subpage (and any detail
# pages). Add a new source by appending to SOURCES in main().

import hashlib
import json
import os
import shutil
from html import escape

FDROID_INDEX = '/data/fdroid/repo/index-v1.json'
WEBUI_DIR = '/data/webui'
STYLE_FILE = 'style.css'
HASH_FILE = os.path.join(WEBUI_DIR, '.source_hash')

# Docker registry data root (the directory that contains registry/v2/...).
DOCKER_REGISTRY_DIR = os.environ.get('APPSTORE_DOCKER_REGISTRY_DIR', '/data/registry')
DOCKER_REGISTRY_URL = os.environ.get('APPSTORE_DOCKER_REGISTRY_URL', '').rstrip('/')

SITE_TITLE = 'Available Software'


def repo_path(filename):
    if not filename:
        return ''
    if filename.startswith('http://') or filename.startswith('https://'):
        return filename
    return f'/fdroid/repo/{filename}'


def format_bytes(n):
    if not n:
        return ''
    units = ['B', 'KB', 'MB', 'GB']
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    return f'{n:.1f} {units[i]}'


def format_date(s):
    if not s:
        return ''
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return s[:10]


def docker_repos_dir():
    return os.path.join(DOCKER_REGISTRY_DIR, 'registry', 'v2', 'repositories')


def docker_blobs_dir():
    return os.path.join(DOCKER_REGISTRY_DIR, 'registry', 'v2', 'blobs', 'sha256')


def docker_blob_path(digest):
    hexd = digest.split(':', 1)[1] if ':' in digest else digest
    return os.path.join(docker_blobs_dir(), hexd[:2], hexd, 'data')


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def docker_manifest_info(digest, seen=None):
    """Return (created, total_size) for a manifest or image-index digest."""
    if seen is None:
        seen = set()
    if digest in seen:
        return None, 0
    seen.add(digest)
    data = read_json(docker_blob_path(digest))
    if not data:
        return None, 0
    # An OCI/Docker image index lists per-platform manifests.
    if 'manifests' in data:
        created = None
        total = 0
        for m in data['manifests']:
            plat = m.get('platform', {})
            if plat.get('os') == 'unknown' and plat.get('architecture') == 'unknown':
                continue  # attestation manifest, not a real image
            c, t = docker_manifest_info(m.get('digest'), seen)
            if created is None:
                created = c
            total += t
        return created, total
    # A single image manifest references a config blob and layer blobs.
    total = 0
    cfg = data.get('config', {})
    total += cfg.get('size', 0)
    for layer in data.get('layers', []):
        total += layer.get('size', 0)
    created = None
    cfg_digest = cfg.get('digest')
    if cfg_digest:
        cfg_data = read_json(docker_blob_path(cfg_digest))
        if cfg_data:
            created = cfg_data.get('created')
    return created, total


def docker_catalog_hash():
    """Lightweight hash of published repos/tags so new pushes trigger a rebuild."""
    hasher = hashlib.sha256()
    repos_dir = docker_repos_dir()
    if not os.path.isdir(repos_dir):
        return hasher.hexdigest()
    for root, dirs, _ in os.walk(repos_dir):
        if '_manifests' in dirs:
            name = os.path.relpath(root, repos_dir)
            hasher.update(name.encode())
            hasher.update(b'\0')
            tags_dir = os.path.join(root, '_manifests', 'tags')
            if os.path.isdir(tags_dir):
                for tag in sorted(os.listdir(tags_dir)):
                    link = os.path.join(tags_dir, tag, 'current', 'link')
                    digest = ''
                    if os.path.exists(link):
                        with open(link) as f:
                            digest = f.read().strip()
                    hasher.update(f'{tag}:{digest}'.encode())
                    hasher.update(b'\0')
            dirs[:] = [d for d in dirs if d not in ('_manifests', '_layers', '_uploads')]
    return hasher.hexdigest()


def page(title, body):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
  <link rel="stylesheet" href="/{STYLE_FILE}">
</head>
<body>
{body}
</body>
</html>
'''


def back_arrow(href, label):
    return f'<a href="{escape(href)}" class="back">&larr; {escape(label)}</a>'


def source_hash():
    """Hash of every input that affects the generated site."""
    hasher = hashlib.sha256()
    for path in [FDROID_INDEX,
                 os.path.join(WEBUI_DIR, 'fingerprint.txt'),
                 '/app/style.css',
                 '/app/generate_site.py']:
        if os.path.exists(path):
            with open(path, 'rb') as f:
                hasher.update(f.read())
        hasher.update(b'\0')
    hasher.update(b'docker:')
    hasher.update(docker_catalog_hash().encode())
    return hasher.hexdigest()


def should_generate():
    current = source_hash()
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE) as f:
            previous = f.read().strip()
        if previous == current:
            print('No changes detected; skipping site generation.')
            return False
    return True


def write_hash():
    with open(HASH_FILE, 'w') as f:
        f.write(source_hash())


def load_fingerprint():
    fp_path = os.path.join(WEBUI_DIR, 'fingerprint.txt')
    if os.path.exists(fp_path):
        with open(fp_path) as f:
            return f.read().strip()
    return ''


def load_fdroid_index():
    if not os.path.exists(FDROID_INDEX):
        return None
    with open(FDROID_INDEX) as f:
        return json.load(f)


def app_name(app):
    return ((app.get('localized') or {}).get('en-US', {}).get('name')
            or app.get('name') or app.get('packageName') or '')


def app_summary(app):
    return ((app.get('localized') or {}).get('en-US', {}).get('summary')
            or app.get('summary') or '')


def render_app_cards(apps):
    if not apps:
        return '<p class="empty">No apps published yet.</p>'
    cards = '\n'.join(
        f'''<article class="card">
  <a href="/android/app/{escape(app.get('packageName', ''))}/">
    <img src="{escape(repo_path(app.get('icon')))}" alt="" width="64" height="64">
    <h3>{escape(app_name(app))}</h3>
    <p>{escape(app_summary(app))}</p>
  </a>
</article>'''
        for app in apps
    )
    return f'<div class="card-grid">\n{cards}\n</div>'


def render_app_detail(app, repo_name, repo_url):
    localized = (app.get('localized') or {}).get('en-US', {})
    name = localized.get('name') or app.get('name') or app.get('packageName')
    summary = localized.get('summary') or app.get('summary') or ''
    description = localized.get('description') or app.get('description') or ''
    package_name = app.get('packageName', '')

    versions = app.get('packages', [])
    if versions:
        version_list = '\n'.join(
            f'''<li>
  <a href="{escape(repo_path(v.get('apkName')))}" download>
    {escape(v.get('versionName', ''))} ({v.get('versionCode', '')})
  </a>
  <span class="muted">&mdash; {format_bytes(v.get('size'))}</span>
</li>'''
            for v in versions
        )
        downloads = f'<ul class="downloads">\n{version_list}\n</ul>'
    else:
        downloads = '<p class="empty">No downloads available.</p>'

    body = f'''<header>
  <h1><a href="/">{escape(SITE_TITLE)}</a></h1>
</header>
<main>
  {back_arrow('/android/', 'Android')}
  <article class="detail">
    <div class="detail-head">
      <img src="{escape(repo_path(app.get('icon')))}" alt="" width="96" height="96">
      <div>
        <h2>{escape(name)}</h2>
        <p>{escape(summary)}</p>
        <p class="meta">{escape(package_name)}</p>
      </div>
    </div>
    <pre class="description">{escape(description)}</pre>
    <h3>Downloads</h3>
    {downloads}
  </article>
</main>
<footer>
  <p>Repo URL: <code>{escape(repo_url)}</code></p>
</footer>
'''
    return page(f'{name} — {SITE_TITLE}', body)


class AndroidSource:
    """The F-Droid Android app store."""

    slug = 'android'
    title = 'Android'
    description = 'F-Droid-compatible app store built from APKs on disk.'

    def __init__(self, index, fingerprint, repo_url, repo_name):
        self.index = index
        self.fingerprint = fingerprint
        self.repo_url = repo_url
        self.repo_name = repo_name
        self.apps = []
        if index:
            packages_by_app = index.get('packages', {})
            for app in index.get('apps', []):
                package_name = app.get('packageName')
                if not package_name:
                    continue
                app['packages'] = packages_by_app.get(package_name, [])
                self.apps.append(app)

    @property
    def available(self):
        return self.index is not None

    @property
    def count(self):
        return len(self.apps)

    def landing_section(self):
        items = render_app_cards(self.apps) if self.apps else \
            '<p class="empty">No apps published yet.</p>'
        return f'''<section class="source">
  <a class="source-link" href="/{self.slug}/" aria-label="{escape(self.title)}"></a>
  <div class="source-head">
    <h2>{escape(self.title)}</h2>
    <p class="source-desc">{escape(self.description)}</p>
  </div>
  {items}
</section>'''

    def instructions(self):
        fp = self.fingerprint or '(unknown)'
        return f'''<section class="instructions">
  <h2>Setup</h2>
  <p>Add this repository to the F-Droid client on your Android device:</p>
  <ol>
    <li>Open F-Droid and go to <em>Settings &rarr; Repositories</em>.</li>
    <li>Add a new repository with this URL:
      <pre><code>{escape(self.repo_url)}</code></pre></li>
    <li>When prompted, enter the repository fingerprint:
      <pre><code class="fingerprint">{escape(fp)}</code></pre></li>
    <li>Refresh the F-Droid repository list and install apps from
      <strong>{escape(self.repo_name)}</strong>.</li>
  </ol>
</section>'''

    def write(self, base_dir):
        os.makedirs(base_dir, exist_ok=True)
        body = f'''<header>
  <h1><a href="/">{escape(SITE_TITLE)}</a></h1>
</header>
<main>
  {back_arrow('/', 'Available Software')}
  {self.instructions()}
  <h2>Apps</h2>
  {render_app_cards(self.apps)}
</main>
<footer>
  <p>Repo URL: <code>{escape(self.repo_url)}</code></p>
  <p>Fingerprint: <code>{escape(self.fingerprint) or '(unknown)'}</code></p>
</footer>
'''
        with open(os.path.join(base_dir, 'index.html'), 'w') as f:
            f.write(page(f'{self.title} — {SITE_TITLE}', body))

        for app in self.apps:
            package_name = app.get('packageName')
            if not package_name:
                continue
            app_dir = os.path.join(base_dir, 'app', package_name)
            os.makedirs(app_dir, exist_ok=True)
            with open(os.path.join(app_dir, 'index.html'), 'w') as f:
                f.write(render_app_detail(app, self.repo_name, self.repo_url))


class DockerSource:
    """Container images served from a local Docker registry."""

    slug = 'docker'
    title = 'Docker'
    description = 'Container images served from a local Docker registry.'

    def __init__(self, registry_url):
        self.registry_url = registry_url
        self.images = self._load()

    @property
    def available(self):
        return bool(self.images)

    @property
    def count(self):
        return len(self.images)

    def _load(self):
        repos_dir = docker_repos_dir()
        if not os.path.isdir(repos_dir):
            return []
        images = []
        for root, dirs, _ in os.walk(repos_dir):
            if '_manifests' not in dirs:
                continue
            name = os.path.relpath(root, repos_dir)
            tags_dir = os.path.join(root, '_manifests', 'tags')
            tags = []
            if os.path.isdir(tags_dir):
                for tag in sorted(os.listdir(tags_dir)):
                    link = os.path.join(tags_dir, tag, 'current', 'link')
                    if not os.path.exists(link):
                        continue
                    with open(link) as f:
                        digest = f.read().strip()
                    created, size = docker_manifest_info(digest)
                    tags.append({'tag': tag, 'created': created,
                                 'size': size, 'digest': digest})
            if tags:
                images.append({'name': name, 'tags': tags})
            dirs[:] = [d for d in dirs if d not in ('_manifests', '_layers', '_uploads')]
        images.sort(key=lambda i: i['name'])
        return images

    def _pull_ref(self, name, tag):
        if self.registry_url:
            return f'{self.registry_url}/{name}:{tag}'
        return f'<registry>/{name}:{tag}'

    def render_image_list(self):
        if not self.images:
            return '<p class="empty">No images published yet.</p>'
        items = []
        for img in self.images:
            tag_rows = []
            for t in img['tags']:
                meta = []
                if t['created']:
                    meta.append(format_date(t['created']))
                if t['size']:
                    meta.append(format_bytes(t['size']))
                meta_html = (f'<span class="muted">{escape(" \u00b7 ".join(meta))}</span>'
                             if meta else '')
                tag_rows.append(
                    f'<li><code>{escape(self._pull_ref(img["name"], t["tag"]))}</code>'
                    f' {meta_html}</li>')
            items.append(
                f'<article class="image">\n'
                f'  <h3>{escape(img["name"])}</h3>\n'
                f'  <ul class="tag-list">\n' + '\n'.join(tag_rows) + '\n  </ul>\n'
                f'</article>')
        return f'<div class="image-list">\n' + '\n'.join(items) + '\n</div>'

    def landing_section(self):
        return f'''<section class="source">
  <a class="source-link" href="/{self.slug}/" aria-label="{escape(self.title)}"></a>
  <div class="source-head">
    <h2>{escape(self.title)}</h2>
    <p class="source-desc">{escape(self.description)}</p>
  </div>
  {self.render_image_list()}
</section>'''

    def instructions(self):
        url = self.registry_url or '<registry>'
        return f'''<section class="instructions">
  <h2>Setup</h2>
  <p>Pull images from this registry with the Docker client:</p>
  <ol>
    <li>Log in to the registry (if it requires authentication):
      <pre><code>docker login {escape(url)}</code></pre></li>
    <li>Pull an image by its tag:
      <pre><code>docker pull {escape(url)}/&lt;image&gt;:&lt;tag&gt;</code></pre></li>
  </ol>
  <p>The registry API endpoint is <code>{escape(url)}/v2/</code>.</p>
</section>'''

    def write(self, base_dir):
        os.makedirs(base_dir, exist_ok=True)
        body = f'''<header>
  <h1><a href="/">{escape(SITE_TITLE)}</a></h1>
</header>
<main>
  {back_arrow('/', 'Available Software')}
  {self.instructions()}
  <h2>Images</h2>
  {self.render_image_list()}
</main>
'''
        with open(os.path.join(base_dir, 'index.html'), 'w') as f:
            f.write(page(f'{self.title} — {SITE_TITLE}', body))


def render_landing(sources):
    sections = '\n'.join(src.landing_section() for src in sources)
    body = f'''<header>
  <h1>{escape(SITE_TITLE)}</h1>
</header>
<main>
{sections}
</main>
'''
    return page(SITE_TITLE, body)


def main():
    os.makedirs(WEBUI_DIR, exist_ok=True)

    if not should_generate():
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    style_src = os.path.join(script_dir, STYLE_FILE)
    if os.path.exists(style_src):
        shutil.copy(style_src, os.path.join(WEBUI_DIR, STYLE_FILE))

    index = load_fdroid_index()
    repo = (index or {}).get('repo', {})
    repo_url = repo.get('address') or repo.get('url') or ''
    repo_name = repo.get('name') or 'App Store'
    fingerprint = load_fingerprint()

    sources = [AndroidSource(index, fingerprint, repo_url, repo_name),
               DockerSource(DOCKER_REGISTRY_URL)]

    with open(os.path.join(WEBUI_DIR, 'index.html'), 'w') as f:
        f.write(render_landing(sources))

    for src in sources:
        src.write(os.path.join(WEBUI_DIR, src.slug))

    write_hash()


if __name__ == '__main__':
    main()
