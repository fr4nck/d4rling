#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Re-authenticate the private Debian i386 indexes (InRelease -> sqv -> SHA-256).

Usage: verify_indexes.py INDEX_DIR   (INDEX_DIR/raw holds the downloaded files)
Never touches APT, dpkg or system files.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

D = Path(sys.argv[1]).resolve()
R = D / 'raw'
KEYRING = '/usr/share/keyrings/debian-archive-keyring.pgp'
FILES = {
    'trixie': ['main/binary-i386/Packages.xz', 'main/Contents-i386.gz'],
    'trixie-updates': ['main/binary-i386/Packages.xz'],
    'trixie-security': ['main/binary-i386/Packages.xz'],
}


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


out = {}
for suite, members in FILES.items():
    signed = R / f'{suite}-InRelease'
    release = D / f'{suite}-Release.verified'
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(['sqv', '--keyring', KEYRING, '--cleartext', str(signed), '--output', tmp + '/Release'],
                           capture_output=True, text=True)
        assert r.returncode == 0, (suite, r.stderr)
        text = Path(tmp, 'Release').read_text()
    assert text.startswith('Origin: Debian\n'), suite
    if release.exists():
        assert release.read_text() == text, (suite, 'verified Release changed')
    else:
        release.write_text(text)
    head = dict(l.split(': ', 1) for l in text.split('\nMD5Sum:', 1)[0].splitlines() if ': ' in l)
    table = text.split('\nSHA256:\n', 1)[1]
    rows = {}
    for line in table.splitlines():
        if not line.startswith(' '):
            break
        h, size, name = line.split()
        rows[name] = (h, int(size))
    entry = {'inrelease_sha256': sha(signed), 'signers': (r.stdout + r.stderr).split(),
             'date': head.get('Date'), 'valid_until': head.get('Valid-Until'),
             'version': head.get('Version'), 'files': {}}
    for m in members:
        local = R / f"{suite}-{m.replace('/binary-i386/', '-i386-').replace('/', '-')}"
        h, size = rows[m]
        assert local.stat().st_size == size and sha(local) == h, (suite, m)
        entry['files'][m] = {'local': local.name, 'sha256': h, 'bytes': size}
    out[suite] = entry
    print('INDEX_OK', suite, head.get('Date'), ' '.join(f"{m}={v['sha256'][:12]}" for m, v in entry['files'].items()))
(D / 'indexes.json').write_text(json.dumps(out, indent=2) + '\n')
