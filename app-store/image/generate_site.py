#!/usr/bin/env python3
#
# Generate a static, no-JavaScript web UI from the F-Droid index-v1.json file.

import hashlib
import json
import os
import shutil
from html import escape

REPO_INDEX = '/data/fdroid/repo/index-v1.json'
WEBUI_DIR = '/data/webui'
STYLE_FILE = 'style.css'
HASH_FILE = os.path.join(WEBUI_DIR, '.source_hash')


def repo_path(filename):
    if not filename:
        return ''
    if filename.startswith('http://') or filename.startswith('https://'):
        return filename
    return f'/fdroid/repo/{filename}'


def source_hash():
    hasher = hashlib.sha256()
    for path in [REPO_INDEX, os.path.join(WEBUI_DIR, 'fingerprint.txt'), '/app/style.css', '/app/generate_site.py']:
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


def render_index(data):
    apps = data.get('apps', [])
    repo = data.get('repo', {})
    repo_url = repo.get('address') or repo.get('url') or ''
    repo_name = repo.get('name') or 'App Store'
    repo_description = repo.get('description') or 'F-Droid app store'

    fingerprint = ''
    fp_path = os.path.join(WEBUI_DIR, 'fingerprint.txt')
    if os.path.exists(fp_path):
        with open(fp_path) as f:
            fingerprint = f.read().strip()

    if apps:
        cards = '\n'.join(
            f'''<article class="app-card">
  <a href="/app/{escape(app.get('packageName', ''))}/">
    <img src="{escape(repo_path(app.get('icon')))}" alt="" width="64" height="64">
    <h2>{escape((app.get('localized') or {}).get('en-US', {}).get('name') or app.get('name') or app.get('packageName'))}</h2>
    <p>{escape((app.get('localized') or {}).get('en-US', {}).get('summary') or app.get('summary') or '')}</p>
  </a>
</article>'''
            for app in apps
        )
        grid = f'<section class="app-grid">\n{cards}\n</section>'
    else:
        grid = '<p class="empty">No apps published yet. Drop an APK in the NAS apks folder.</p>'

    body = f'''<header>
  <h1>{escape(repo_name)}</h1>
  <p>{escape(repo_description)}</p>
</header>
<main>
{grid}
</main>
<footer>
  <p>Repo URL: <code>{escape(repo_url)}</code></p>
  <p>Fingerprint: <code>{escape(fingerprint) or '(unknown)'}</code></p>
</footer>
'''
    return page(repo_name, body)


def render_app(app, repo_name='App Store'):
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
  <span>— {format_bytes(v.get('size'))}</span>
</li>'''
            for v in versions
        )
        downloads = f'<ul>\n{version_list}\n</ul>'
    else:
        downloads = '<p>No downloads available.</p>'

    body = f'''<header>
  <h1><a href="/">{escape(repo_name)}</a></h1>
</header>
<main>
  <a href="/" class="back">← Back to apps</a>
  <article class="detail">
    <div class="detail-header">
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
'''
    return page(f'{name} — {repo_name}', body)


def main():
    os.makedirs(WEBUI_DIR, exist_ok=True)

    with open(REPO_INDEX) as f:
        data = json.load(f)

    if not should_generate():
        return

    repo_name = data.get('repo', {}).get('name') or 'App Store'

    script_dir = os.path.dirname(os.path.abspath(__file__))
    style_src = os.path.join(script_dir, STYLE_FILE)
    if os.path.exists(style_src):
        shutil.copy(style_src, os.path.join(WEBUI_DIR, STYLE_FILE))

    with open(os.path.join(WEBUI_DIR, 'index.html'), 'w') as f:
        f.write(render_index(data))

    packages_by_app = data.get('packages', {})
    for app in data.get('apps', []):
        package_name = app.get('packageName')
        if not package_name:
            continue
        app['packages'] = packages_by_app.get(package_name, [])
        app_dir = os.path.join(WEBUI_DIR, 'app', package_name)
        os.makedirs(app_dir, exist_ok=True)
        with open(os.path.join(app_dir, 'index.html'), 'w') as f:
            f.write(render_app(app, repo_name))

    write_hash()


if __name__ == '__main__':
    main()
