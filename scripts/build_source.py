#!/usr/bin/env python3
"""Build source.json (AltStore / SideStore / LiveContainer source) and index.html.

For every app in config/apps.json it reads the repository's GitHub releases,
downloads each release's IPA, and takes the bundle ID, version, build number,
minimum iOS and privacy permissions from the app's own Info.plist, so the
source always matches the files people actually install. Apps without a
release yet are left out. Standard library only.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import plistlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from io import BytesIO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_VERSIONS = 5
TOKEN = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')


def get(url: str, accept: str = 'application/vnd.github+json') -> bytes:
    headers = {'Accept': accept, 'User-Agent': 'ratterau-apps-source'}
    if TOKEN and url.startswith('https://api.github.com/'):
        headers['Authorization'] = f'Bearer {TOKEN}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as r:
        return r.read()


def releases(repo: str) -> list[dict]:
    try:
        data = json.loads(get(f'https://api.github.com/repos/{repo}/releases?per_page=30'))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    return [r for r in data if not r['draft'] and not r['prerelease']]


def read_ipa(data: bytes) -> dict:
    with zipfile.ZipFile(BytesIO(data)) as z:
        name = next(n for n in z.namelist()
                    if re.fullmatch(r'Payload/[^/]+\.app/Info\.plist', n))
        return plistlib.loads(z.read(name))


def plain(markdown: str) -> str:
    """Release notes in plain text for the store's 'What's new'."""
    text = markdown or ''
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'^#+\s*', '', text, flags=re.M)
    text = re.sub(r'[*_`]{1,2}([^*_`]+)[*_`]{1,2}', r'\1', text)
    text = re.sub(r'^\s*[-*]\s+', '• ', text, flags=re.M)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text[:4000]


def build_app(cfg: dict, source_cfg: dict) -> dict | None:
    repo = cfg['repo']
    versions, bundle_id, privacy = [], None, {}
    for rel in releases(repo):
        asset = next((a for a in rel['assets'] if a['name'] == cfg['asset']), None)
        if not asset:
            continue
        ipa = get(asset['browser_download_url'], accept='application/octet-stream')
        info = read_ipa(ipa)
        bid = info['CFBundleIdentifier']
        if bundle_id is None:
            bundle_id = bid
            privacy = {k: v for k, v in info.items()
                       if k.startswith('NS') and k.endswith('UsageDescription')}
        elif bid != bundle_id:
            print(f'  skipping {rel["tag_name"]}: different bundle ID {bid}', file=sys.stderr)
            continue
        versions.append({
            'version': info.get('CFBundleShortVersionString', rel['tag_name'].lstrip('v')),
            'buildVersion': str(info.get('CFBundleVersion', '1')),
            'date': rel['published_at'],
            'localizedDescription': plain(rel.get('body') or '') or f'{cfg["name"]} {rel["tag_name"]}',
            'downloadURL': asset['browser_download_url'],
            'size': asset['size'],
            'sha256': hashlib.sha256(ipa).hexdigest(),
            'minOSVersion': info.get('MinimumOSVersion', '15.0'),
        })
        print(f'  {cfg["name"]} {versions[-1]["version"]} ({versions[-1]["buildVersion"]})', file=sys.stderr)
        if len(versions) >= MAX_VERSIONS:
            break
    if not versions:
        print(f'  {cfg["name"]}: no release with {cfg["asset"]} yet, left out', file=sys.stderr)
        return None

    raw = f'https://raw.githubusercontent.com/{repo}/main/'
    site = source_cfg['website']
    latest = versions[0]
    return {
        'name': cfg['name'],
        'bundleIdentifier': bundle_id,
        'developerName': 'RatterAU',
        'subtitle': cfg['subtitle'],
        'localizedDescription': cfg['description'],
        'iconURL': site + cfg['icon'],
        'tintColor': cfg['tintColor'],
        'category': cfg.get('category', 'other'),
        'screenshots': [raw + s for s in cfg.get('screenshots', [])],
        'versions': versions,
        'appPermissions': {'entitlements': [], 'privacy': privacy},
        # Older SideStore / AltStore versions read these instead of `versions`
        'version': latest['version'],
        'versionDate': latest['date'],
        'versionDescription': latest['localizedDescription'],
        'downloadURL': latest['downloadURL'],
        'size': latest['size'],
        # Not part of the AltStore format; used by the landing page
        '_repo': repo,
    }


def build() -> dict:
    with open(os.path.join(ROOT, 'config', 'apps.json')) as f:
        cfg = json.load(f)
    s = cfg['source']
    apps = [a for a in (build_app(c, s) for c in cfg['apps']) if a]
    return {
        'name': s['name'],
        'identifier': s['identifier'],
        'subtitle': s['subtitle'],
        'description': s['description'],
        'iconURL': s['iconURL'],
        'website': s['website'],
        'tintColor': s['tintColor'],
        'sourceURL': s['url'],
        'featuredApps': [a['bundleIdentifier'] for a in apps],
        'apps': apps,
        'news': [],
    }


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RatterAU's Apps</title>
<meta name="description" content="Install my apps with LiveContainer, SideStore or AltStore.">
<style>
:root {{ --bg:#F2F2F7; --card:#FFFFFF; --text:#1C1C1E; --dim:#6C6C70; --line:rgba(60,60,67,.14); --accent:#0A84FF; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#000; --card:#1C1C1E; --text:#F2F2F7; --dim:#98989F; --line:rgba(235,235,245,.12); }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font:16px/1.45 -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif; -webkit-font-smoothing:antialiased; }}
main {{ max-width:720px; margin:0 auto; padding:40px 16px 64px; }}
h1 {{ font-size:34px; line-height:1.1; margin:0 0 6px; letter-spacing:-.02em; }}
.lede {{ color:var(--dim); margin:0 0 28px; }}
.card {{ background:var(--card); border-radius:18px; padding:18px; margin-bottom:14px; }}
.add h2 {{ font-size:13px; text-transform:uppercase; letter-spacing:.06em; color:var(--dim); margin:0 0 12px; font-weight:600; }}
.btn {{ display:flex; align-items:center; justify-content:space-between; gap:12px; text-decoration:none; color:var(--text); padding:14px 0; border-top:1px solid var(--line); }}
.btn:first-of-type {{ border-top:0; padding-top:4px; }}
.btn b {{ display:block; font-weight:600; }}
.btn span {{ color:var(--dim); font-size:14px; }}
.btn i {{ font-style:normal; color:var(--accent); font-weight:600; white-space:nowrap; }}
.rec {{ display:inline-block; font-size:12px; font-weight:600; color:#1F7A4D; background:rgba(48,209,88,.16); border-radius:6px; padding:1px 6px; margin-left:6px; vertical-align:2px; }}
.url {{ display:flex; gap:8px; margin-top:14px; }}
.url code {{ flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; background:var(--bg); border-radius:10px; padding:10px 12px; font:13px ui-monospace, SFMono-Regular, Menlo, monospace; }}
.url button {{ border:0; border-radius:10px; padding:0 14px; background:var(--accent); color:#fff; font:600 14px -apple-system, sans-serif; cursor:pointer; }}
.app {{ display:flex; gap:14px; align-items:flex-start; }}
.app img {{ width:64px; height:64px; border-radius:15px; flex:none; box-shadow:0 0 0 1px var(--line); }}
.app h3 {{ margin:0; font-size:19px; }}
.app p {{ margin:2px 0 0; color:var(--dim); font-size:15px; }}
.meta {{ font-size:13px; color:var(--dim); margin-top:8px; }}
.meta a {{ color:var(--accent); text-decoration:none; }}
.note {{ font-size:14px; color:var(--dim); margin:22px 4px 0; }}
.note b {{ color:var(--text); }}
</style>
</head>
<body>
<main>
<h1>RatterAU's Apps</h1>
<p class="lede">Free iPhone apps with no ads, no accounts and no tracking. Add this source once and you can install and update all of them from your phone.</p>

<section class="card add">
<h2>Add the source</h2>
<a class="btn" href="livecontainer://source?url={u}"><div><b>LiveContainer <span class="rec">Recommended</span></b><span>Apps run inside LiveContainer and don't count towards the 3-app limit</span></div><i>Add&nbsp;›</i></a>
<a class="btn" href="sidestore://source?url={u}"><div><b>SideStore</b><span>Each app uses one of your 3 app slots</span></div><i>Add&nbsp;›</i></a>
<a class="btn" href="altstore://source?url={u}"><div><b>AltStore</b><span>Each app uses one of your 3 app slots</span></div><i>Add&nbsp;›</i></a>
<div class="url"><code id="u">{url}</code><button onclick="navigator.clipboard.writeText(document.getElementById('u').textContent).then(()=>{{this.textContent='Copied'}})">Copy</button></div>
</section>

{cards}

<p class="note"><b>Using LiveContainer + SideStore?</b> Add the source in <b>LiveContainer's Sources tab</b>, not in SideStore. Apps installed from SideStore are installed as normal apps and use up your app slots.</p>
<p class="note">Every app is built from its public GitHub repository, and every download comes straight from that repository's releases. This page and the source are rebuilt automatically from those releases.</p>
</main>
</body>
</html>
"""

