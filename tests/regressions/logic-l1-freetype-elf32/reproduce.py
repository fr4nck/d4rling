#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Private ELF32 FreeType qualification; never installs packages or launches Logic."""
import argparse
import hashlib
import json
import lzma
import os
from pathlib import Path
import shlex
import subprocess
import time

P = argparse.ArgumentParser(description=__doc__)
P.add_argument('--stage', required=True, type=Path)
P.add_argument('--run', action='store_true', help='execute the original Mach-O witnesses in new delegated namespaces')
args = P.parse_args()
H = args.stage.resolve()
assert H.name == 'security-s4-logic-l1-20261114' and H.parent.name == 'validation'
HERE = Path(__file__).resolve().parent
BASE = H / 'elf32-freetype'
O = H / ('elf32-replay-' + str(time.time_ns()))
O.mkdir()
for name in ['metadata', 'packages', 'sysroot', 'logs', 'bin', 'commands']:
    (O / name).mkdir()

def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def command(argv, log):
    r = subprocess.run([str(x) for x in argv], capture_output=True, text=True)
    (O / 'logs' / log).write_text(r.stdout + r.stderr)
    assert r.returncode == 0, (argv[0], r.returncode, r.stderr[-1500:])
    return r.stdout

def paragraphs(data):
    for para in data.split('\n\n'):
        d = {}
        key = None
        for line in para.splitlines():
            if line.startswith(' ') and key:
                d[key] += '\n' + line
            elif ': ' in line:
                key, value = line.split(': ', 1)
                d[key] = value
        if 'Package' in d:
            yield d

# Preserve the frozen bank and the original failure control. These are existing
# private qualified build inputs, not a replacement SDK downloaded by this test.
for name, expected in json.loads((HERE / 'inputs.json').read_text()).items():
    assert sha(H / name) == expected, name
for path, expected in json.loads((H / 'l1-frozen-inputs.json').read_text()).items():
    assert sha(path) == expected, path

# Re-authenticate the captured complete Debian indexes. No apt configuration,
# package database, global architecture, package scripts or system files change.
indexes = []
release_evidence = []
for prefix in ['', 'security-']:
    signed = BASE / 'metadata' / (prefix + 'InRelease')
    release = O / 'metadata' / (prefix + 'Release')
    keys = command(['sqv', '--keyring', '/usr/share/keyrings/debian-archive-keyring.pgp',
                    '--cleartext', signed, '--output', release], prefix + 'signature.log')
    index = BASE / 'metadata' / (prefix + 'Packages.xz')
    entries = release.read_text().split('SHA256:\n', 1)[1].split('\n\n', 1)[0].splitlines()
    expected = next(x.split() for x in entries if x.strip().endswith('main/binary-i386/Packages.xz'))
    assert index.stat().st_size == int(expected[1]) and sha(index) == expected[0]
    indexes.extend(paragraphs(lzma.decompress(index.read_bytes()).decode()))
    release_evidence.append({'signed_sha256': sha(signed), 'index_sha256': sha(index),
                             'index_bytes': index.stat().st_size, 'signers': keys.splitlines()})
packages = json.loads((HERE / 'packages.json').read_text())
for d in packages:
    assert any(all(record.get(k) == d[k] for k in
                   ['Package', 'Version', 'Architecture', 'Filename', 'SHA256', 'Size', 'Depends'])
               for record in indexes), d['Package']
    archive = BASE / 'packages' / Path(d['Filename']).name
    if not archive.exists():
        archive = O / 'packages' / Path(d['Filename']).name
        command(['curl', '--fail', '--location', '--max-time', '90', '-sS', '-o', archive, d['url']],
                d['Package'] + '-download.log')
    assert sha(archive) == d['SHA256'] and archive.stat().st_size == int(d['Size'])
    arch = command(['dpkg-deb', '-f', archive, 'Architecture'], d['Package'] + '-arch.log').strip()
    assert arch == 'i386'
    command(['dpkg-deb', '--extract', archive, O / 'sysroot'], d['Package'] + '-extract.log')
