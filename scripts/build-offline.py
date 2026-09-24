#!/usr/bin/env python3
"""Import a pinned copy once; rebuild the complete, single-file app offline."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'mike-stack1982364/Ontological-Worlds'
COMMIT = 'f34066d0b7466f7477f9d077cff72cbb27a9e47e'
FILES = (
    'extra-training.html', 'extra-training-runtime.js', 'number-speech.js',
    'number-speech-data.js', 'NUMBER-SPEECH-ASSETS.md',
    'assets/number-voice/LICENSE.txt', 'assets/number-voice/CREDITS.txt',
    'assets/number-voice/source.json', 'scripts/build-number-speech.py',
)
KNOWN = {
    'extra-training.html': 'f759bcea052ad41e7930f794905b1dd204b06c71',
    'extra-training-runtime.js': 'f83c9a80959422d194bd6f3104e5213352ee1a3a',
    'number-speech.js': '2e0c45acd8e888efb45fe474f9dcbc746d2d69a4',
    'number-speech-data.js': '7ad10b714d92b4a0435055ed061efb6a974b0760',
}


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={'User-Agent': 'dream-unity-n-back-import'})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read(12_000_001)
    if len(data) > 12_000_000:
        raise ValueError('Unexpectedly large source asset')
    return data


def import_source() -> None:
    tree = json.loads(get(f'https://api.github.com/repos/{SOURCE}/git/trees/{COMMIT}?recursive=1'))
    if tree.get('truncated'):
        raise ValueError('Source tree is truncated')
    entries = {entry['path']: entry for entry in tree['tree'] if entry['type'] == 'blob'}
    manifest = {'repository': SOURCE, 'commit': COMMIT, 'files': {}}
    # Read only explicitly selected training files. Never modify the source repo.
    for name in FILES:
        entry = entries[name]
        if name in KNOWN and entry['sha'] != KNOWN[name]:
            raise ValueError(f'Unexpected source version: {name}')
        data = get(f'https://raw.githubusercontent.com/{SOURCE}/{COMMIT}/{name}')
        if blob_sha(data) != entry['sha']:
            raise ValueError(f'Source hash mismatch: {name}')
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        manifest['files'][name] = {'git_blob_sha': entry['sha'], 'bytes': len(data)}
    (ROOT / 'SOURCE.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


MENU = '''
<main id="training-menu" class="container">
<header><div><p class="brand">DREAM UNITY · N-BACK</p><h1 id="menu-title">Extra Training</h1></div></header>
<section class="controls menu-card">
<a id="open-training" class="training-portal" href="#training"><span>Open ordered<br>number n-back</span><span aria-hidden="true">›</span></a>
<p class="menu-note">The complete Ordered Number N-back trainer from Ontological Worlds, in an independent, offline application.</p>
<p class="help">All training code and recorded number audio are embedded in this file. No internet connection, account or installation is required to play.</p>
</section>
<section class="controls guide" aria-labelledby="guide-title">
<h2 id="guide-title">How to play</h2>
<p>Remember each ordered sequence of 1–3 digits. Select <strong>Match</strong> when <strong>at least one digit</strong> is the same in the <strong>same position</strong> as it was exactly N trials earlier. Otherwise select <strong>No Match</strong>. A digit repeated in a different position is not a match.</p>
<p>For example, when the target is <strong>1, 2, 3</strong>, <strong>8, 2, 7</strong> is a match in position two. <strong>2, 3, 1</strong> is not a match.</p>
<p>The first N trials fill your memory and are not scored. When speech is enabled, the complete sequence plays before the response timer starts. Missing a scored response counts against accuracy.</p>
<p><strong>Keyboard:</strong> F or J = Match; D or K = No Match; Escape = Stop. Use the Pause/Resume button to pause. Returning to this menu stops an active session.</p>
<p class="help">Haptics operate only on devices and browsers that support vibration. This copy preserves the source trainer’s game rules, options, scoring and recorded voice.</p>
</section>
</main>
'''

EXTRA_CSS = '''
[hidden]{display:none!important}
.brand{font-size:.76rem;font-weight:800;letter-spacing:.16em;color:var(--muted);margin:0 0 8px}
.menu-card{text-align:center;padding:30px 22px}
.training-portal{display:flex;align-items:center;justify-content:space-between;gap:28px;max-width:550px;margin:0 auto;padding:24px 30px;border:3px solid #176aa8;border-radius:24px;background:linear-gradient(125deg,#0b4f88,#49aee7);box-shadow:0 12px 26px rgba(15,65,112,.17);color:#fff;text-decoration:none;text-align:left;font-size:clamp(1.35rem,4vw,2.2rem);font-weight:900;line-height:1.12;text-transform:uppercase}
.training-portal:hover{filter:brightness(1.04)}
.training-portal:focus-visible,button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #176aa8;outline-offset:4px}
.menu-note{max-width:620px;margin:22px auto 12px;line-height:1.55;color:var(--muted)}
.guide{line-height:1.65}.guide h2{margin-top:0;color:var(--blue);font-size:1.15rem}
.offline-credits{padding:10px 0 22px}.offline-credits summary{cursor:pointer;font-weight:700;color:var(--blue)}
.offline-credits pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;line-height:1.55;padding:14px;background:var(--panel);border-radius:10px}
.key-guide{text-align:center;margin-top:12px}
'''

NAVIGATION = '''
(function () {
  'use strict';
  const menu = document.getElementById('training-menu');
  const trainer = document.getElementById('trainer');
  function showView() {
    const training = location.hash === '#training';
    if (!training && !trainer.hidden) {
      // Call the source handler even during an idle Test Speech playback.
      const stop = document.getElementById('stop');
      if (typeof stop.onclick === 'function') stop.onclick();
    }
    menu.hidden = training;
    trainer.hidden = !training;
    document.title = training ? 'Ordered Number N-back — Dream Unity' : 'N-back — Dream Unity';
    window.scrollTo(0, 0);
    if (training) document.getElementById('training-title').focus({preventScroll: true});
    else document.getElementById('open-training').focus({preventScroll: true});
  }
  window.addEventListener('hashchange', showView);
  showView();
})();
'''


def build() -> None:
    manifest = json.loads((ROOT / 'SOURCE.json').read_text(encoding='utf-8'))
    # Fail rather than silently bundle an incomplete or changed import.
    for name, entry in manifest['files'].items():
        if blob_sha((ROOT / name).read_bytes()) != entry['git_blob_sha']:
            raise ValueError(f'Imported file changed: {name}')
    source_html = (ROOT / 'extra-training.html').read_text(encoding='utf-8')
    scripts = re.findall(r'<script src="([^\"]+)"></script>', source_html)
    expected = ['number-speech-data.js', 'number-speech.js', 'extra-training-runtime.js']
    if [src.split('?')[0] for src in scripts] != expected:
        raise ValueError('Unexpected source script dependencies')
    document = source_html.replace('<title>Extra Training — Ordered Number N-back</title>', '<title>N-back — Dream Unity</title>')
    document = document.replace('</style>', EXTRA_CSS + '\n</style>', 1)
    marker = '<main class="container">'
    if document.count(marker) != 1:
        raise ValueError('Unexpected source page structure')
    document = document.replace(marker, MENU + '<main id="trainer" class="container" hidden>', 1)
    document = document.replace('<h1>Extra Training', '<h1 id="training-title" tabindex="-1">Extra Training', 1)
    document = document.replace('class="back" href="index.html">← Main Training', 'id="back-to-menu" class="back" href="#menu">← Main Menu', 1)
    document = document.replace('<div class="timer">', '<p class="help key-guide">F / J: Match · D / K: No Match · Escape: Stop</p>\n<div class="timer">', 1)
    credits = (ROOT / 'assets/number-voice/CREDITS.txt').read_text(encoding='utf-8')
    license_text = (ROOT / 'assets/number-voice/LICENSE.txt').read_text(encoding='utf-8')
    notes = (ROOT / 'NUMBER-SPEECH-ASSETS.md').read_text(encoding='utf-8')
    footer = '<footer class="container help offline-credits"><details><summary>Recorded voice credits and license — included offline</summary>'
    footer += '<p>Australian English voice: Cameron, recorded by CAMSOWN. Adapted from Asterisk Core Sounds 1.6.1. CC BY 3.0. No endorsement is claimed.</p>'
    footer += '<p>The complete attribution, modifications and original license are reproduced below.</p>'
    footer += '<pre>' + html.escape(credits + '\n\n' + notes + '\n\n' + license_text) + '</pre></details></footer>'
    document, count = re.subn(r'<footer\b[^>]*>.*?</footer>', lambda _: footer, document, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Missing source voice attribution')
    for src in scripts:
        name = src.split('?')[0]
        code = (ROOT / name).read_text(encoding='utf-8')
        code = re.sub(r'</script', lambda _: '<\\/script', code, flags=re.I)
        document = document.replace(f'<script src="{src}"></script>', f'<script data-bundled-file="{name}">\n{code}\n</script>', 1)
    document = document.replace('</body>', '<script>\n' + NAVIGATION + '\n</script>\n</body>', 1)
    document = document.replace('<head>', '<head>\n<!-- Independent n-back copy; source ' + SOURCE + '@' + COMMIT + '. Rebuild: python3 scripts/build-offline.py -->', 1)
    if re.search(r'<script[^>]+\bsrc\s*=', document, re.I):
        raise ValueError('External script remains in offline build')
    payload = document.encode('utf-8')
    for name in ('index.html', 'N-Back-Offline.html'):
        (ROOT / name).write_bytes(payload)
    (ROOT / '.nojekyll').write_text('', encoding='utf-8')
    print(f'Built complete offline HTML: {len(payload):,} bytes; SHA-256 {hashlib.sha256(payload).hexdigest()}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-source', action='store_true', help='One-time network import from the pinned source commit')
    args = parser.parse_args()
    if args.import_source:
        import_source()
    build()
