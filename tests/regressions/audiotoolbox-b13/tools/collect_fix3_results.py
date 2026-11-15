#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""B13 / ATB-FIX3: gather the executed results (unpatched production, private candidate, production
commit rebuilt in the master build) without personal paths.
Usage: collect_fix3_results.py B13_STAGE AUDIO_STAGE B12_STAGE PRODUCTION_COMMIT OUT.json"""
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
            'failures': [s for s in so.splitlines() if ' FAIL ' in s],
            'end': re.findall(r'(darlingserver_before=\d+|host_mounts_after=\d+|darlingserver_after=\d+|residual_prefix_processes=\d+)', m)}
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
def section(p, a, seg, s):
    d = run('llvm-objdump-19', '--macho', '--arch=' + a, f'--section={seg},{s}', '--full-contents', p).splitlines()[2:]
    return hashlib.sha256(('\n'.join(d) + '\n').encode()).hexdigest()
R = T / 'runs/fix3'
res = {'lot': 'B13 / ATB-FIX3', 'date': '2026-11-15',
       'production_commit': run('git', '-C', T / 'src', 'rev-parse', COMMIT).strip(),
       'parent': run('git', '-C', T / 'src', 'rev-parse', COMMIT + '^').strip(),
       'files': run('git', '-C', T / 'src', 'diff', '--stat', COMMIT + '^', COMMIT).splitlines(),
       'patch_sha256': sha(T / 'fix/ATB-FIX3.patch'),
       'local_replays': {'note': 'unpublished local commits replayed over concurrent documentation commits (disjoint files); same source blob',
                         'commits': [{'sha': '2a70a0ee604e7da8cb15358a325e7d41f3c2f276', 'parent': '8b47e4461fb5afc5a3ddf342e49901fa5fc9b02d', 'rebuilt': 'cand-prod3'},
                                     {'sha': '8372fd42bb3286e287626513f7b98c811b0a505f', 'parent': '786cf3813bfbac8e2206df2f44933707e62e4a38', 'rebuilt': 'cand-prod3b'}],
                         'published': 'production_commit, built by plumbing over 89d6000e without touching the source file: ninja found no work, the build output stays cand-prod3b'},
       'rebuild_logs': {k: [x(l) for l in (T / 'reports' / f).read_text().splitlines()[-3:]] for k, f in
                        [('first', 'mbuild-prod-fix3.log'), ('final', 'mbuild-prod-fix3b.log')]},
       'frozen_before_runs': (T / 'reports/fix3-frozen-before-runs.txt').read_text().replace(str(T), '<B13_STAGE>').splitlines(),
       'reference_installation_audiotoolbox': sha(T / 'mbuild/private-install/libexec/darling' / F)}
res['binaries'] = {}
for c, why in [('prod3b', 'production commit (final) rebuilt in the master build'), ('prod3', 'first local commit rebuilt (same source; differs by N_OSO timestamps and signature)'),
               ('fix3', 'private candidate (build_candidate.py)'), ('ref3', 'method control: no substitution, must equal prod2'),
               ('prod2', 'master before FIX3 (ATB-FIX2-R2b production)')]:
    p = T / 'mfix' / ('cand-' + c) / 'layer' / F
    e = {'role': why, 'sha256': sha(p)}
    for a in ['i386', 'x86_64']:
        e[a] = {s: section(p, a, '__TEXT', s) for s in ['__text', '__const', '__cstring', '__unwind_info', '__eh_frame']}
        e[a]['__DATA,__data'] = section(p, a, '__DATA', '__data')
        e[a]['exports'] = len(exports(p, a))
        e[a]['exports_equal_master_reference'] = exports(p, a) == sorted(set((E / f'master-AudioToolbox-{a}.txt').read_text().split()))
    res['binaries'][c] = e
res['witnesses'] = {**{f'mwit-afm2/{f.name}': sha(f) for f in sorted((T / 'mwit-afm2').iterdir()) if f.suffix == '' and f.is_file()},
                    'b13-afm2.c': sha(P / 'b13-afm2.c'), 'verify_b13_afm2.py': sha(P / 'verify_b13_afm2.py'),
                    'b13-afm2-invalid-specifier.c (first version, recipe error)': sha(T / 'reports/b13-afm2-invalid-specifier.c'),
                    'make_fix3_media.py': sha(P / 'make_fix3_media.py'),
                    **{f'mwit/b13-afm-{a}': sha(T / 'mwit' / f'b13-afm-{a}') for a in ['i386', 'x86_64']}}
res['media_fix3'] = json.loads((T / 'media-fix3/fix3-media.json').read_text())
def afm(c):
    return {'defect_witness_b13_afm': run('python3', '-I', P / 'verify_b13_afm.py', R / c / 'afm/i386', R / c / 'afm/x86_64').splitlines(),
            'positive_oracle_b13_afm2': run('python3', '-I', P / 'verify_b13_afm2.py', R / c / 'afm2/i386', R / c / 'afm2/x86_64').splitlines(),
            'raw': {a: [l for f in sorted((R / c / 'afm2' / a).glob('*.log')) for l in f.read_text().splitlines() if l.startswith('B13AFM2')] for a in ['i386', 'x86_64']}}
res['format_recognition'] = {'unpatched_prod2': afm('prod2'), 'candidate_fix3': afm('fix3'), 'production_prod3b': afm('prod3b')}
lab = lambda pre: [f'{pre}{k}{a}' for a in 'ix' for k in 'ctwzo']
res['format_recognition_runs'] = {
    'unpatched_prod2': [guest(l) for l in lab('hpr2') + [f'jpr2{k}{a}' for a in 'ix' for k in 'leto']],
    'candidate_fix3': [guest(l) for l in lab('hfi3') + [f'jfi3{k}{a}' for a in 'ix' for k in 'leto']],
    'production_prod3b': [guest(l) for l in [f'u{k}{a}' for a in 'ix' for k in 'ctwzo'] + [f'v{k}{a}' for a in 'ix' for k in 'tleo']],
    'invalid_attempts': {'labels': [f'k{c}{k}{a}' for c in ('pr2', 'fi3') for a in 'ix' for k in 'teo' + 'l'],
                         'note': 'first b13-afm2 build: TypesFor* specifier passed as &CFStringRef instead of the CFStringRef (witness error); '
                                 'lookup and lookup_empty crashed (rc=139) on both binaries; tables and open outputs of these runs are superseded by the j* runs',
                         'rc': {l: int((T / 'runs/guest' / l / 'rc').read_text()) for l in [f'k{c}{k}{a}' for c in ('pr2', 'fi3') for a in 'ix' for k in 'tleo']}}}
def series(prefix, cand):
    out = []
    for a in 'ix':
        for t, kind in [('p', 'probe'), ('c', None), ('a', 'fix1'), ('b', 'fix2'), ('v', 'fix2v1'), ('l', None)]:
            l = f'{prefix}{t}{a}'; r = guest(l); r['candidate'] = cand
            if kind:
                r['verify'] = verify(l, kind)
            if t in ('p', 'b', 'a'):
                r['outputs_sha256'] = outputs(l)
            out.append(r)
    return out
res['non_regression'] = {'candidate_fix3': series('y', 'fix3'), 'production_prod3b': series('w', 'prod3b')}
aiff, ulaw = T / 'media/ref-s16be.raw', T / 'media/ref-ulaw-s16be.raw'
res['b13d'] = [play(T / 'runs/play' / l, ulaw if l[2] == 'u' else aiff) for l in ['xdui', 'xdai', 'xdsi', 'xdux', 'xdax', 'ydui', 'ydai', 'ydsi', 'ydux', 'ydax']]
res['b12_non_regression'] = [play(A / 'runs/b12' / l, A / 'runs/b12' / l / 'gms.pcm') for l in ['xn1p', 'xn1s', 'yn1p', 'yn1s']]
res['mapped_elf_i386'] = {}
for n in ['mmaps-xdui', 'mmaps-ydui']:
    rows = [l.split(' ', 2) for l in (T / 'runs' / (n + '.txt')).read_text().splitlines()]
    res['mapped_elf_i386'][n] = {'count': len(rows), 'private_ffmpeg': sum('private-ffmpeg' in r[2] for r in rows), 'private_pulse': sum('private-pulse' in r[2] for r in rows),
                                 'usr_lib32': sum(r[2].startswith('/usr/lib32/') for r in rows), 'x86_64': sum('x86_64-linux-gnu' in r[2] for r in rows),
                                 'etc_ld_so_cache': sum(r[2] == '/etc/ld.so.cache' for r in rows)}
res['mapped_elf_i386']['note'] = ('/etc/ld.so.cache is the path inside the private mount namespace, where the bench bind-mounts the private cache '
                                  '(PREFLIGHT ns_ldcache); the observer matches it through its \\.so pattern and hashes the host file at the same path')
res['host'] = {'i386_packages': int(run('sh', '-c', "dpkg -l | awk '$4==\"i386\"' | wc -l")), 'foreign_architectures': run('dpkg', '--print-foreign-architectures').split(),
               'ld_so_cache_sha256': sha('/etc/ld.so.cache'), 'dpkg_status_sha256': sha('/var/lib/dpkg/status'),
               'usr_lib_i386_linux_gnu': Path('/usr/lib/i386-linux-gnu').exists(), 'mounts': int(run('sh', '-c', 'findmnt -rn | wc -l'))}
Out = Path(sys.argv[5]); Out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + '\n')
print('RESULTS', {k: v['positive_oracle_b13_afm2'][-1] for k, v in res['format_recognition'].items()})