lib = O / 'sysroot/usr/lib/i386-linux-gnu'
(O / 'ld.so.conf').write_text(str(lib) + '\ninclude /etc/ld.so.conf\n')
command(['/sbin/ldconfig', '-X', '-i', '-C', O / 'ld.so.cache', '-f', O / 'ld.so.conf'], 'ldconfig.log')
command(['/sbin/ldconfig', '-p', '-C', O / 'ld.so.cache'], 'cache.txt')

# Compile and link original Mach-O programs against real Darling libSystem.
for arch, old in [('i386', 'native-freetype-i386'), ('x86_64', 'native-freetype-x86_64')]:
    for step in ['compile', 'link']:
        original = json.loads((H / 'commands' / (old + '-' + step + '.json')).read_text())
        c = [str(O / 'bin' / Path(v).name.replace(old, 'ft-api-' + arch))
             if v.startswith(str(H / 'bin') + '/') else str(HERE / 'freetype-api.c')
             if v == str(H / 'native-freetype-probe.c') else v for v in original]
        for flag in ['-o', '-MF']:
            if flag in c:
                assert Path(c[c.index(flag) + 1]).is_relative_to(O)
        (O / 'commands' / ('ft-api-' + arch + '-' + step + '.json')).write_text(json.dumps(c, indent=2) + '\n')
        command(c, 'ft-api-' + arch + '-' + step + '.log')

# Adapt only a copy of the qualified delegated runner; select a read-only cache
# in its private mount namespace. LD_LIBRARY_PATH remains absent and filtered.
def runner(cache):
    t = (H / 'run-deleg.sh').read_text()
    old = 'H="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"'
    assert old in t
    t = t.replace(old, 'H=' + shlex.quote(str(H)) + '\nE=' + shlex.quote(str(O)), 1)
    t = t.replace('cp -- "$lib" "$runtime/$dest"', 'cmp -- "$lib" "$runtime/$dest"')
    t = t.replace('witness|symbol-probe|', 'ft-api-i386|ft-api-x86_64|witness|symbol-probe|')
    t = t.replace('executable="$H/bin/$program"', 'executable="$H/bin/$program"; if [[ "$program" = ft-api-* ]]; then executable="$E/bin/$program"; fi')
    if cache:
        t = t.replace('  mount --make-rprivate /', '  mount --make-rprivate /\n  mount --bind '
                      + shlex.quote(str(O / 'ld.so.cache')) + ' /etc/ld.so.cache\n  mount -o remount,bind,ro /etc/ld.so.cache')
    old = '  exec setpriv --groups=0 -- "$inst/bin/darling" exec "$program"'
    assert old in t
    new = ('  setpriv --groups=0 -- "$inst/bin/darling" exec "$program" &\n'
           '  child=$!\n  python3 ' + shlex.quote(str(HERE / 'capture-maps.py')) +
           ' "$h/runs/$label/elf-maps.json" "$child" &\n  observer=$!\n  set +e\n'
           '  wait "$child"; result=$?\n  wait "$observer"; observation=$?\n'
           '  test "$observation" = 0 || exit 92\n  exit "$result"')
    t = t.replace(old, new)
    marker = '  test "$(cat /proc/self/setgroups)" = allow'
    t = t.replace(marker, '  readlink /proc/self/ns/pid > "$h/runs/$label/pid-namespace"\n' + marker)
    t = t.replace('rc=$?\nset -e', 'rc=$?\nset -e\npython3 ' + shlex.quote(str(HERE / 'check-teardown.py')) + ' "$out"')
    p = O / ('run-private.sh' if cache else 'run-baseline.sh')
    p.write_text(t)
    return p

