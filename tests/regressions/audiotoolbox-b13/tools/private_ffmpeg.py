#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""B13: private ELF32 FFmpeg closure for AudioToolbox i386 (AUDIO-I386 method).

  private_ffmpeg.py plan    STAGE INDEX_DIR PULSE_DIR
  private_ffmpeg.py prepare STAGE INDEX_DIR PULSE_DIR OUT --allow-download

STAGE holds closure-ffmpeg-i386.json (resolve_closure.py libavformat61,libavcodec61,
libavutil59,libswresample5). PULSE_DIR is the AUDIO-I386 private extraction
(packages-private-pulse.json beside it, sysroot/ inside): its packages are reused,
never downloaded again. glibc and the GCC runtime come from the installed biarch
packages (same versions, checked). `plan` writes packages-private-ffmpeg.json and
downloads nothing. `prepare` (operator approval: --allow-download) downloads only
the pinned archives, checks size, SHA-256, name, version and architecture,
extracts with dpkg-deb --extract (no maintainer script), builds a private
ld.so.cache covering FFmpeg + PulseAudio trees, and checks that every ELF32
DT_NEEDED resolves. Never calls apt; never changes dpkg, APT, /etc or host libraries.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

MODE, STAGE, IDX, PULSE = sys.argv[1], Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve(), Path(sys.argv[4]).resolve()
BIARCH = {'libc6': 'libc6-i386', 'libgcc-s1': 'lib32gcc-s1', 'gcc-14-base': None, 'libstdc++6': 'lib32stdc++6',
          'libatomic1': 'lib32atomic1', 'libgomp1': 'lib32gomp1'}
MIRRORS = {'trixie': 'https://deb.debian.org/debian/', 'trixie-updates': 'https://deb.debian.org/debian/',
           'trixie-security': 'https://security.debian.org/debian-security/'}


def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def run(argv):
    return subprocess.run([str(a) for a in argv], capture_output=True, text=True, check=True).stdout


protected = [Path('/etc/ld.so.cache'), Path('/var/lib/dpkg/status'), Path('/usr/lib/ld-linux.so.2'),
             Path('/usr/lib32/ld-linux.so.2')] + sorted(Path('/etc/apt/sources.list.d').glob('*'))
before = {str(p): sha(p) for p in protected}
foreign_before = run(['dpkg', '--print-foreign-architectures'])

run(['python3', '-I', Path(__file__).resolve().parent / 'verify_indexes.py', IDX])
closure = json.loads((STAGE / 'closure-ffmpeg-i386.json').read_text())
pulse = {p['package']: p for p in json.loads((PULSE.parent / 'packages-private-pulse.json').read_text())}
pins, reused, biarch = [], [], []
for p in closure['packages']:
    n = p['package']
    if n in pulse:
        assert (pulse[n]['version'], pulse[n]['sha256']) == (p['version'], p['sha256']), n
        assert (PULSE / 'packages' / Path(p['filename']).name).exists(), n
        reused.append(n)
        continue
    if n in BIARCH:
        b = BIARCH[n]
        if b:
            st = run(['dpkg-query', '-W', '-f', '${db:Status-Abbrev} ${Version}', b]).split()
            assert st[0] == 'ii' and st[1] == p['version'], (n, b, st)
        biarch.append({'package': n, 'version': p['version'], 'provided_by': b})
        continue
    pins.append({k: p[k] for k in ['package', 'version', 'suite', 'filename', 'size', 'sha256', 'source',
                                    'installed_size_kib', 'amd64_installed', 'version_lock']}
                | {'url': MIRRORS[p['suite']] + p['filename']})
(STAGE / 'packages-private-ffmpeg.json').write_text(json.dumps(
    {'reused_from_audio_i386': reused, 'biarch': biarch, 'download': pins}, indent=2) + '\n')
print('PLAN download_packages=%d download_bytes=%d extracted_kib=%d reused_from_audio_i386=%d biarch=%d'
      % (len(pins), sum(p['size'] for p in pins), sum(p['installed_size_kib'] for p in pins), len(reused), len(biarch)))

if MODE == 'prepare':
    OUT = Path(sys.argv[5]).resolve()
    assert '--allow-download' in sys.argv, 'binary package download requires --allow-download (explicit operator approval)'
    OUT.mkdir()
    for d in ['packages', 'sysroot']:
        (OUT / d).mkdir()
    for p in pins:
        deb = OUT / 'packages' / Path(p['filename']).name
        run(['curl', '--fail', '--location', '--max-time', '300', '-sS', '-o', deb, p['url']])
        assert deb.stat().st_size == p['size'] and sha(deb) == p['sha256'], p['package']
        assert run(['dpkg-deb', '-f', deb, 'Package', 'Version', 'Architecture']).split() == \
            ['Package:', p['package'], 'Version:', p['version'], 'Architecture:', 'i386'], p['package']
        run(['dpkg-deb', '--extract', deb, OUT / 'sysroot'])
    roots = [OUT / 'sysroot', PULSE / 'sysroot']
    dirs = []
    for r in roots:
        lib = r / 'usr/lib/i386-linux-gnu'
        dirs += [lib] + sorted({f.parent for f in lib.rglob('*.so*') if f.parent != lib})
    (OUT / 'ld.so.conf').write_text(''.join(f'{d}\n' for d in dirs) + 'include /etc/ld.so.conf\n')
    run(['/sbin/ldconfig', '-X', '-i', '-C', OUT / 'ld.so.cache', '-f', OUT / 'ld.so.conf'])
    (OUT / 'cache.txt').write_text(run(['/sbin/ldconfig', '-p', '-C', OUT / 'ld.so.cache']))
    cache = {}
    for line in (OUT / 'cache.txt').read_text().splitlines()[1:]:
        m = re.match(r'\s*(\S+) \((\S+)\) => (\S+)', line)
        if m and m.group(2).startswith('libc6') and 'x86-64' not in m.group(2) and 'x32' not in m.group(2):
            cache.setdefault(m.group(1), m.group(3))
    elves, unresolved_all = [], {}
    for f in sorted((OUT / 'sysroot/usr/lib/i386-linux-gnu').rglob('*.so*')):
        if f.is_file() and not f.is_symlink() and f.read_bytes()[:5] == b'\x7fELF\x01':
            dyn = run(['readelf', '-d', f])
            needed = re.findall(r'\(NEEDED\).*\[(.+?)\]', dyn)
            unresolved = [n for n in needed if n not in cache]
            if unresolved:
                unresolved_all[str(f.relative_to(OUT))] = unresolved
            elves.append({'file': str(f.relative_to(OUT)), 'sha256': sha(f), 'needed': needed,
                          'resolved': {n: cache.get(n) for n in needed}, 'unresolved': unresolved})
    (OUT / 'elf32.json').write_text(json.dumps(elves, indent=2) + '\n')
    print('PREPARED', OUT, 'elf32_images=%d unresolved=%s' % (len(elves), json.dumps(unresolved_all)))
    assert not unresolved_all

assert before == {str(p): sha(p) for p in protected}, 'host state changed'
assert foreign_before == run(['dpkg', '--print-foreign-architectures'])
print('HOST_UNCHANGED', ' '.join(f'{Path(k).name}={v[:12]}' for k, v in before.items()))
