#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""B13 / ATB-FIX2-R2b: gather the executed results (private candidates, production commit rebuilt
in the master build) without personal paths.
Usage: collect_r2b_results.py B13_STAGE AUDIO_STAGE B12_STAGE PRODUCTION_COMMIT OUT.json"""
import hashlib, json, re, subprocess, sys
from pathlib import Path
T, A, B = (Path(x) for x in sys.argv[1:4])
COMMIT = sys.argv[4]
H = str(Path.home())
def x(s): return s.replace(str(T), '<B13_STAGE>').replace(str(A), '<AUDIO_STAGE>').replace(str(B), '<B12_STAGE>').replace(H, '~')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def find(rx, s, g=1):
    m = re.search(rx, s, re.M)
    return m.group(g) if m else None
def run(*a): return subprocess.run([str(v) for v in a], capture_output=True, text=True).stdout
def guest(l):
    g = T / 'runs/guest' / l; m = (g / 'meta.txt').read_text(); err = (g / 'stderr.log').read_text(); so = (g / 'stdout.log').read_text()
    return {'label': l, 'rc': int((g / 'rc').read_text()), 'program_sha256': find(r'program=\S+ sha256=(\w+)', m),
            'args': x(find(r'^args=(.*)$', m) or ''), 'layer_files': re.findall(r'^layer_file=(\w+)', m, re.M),
            'installation': x(find(r'^installation=(\S+)', m) or ''), 'dyld': find(r' dyld=(\w+)', m),
            'ns_ldcache': find(r'ns_ldcache=(\w+)', err), 'ns_audiotoolbox': find(r'ns_audiotoolbox=(\w+)', err),
            'ns_libcxx': find(r'ns_libcxx=(\w+)', err),
            'summary': [s for s in so.splitlines() if 'SUMMARY' in s],
            'checks': [s for s in so.splitlines() if s.startswith(('B13FIX ', 'B13LIM '))],
            'failures': [s for s in so.splitlines() if ' FAIL ' in s],
            'observation': [s for s in so.splitlines() if 'convertbuffer' in s and s.startswith('B13_OBS')],
            'end': re.findall(r'(host_mounts_after=\d+|darlingserver_after=\d+|residual_prefix_processes=\d+)', m)}
P = T / 'probe'
def verify(l, kind):
    if kind == 'probe':
        return run('python3', '-I', P / 'verify_b13.py', T / 'media', T / 'runs/out' / l, T / 'runs/guest' / l / 'stdout.log').splitlines()[-1:]
    if kind == 'fix2v1':
        return run('python3', '-I', P / 'verify_b13_fix-v1.py', T / 'media', T / 'runs/out' / l, 'fix2').splitlines()
    return run('python3', '-I', P / 'verify_b13_fix.py', T / 'media', T / 'runs/out' / l, kind).splitlines()
def outputs(l): return {f.name: sha(f) for f in sorted((T / 'runs/out' / l).iterdir())}
def bitexact(ref, cap, start=None):
    return run('python3', '-I', B / 'probe/bitexact.py', ref, cap, *([start] if start else [])).strip()
def play(d, ref):
    s = (d / 'summary.txt').read_text()
    e = {'label': d.name, 'summary': [ln for ln in x(s).splitlines() if not ln.startswith('  seq')], 'bitexact': bitexact(ref, d / 'monitor.raw')}
    if 'mode=stoprestart' in s:
        e['bitexact_second_pass'] = bitexact(ref, d / 'monitor.raw', int(find(r'alignment_frame=(\d+)', e['bitexact'])) + 44100)
    gm = (d / 'guest.meta.txt').read_text(); ge = (d / 'guest.stderr.log').read_text()
    e['layer_files'] = re.findall(r'^layer_file=(\w+)', gm, re.M); e['installation'] = x(find(r'^installation=(\S+)', gm) or '')
    e['ns_audiotoolbox'] = find(r'ns_audiotoolbox=(\w+)', ge)
    return e
F = 'System/Library/Frameworks/AudioToolbox.framework/Versions/A/AudioToolbox'
E = T / 'reports/exports'
def exports(p, a): return sorted(set(run('llvm-nm-19', '-g', '--defined-only', '--arch=' + a, p).split()[2::3]))
def section(p, a, s):
    d = run('llvm-objdump-19', '--macho', '--arch=' + a, '--section=__TEXT,' + s, '--full-contents', p).splitlines()[2:]
    return hashlib.sha256(('\n'.join(d) + '\n').encode()).hexdigest()
res = {'lot': 'B13 / ATB-FIX2-R2b', 'date': '2026-11-15',
       'production_commit': run('git', '-C', T / 'src', 'rev-parse', COMMIT).strip(),
       'parent': run('git', '-C', T / 'src', 'rev-parse', COMMIT + '^').strip(),
       'files': run('git', '-C', T / 'src', 'diff', '--stat', COMMIT + '^', COMMIT).splitlines(),
       'patch_sha256': sha(T / 'fix/ATB-FIX2-R2b.patch'),
       'rebuild': {'command': 'ninja -j 14 src/CoreAudio/AudioToolbox/AudioToolbox (master build, FIX1 included)',
                   'log_tail': [x(l) for l in (T / 'reports/mbuild-prod-fix2r2b.log').read_text().splitlines()[-2:]]},
       'reference_installation_audiotoolbox': sha(T / 'mbuild/private-install/libexec/darling' / F)}
res['binaries'] = {}
for c, why in [('prod2', 'production commit rebuilt in the master build'), ('r2b1', 'private candidate R2b (qualified before the GO)'),
               ('r2a1', 'R2 as published (anomalies reproduced)'), ('r2s1', 'test only: R2 + output size 0 on error'),
               ('prodref', 'FIX1 production (method control)')]:
    p = T / 'mfix' / ('cand-' + c) / 'layer' / F
    e = {'role': why, 'sha256': sha(p)}
    for a in ['i386', 'x86_64']:
        e[a] = {s: section(p, a, s) for s in ['__text', '__const', '__cstring']}
        e[a]['exports'] = len(exports(p, a))
        e[a]['exports_equal_master_reference'] = exports(p, a) == sorted(set((E / f'master-AudioToolbox-{a}.txt').read_text().split()))
    j = T / 'mfix' / ('cand-' + c) / 'candidate.json'
    if j.exists():
        k = json.loads(j.read_text())
        e['build_tree_unchanged'] = k.get('build_tree_unchanged'); e['reference_build_sha256'] = k.get('reference_build_sha256')
    res['binaries'][c] = e
res['witnesses'] = {'b13-fix.c (27 controls, frozen)': sha(P / 'b13-fix.c'), 'b13-limits.c': sha(P / 'b13-limits.c'),
                    **{f'mwit3/{f.name}': sha(f) for f in sorted((T / 'mwit3').iterdir()) if f.suffix == '' and f.is_file()},
                    **{f'mwit-lim/{f.name}': sha(f) for f in sorted((T / 'mwit-lim').iterdir()) if f.suffix == '' and f.is_file()},
                    **{f'mwit/{n}': sha(T / 'mwit' / n) for n in ['b13-atb-i386', 'b13-atb-x86_64', 'b13-fix-v1-i386', 'b13-fix-v1-x86_64']}}
def series(prefix, cand, kinds):
    out = []
    for a in 'ix':
        for t, kind in kinds:
            l = f'{prefix}{t}{a}'; r = guest(l); r['candidate'] = cand
            if kind and r['rc'] != 139:
                r['verify'] = verify(l, kind)
            if t in ('p', 'b', 'a'):
                r['outputs_sha256'] = outputs(l)
            out.append(r)
    return out
K = [('p', 'probe'), ('c', None), ('a', 'fix1'), ('b', 'fix2'), ('v', 'fix2v1')]
res['production'] = series('z', 'prod2', K + [('l', None)])
res['candidate_r2b'] = series('q', 'r2b1', K)
res['candidate_r2_as_published'] = series('qr', 'r2a1', [('a', 'fix2')])
res['candidate_size_zero_only'] = series('qr', 'r2s1', [('s', 'fix2')])
res['limits_probe'] = [guest(l) for l in ['limr2bi', 'limr2bx', 'limproi', 'limprox']]
res['earlier_extended_witness_mwit2'] = {'note': 'first extended witness (mwit2), criterion corrected afterwards (see report)',
                                         'runs': [guest(l) for l in ['xr2a1i', 'xr2a1x', 'xr2s1i', 'xr2s1x', 'xr2b1i', 'xr2b1x']]}
aiff, ulaw = T / 'media/ref-s16be.raw', T / 'media/ref-ulaw-s16be.raw'
res['b13d'] = [play(T / 'runs/play' / l, ulaw if l[2] == 'u' else aiff) for l in ['zdui', 'zdai', 'zdsi', 'zdux', 'zdax', 'qdui', 'qdai', 'qdsi', 'qdux', 'qdax']]
res['b12_non_regression'] = [play(A / 'runs/b12' / l, A / 'runs/b12' / l / 'gms.pcm') for l in ['zn1p', 'zn1s', 'qn1p', 'qn1s']]
res['mapped_elf_i386'] = {}
for n in ['mmaps-zdui', 'mmaps-qdui']:
    rows = [l.split(' ', 2) for l in (T / 'runs' / (n + '.txt')).read_text().splitlines()]
    res['mapped_elf_i386'][n] = {'count': len(rows), 'private_ffmpeg': sum('private-ffmpeg' in r[2] for r in rows), 'private_pulse': sum('private-pulse' in r[2] for r in rows),
                                 'usr_lib32': sum(r[2].startswith('/usr/lib32/') for r in rows), 'x86_64': sum('x86_64-linux-gnu' in r[2] for r in rows)}
res['host'] = {'i386_packages': int(run('sh', '-c', "dpkg -l | awk '$4==\"i386\"' | wc -l")), 'foreign_architectures': run('dpkg', '--print-foreign-architectures').split(),
               'ld_so_cache_sha256': sha('/etc/ld.so.cache'), 'dpkg_status_sha256': sha('/var/lib/dpkg/status'),
               'usr_lib_i386_linux_gnu': Path('/usr/lib/i386-linux-gnu').exists(), 'mounts': int(run('sh', '-c', 'findmnt -rn | wc -l'))}
Out = Path(sys.argv[5]); Out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + '\n')
print('RESULTS production', len(res['production']), 'r2b', len(res['candidate_r2b']), 'b13d', len(res['b13d']), 'b12', len(res['b12_non_regression']))