private_runner = runner(True)
baseline_runner = runner(False)
protected = [Path('/etc/ld.so.cache'), Path('/var/lib/dpkg/status')] + sorted(Path('/etc/apt/sources.list.d').glob('*'))
before = {str(p): sha(p) for p in protected}
records = []
if args.run:
    cases = [
        ('ft32-before', 'ft-api-i386', 'logic-candidate', 'normal', baseline_runner, 134, 'Cannot load libfreetype.so.6 (ELF)', 'EXPECTED_FAILURE'),
        ('ft32-private', 'ft-api-i386', 'logic-candidate', 'normal', private_runner, 0, 'FT_API_PASS', 'PASS'),
        ('ft64-private', 'ft-api-x86_64', 'logic-candidate', 'normal', private_runner, 0, 'FT_API_PASS', 'PASS'),
        ('carbon32-private', 'logic-load-probe', 'logic-candidate', 'normal', private_runner, 134, 'Cannot load libfontconfig.so.1 (ELF)', 'BLOCKED'),
        ('homeres32-normal', 'witness', 'candidate', 'normal', private_runner, 0, 'HOME_RES_I386_PASS checks=88 failures=0', 'PASS'),
        ('homeres32-bypass', 'witness', 'candidate', 'bypass', private_runner, 0, 'HOME_RES_I386_PASS checks=88 failures=0', 'PASS'),
    ]
    for name, program, variant, mode, script, expected, marker, status in cases:
        label = O.name + '-' + name
        command(['bash', script, variant, label, program, mode], name + '-runner.log')
        run = H / 'runs' / label
        rc = int((run / 'rc').read_text())
        logs = (run / 'stdout.log').read_text() + (run / 'stderr.log').read_text()
        assert rc == expected and marker in logs, (name, rc, logs[-1200:])
        meta = dict(x.split('=', 1) for x in (run / 'meta.txt').read_text().splitlines() if '=' in x)
        assert meta['host_mounts_before'] == meta['host_mounts_after']
        teardown = json.loads((run / 'process-teardown.json').read_text())
        assert teardown['status'] == 'PASS' and not teardown['remaining_pids']
        mapped = sorted({x[1] for x in json.loads((run / 'elf-maps.json').read_text())})
        if name == 'ft32-private':
            required = ['libfreetype.so.', 'libbrotlidec.so.', 'libbrotlicommon.so.', 'libbz2.so.', 'libpng16.so.', 'libz.so.']
            for prefix in required:
                assert any(str(lib) in p and Path(p).name.startswith(prefix) for p in mapped), prefix
        if name == 'ft64-private':
            assert not any(str(lib) in p for p in mapped)
            assert any('/x86_64-linux-gnu/libfreetype.so.' in p for p in mapped)
        images = []
        for path in mapped:
            p = Path(path)
            if p.is_file():
                with p.open('rb') as f:
                    ident = f.read(5)
                if ident[:4] == b'\x7fELF':
                    images.append({'path': path, 'sha256': sha(p), 'elf_class': ident[4] * 32})
        records.append({'name': name, 'status': status, 'rc': rc, 'expected_rc': expected,
                        'label': label, 'program': program, 'mode': mode,
                        'binary_sha256': meta['program_sha256'], 'native_images': images,
                        'process_teardown': teardown, 'global_server_counts': [meta['darlingserver_before'], meta['darlingserver_after']]})
        print(name, status, 'rc=' + str(rc), flush=True)
assert before == {str(p): sha(p) for p in protected}, 'host state changed'
for name, expected in json.loads((HERE / 'inputs.json').read_text()).items():
    assert sha(H / name) == expected, name
report = {'source_head': subprocess.check_output(['git', '-C', str(H / 'src'), 'rev-parse', 'HEAD'], text=True).strip(),
          'packages': packages, 'metadata': release_evidence, 'runs': records,
          'host_files_unchanged': before, 'global_foreign_architectures': subprocess.check_output(['dpkg', '--print-foreign-architectures'], text=True).splitlines()}
(O / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
print('PRIVATE_ELF32_EVIDENCE', O, flush=True)