CARD = """<section class="card app">
<img src="{icon}" alt="">
<div>
<h3>{name}</h3>
<p>{subtitle}</p>
<div class="meta">Version {version} · {size} · iOS {minos}+ · <a href="https://github.com/{repo}">Source &amp; guide</a></div>
</div>
</section>"""


def write(source: dict) -> None:
    public = {**source, 'apps': [{k: v for k, v in a.items() if not k.startswith('_')}
                                 for a in source['apps']]}
    with open(os.path.join(ROOT, 'source.json'), 'w') as f:
        json.dump(public, f, indent=2, ensure_ascii=False)
        f.write('\n')
    cards = '\n'.join(CARD.format(
        icon=html.escape(a['iconURL']), name=html.escape(a['name']),
        subtitle=html.escape(a['subtitle']), version=html.escape(a['version']),
        size=f'{a["size"] / 1e6:.1f} MB', minos=html.escape(a['versions'][0]['minOSVersion']),
        repo=html.escape(a['_repo'])) for a in source['apps'])
    url = source['sourceURL']
    with open(os.path.join(ROOT, 'index.html'), 'w') as f:
        f.write(PAGE.format(u=urllib.parse.quote(url, safe=''), url=html.escape(url), cards=cards))


if __name__ == '__main__':
    write(build())
    print('wrote source.json and index.html', file=sys.stderr)
