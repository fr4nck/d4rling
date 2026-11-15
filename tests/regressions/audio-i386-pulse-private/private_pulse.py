#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Private ELF32 PulseAudio client closure (method of LOGIC-L1 FreeType, a007a5399).

  private_pulse.py plan    WORK      check pins against the authenticated indexes; no download
  private_pulse.py prepare WORK OUT  download pinned .deb (only with --allow-download), verify
                                     SHA-256, dpkg-deb --extract (no maintainer script), build a
                                     private ld.so.cache, check every DT_NEEDED resolves
WORK is the audio-i386-deps workspace. Never calls apt, never modifies dpkg, APT,
architectures, /etc or any amd64 library. glibc ELF32 and its interpreter are
reused from the installed libc6-i386 (/usr/lib32), never replaced.
"""
import hashlib
import json
import lzma
import re
import subprocess
import sys
from pathlib import Path

MODE, WORK = sys.argv[1], Path(sys.argv[2]).resolve()
ALLOW = '--allow-download' in sys.argv
IDX = WORK / 'index-20261115'
MANIFEST = WORK / 'packages-private-pulse.json'
# libc6, libgcc-s1 and gcc-14-base belong to the apt closure but are provided at
# the ELF level by the installed biarch packages libc6-i386 / lib32gcc-s1.
BIARCH = {'libc6': 'libc6-i386', 'libgcc-s1': 'lib32gcc-s1', 'gcc-14-base': None}
MIRRORS = {'trixie': 'https://deb.debian.org/debian/', 'trixie-updates': 'https://deb.debian.org/debian/',
           'trixie-security': 'https://security.debian.org/debian-security/'}


def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def run(argv, **kw):
    return subprocess.run([str(a) for a in argv], capture_output=True, text=True, check=True, **kw).stdout


protected = [Path('/etc/ld.so.cache'), Path('/var/lib/dpkg/status'), Path('/usr/lib/ld-linux.so.2'),
             Path('/usr/lib32/ld-linux.so.2')] + sorted(Path('/etc/apt/sources.list.d').glob('*'))
before = {str(p): sha(p) for p in protected}
foreign_before = run(['dpkg', '--print-foreign-architectures'])

# 1. re-authenticate the indexes, then pin every package to an index record
run(['python3', '-I', WORK / 'tools/verify_indexes.py', IDX])
records = {}
for suite, e in json.loads((IDX / 'indexes.json').read_text()).items():
    raw = lzma.decompress((IDX / 'raw' / e['files']['main/binary-i386/Packages.xz']['local']).read_bytes()).decode()
    for para in raw.split('\n\n'):
        d = dict(l.split(': ', 1) for l in para.splitlines() if ': ' in l and not l.startswith(' '))
        if 'Package' in d:
            records.setdefault((d['Package'], d['Version'], d['SHA256']), suite)
closure = json.loads((WORK / 'closure-libpulse0-i386.json').read_text())
pins = []
for p in closure['packages']:
    assert (p['package'], p['version'], p['sha256']) in records, p['package']
    if p['package'] in BIARCH:
        continue
    pins.append({k: p[k] for k in ['package', 'version', 'suite', 'filename', 'size', 'sha256', 'source',
                                    'depends', 'amd64_installed', 'version_lock']}
                | {'url': MIRRORS[p['suite']] + p['filename']})
for name, biarch in BIARCH.items():
    if biarch:
        st = run(['dpkg-query', '-W', '-f', '${db:Status-Abbrev} ${Version}', biarch]).split()
        assert st[0] == 'ii', biarch
MANIFEST.write_text(json.dumps(pins, indent=2) + '\n')
print('PLAN packages=%d download_bytes=%d (excluded, provided by biarch: %s)'
      % (len(pins), sum(p['size'] for p in pins), ', '.join(f'{k}->{v}' for k, v in BIARCH.items())))
for p in pins:
    print(f"  {p['package']:<16} {p['version']:<24} {p['size']:>8}  {p['url']}")

if MODE == 'prepare':
    OUT = Path(sys.argv[3]).resolve()
    assert ALLOW, 'binary package download requires --allow-download (explicit operator approval)'
    OUT.mkdir()
    for d in ['packages', 'sysroot', 'logs']:
        (OUT / d).mkdir()
    for p in pins:
        deb = OUT / 'packages' / Path(p['filename']).name
        run(['curl', '--fail', '--location', '--max-time', '120', '-sS', '-o', deb, p['url']])
        assert deb.stat().st_size == p['size'] and sha(deb) == p['sha256'], p['package']
        assert run(['dpkg-deb', '-f', deb, 'Package', 'Version', 'Architecture']).split() == \
            ['Package:', p['package'], 'Version:', p['version'], 'Architecture:', 'i386'], p['package']
        run(['dpkg-deb', '--extract', deb, OUT / 'sysroot'])
    lib = OUT / 'sysroot/usr/lib/i386-linux-gnu'
    (OUT / 'ld.so.conf').write_text(f'{lib}\n{lib}/pulseaudio\ninclude /etc/ld.so.conf\n')
    run(['/sbin/ldconfig', '-X', '-i', '-C', OUT / 'ld.so.cache', '-f', OUT / 'ld.so.conf'])
    (OUT / 'cache.txt').write_text(run(['/sbin/ldconfig', '-p', '-C', OUT / 'ld.so.cache']))
    # every ELF32 DT_NEEDED must resolve to the private tree or to /usr/lib32
    cache = {}
    for line in (OUT / 'cache.txt').read_text().splitlines()[1:]:
        m = re.match(r'\s*(\S+) \((\S+)\) => (\S+)', line)
        if m and m.group(2).startswith('libc6') and ',x86-64' not in m.group(2) and 'x32' not in m.group(2):
            cache.setdefault(m.group(1), m.group(3))
    elves = []
    for f in sorted(lib.rglob('*.so*')):
        if f.is_file() and not f.is_symlink() and f.read_bytes()[:5] == b'\x7fELF\x01':
            dyn = run(['readelf', '-d', f])
            needed = re.findall(r'\(NEEDED\).*\[(.+?)\]', dyn)
            runpath = re.findall(r'\((?:RUNPATH|RPATH)\).*\[(.+?)\]', dyn)
            unresolved = [n for n in needed if n not in cache]
            elves.append({'file': str(f.relative_to(OUT)), 'sha256': sha(f), 'needed': needed,
                          'runpath': runpath, 'resolved': {n: cache.get(n) for n in needed},
                          'unresolved': unresolved})
            assert not unresolved, (f, unresolved)
    (OUT / 'elf32.json').write_text(json.dumps(elves, indent=2) + '\n')
    print('PREPARED', OUT, 'elf32_images=%d' % len(elves))

assert before == {str(p): sha(p) for p in protected}, 'host state changed'
assert foreign_before == run(['dpkg', '--print-foreign-architectures'])
print('HOST_UNCHANGED', ' '.join(f'{Path(k).name}={v[:12]}' for k, v in before.items()))
