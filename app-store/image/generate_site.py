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

    sources = [AndroidSource(index, fingerprint, repo_url, repo_name)]

    with open(os.path.join(WEBUI_DIR, 'index.html'), 'w') as f:
        f.write(render_landing(sources))

    for src in sources:
        src.write(os.path.join(WEBUI_DIR, src.slug))

    write_hash()


if __name__ == '__main__':
    main()
