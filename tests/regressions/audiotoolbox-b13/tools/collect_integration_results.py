#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""B13-INT (requalification on master and integration): gather the executed results without personal paths.
Usage: collect_integration_results.py B13_STAGE AUDIO_STAGE B12_STAGE OUT.json"""
import hashlib, json, re, subprocess, sys
from pathlib import Path
T, A, B = (Path(x) for x in sys.argv[1:4])
H = str(Path.home())
def x(s): return s.replace(str(T), '<B13_STAGE>').replace(str(A), '<AUDIO_STAGE>').replace(str(B), '<B12_STAGE>').replace(H, '~')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def find(rx, s, g=1):
    m = re.search(rx, s, re.M)
    return m.group(g) if m else None
def run(*a): return subprocess.run([str(v) for v in a], capture_output=True, text=True).stdout
def guest(l, root=T / 'runs/guest'):
    g = root / l; m = (g / 'meta.txt').read_text(); err = (g / 'stderr.log').read_text(); so = (g / 'stdout.log').read_text()
    return {'label': l, 'rc': int((g / 'rc').read_text()), 'program_sha256': find(r'program=\S+ sha256=(\w+)', m),
            'args': x(find(r'^args=(.*)$', m) or ''), 'layer_files': re.findall(r'^layer_file=(\w+)', m, re.M),
            'installation': x(find(r'^installation=(\S+)', m) or ''), 'dyld': find(r' dyld=(\w+)', m), 'kernel': find(r' kernel=(\w+)', m),
            'ns_ldcache': find(r'ns_ldcache=(\w+)', err), 'ns_audiotoolbox': find(r'ns_audiotoolbox=(\w+)', err),
            'ns_libcxx': find(r'ns_libcxx=(\w+)', err), 'ns_mldr': find(r'ns_mldr=(\w+)', err),
            'summary': [s for s in so.splitlines() if 'SUMMARY' in s], 'last_enter': ([s for s in so.splitlines() if s.startswith('B13FIX_ENTER')] or [None])[-1],
            'checks': [s for s in so.splitlines() if s.startswith('B13FIX ')],
            'failures': [s for s in so.splitlines() if ' FAIL ' in s],
            'end': re.findall(r'(host_mounts_after=\d+|darlingserver_after=\d+|residual_prefix_processes=\d+)', m)}
P = T / 'probe'
def verify(l, kind):
    if kind == 'probe':
        return run('python3', '-I', P / 'verify_b13.py', T / 'media', T / 'runs/out' / l, T / 'runs/guest' / l / 'stdout.log').splitlines()[-1:]
    if kind == 'fix2v1':
        return run('python3', '-I', P / 'verify_b13_fix-v1.py', T / 'media', T / 'runs/out' / l, 'fix2').splitlines()
    return run('python3', '-I', P / 'verify_b13_fix.py', T / 'media', T / 'runs/out' / l, kind).splitlines()
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
I = T / 'mbuild/private-install/libexec/darling'
res = {'lot': 'B13-INT', 'date': '2026-11-15',
       'master': run('git', '-C', T / 'src', 'rev-parse', '397e94d47').strip(),
       'libcxx_gitlink': run('git', '-C', T / 'src', 'rev-parse', '397e94d47:src/external/libcxx').strip(),
       'build': {'configure': 'tools/build-master.sh (same cache options as the B11E build)',
                 'build_log_tail': [x(l) for l in (T / 'reports/mbuild-build.log').read_text().splitlines()[-1:]],
                 'failed_steps': (T / 'reports/mbuild-build.log').read_text().count('\nFAILED')},
       'images': {k: sha(I / k) for k in ['System/Library/Frameworks/AudioToolbox.framework/Versions/A/AudioToolbox',
                  'System/Library/Frameworks/CoreAudio.framework/Versions/A/CoreAudio', 'usr/lib/libc++.1.dylib', 'usr/lib/dyld',
                  'usr/lib/system/libdyld.dylib', 'usr/lib/system/libsystem_kernel.dylib', 'usr/libexec/darling/mldr', 'usr/libexec/darling/mldr32']}}
E = T / 'reports/exports'
res['exports'] = {}
for n in ['libc++.1.dylib', 'AudioToolbox']:
    for a in ['i386', 'x86_64']:
        m = set((E / f'master-{n}-{a}.txt').read_text().split()); b = set((E / f'b11e-{n}-{a}.txt').read_text().split())
        res['exports'][f'{n}/{a}'] = {'b11e_build': len(b), 'master': len(m), 'added': sorted(m - b), 'removed': sorted(b - m)}
res['candidates'] = {}
for c in ['ref0', 'fix1', 'fix2', 'fix2r', 'fix12', 'fix12r']:
    j = json.loads((T / 'mfix' / ('cand-' + c) / 'candidate.json').read_text())
    res['candidates'][c] = {'audiotoolbox_sha256': j['audiotoolbox_sha256'], 'reference_build_sha256': j['reference_build_sha256'],
                            'objects': {Path(k).name: {'candidate_source_sha256': v['candidate_sha256'], 'object_sha256': v['object_sha256']} for k, v in j['objects'].items()},
                            'build_tree_unchanged': j['build_tree_unchanged']}
pa = T / 'mfix/cand-prod1/layer/System/Library/Frameworks/AudioToolbox.framework/Versions/A/AudioToolbox'
res['candidates']['prod1'] = {'audiotoolbox_sha256': sha(pa), 'source': 'commit d65d7df6 (FIX1) rebuilt in the master build: AudioConverterImpl.cpp.o + link',
                              'exports_equal_reference': all(sorted(set(run('llvm-nm-19', '-g', '--defined-only', '--arch=' + a, pa).split()[2::3])) == sorted(set((E / f'master-AudioToolbox-{a}.txt').read_text().split())) for a in ['i386', 'x86_64'])}
res['witnesses'] = {f.name: sha(f) for f in sorted((T / 'mwit').iterdir()) if f.suffix == '' and f.is_file()}
res['matrix'] = []
for c, k in [('ref', '0'), ('fix1', '1'), ('fix2', '2'), ('fix2r', '2r'), ('fix12', '12'), ('fix12r', '12r'), ('prod1', 'prod1')]:
    for a in 'ix':
        for t, kind in [('p', 'probe'), ('c', None), ('a', 'fix1'), ('v', 'fix2v1'), ('b', 'fix2')]:
            l = f'm{k}{t}{a}'; r = guest(l); r['candidate'] = c
            if kind and r['rc'] != 139:
                r['verify'] = verify(l, kind)
            if t == 'c':
                r['observation'] = [s for s in (T / 'runs/guest' / l / 'stdout.log').read_text().splitlines() if 'convertbuffer' in s]
            if t == 'p' and r['rc'] != 139:
                r['outputs_sha256'] = {f.name: sha(f) for f in sorted((T / 'runs/out' / l).iterdir())}
            res['matrix'].append(r)
aiff, ulaw = T / 'media/ref-s16be.raw', T / 'media/ref-ulaw-s16be.raw'
res['b13d'] = [play(T / 'runs/play' / l, ulaw if l[2] == 'u' else aiff) for l in ['mpu12i', 'mpa12i', 'mps12i', 'mpa0i', 'mpu0i', 'mpa12x', 'mpu12x', 'mqui', 'mqai', 'mqsi', 'mqux', 'mqax']]
res['b12_non_regression'] = [play(A / 'runs/b12' / l, A / 'runs/b12' / l / 'gms.pcm') for l in ['mn0p', 'mn1p', 'mn2p', 'mn2s', 'mq0p', 'mq0s']]
res['mapped_elf_i386'] = {}
for n in ['mmaps-mpu12i', 'mmaps-mqui']:
    rows = [l.split(' ', 2) for l in (T / 'runs' / (n + '.txt')).read_text().splitlines()]
    res['mapped_elf_i386'][n] = {'count': len(rows), 'private_ffmpeg': sum('private-ffmpeg' in r[2] for r in rows), 'private_pulse': sum('private-pulse' in r[2] for r in rows),
                                 'usr_lib32': sum(r[2].startswith('/usr/lib32/') for r in rows), 'x86_64': sum('x86_64-linux-gnu' in r[2] for r in rows),
                                 'images': [{'file': x(r[2]), 'sha256': r[1]} for r in rows]}
res['defect3'] = {'verify': run('python3', '-I', P / 'verify_b13_afm.py', T / 'runs/afm/i386', T / 'runs/afm/x86_64').splitlines(),
                  'raw': {a: [l for f in sorted((T / 'runs/afm' / a).glob('*.log')) for l in f.read_text().splitlines() if l.startswith('B13AFM')] for a in ['i386', 'x86_64']},
                  'runs': [guest(l) for l in ['mdci2', 'mdti2', 'mdwi2', 'mdzi2', 'mdoi2', 'mdcx2', 'mdtx2', 'mdwx2', 'mdzx2', 'mdox2']],
                  'invalid_attempts': {'labels': ['mdci', 'mdti', 'mdwi', 'mdzi', 'mdoi', 'mdcx', 'mdtx', 'mdwx', 'mdzx', 'mdox'],
                                       'rc': sorted({int((T / 'runs/guest' / l / 'rc').read_text()) for l in ['mdci', 'mdti', 'mdwi', 'mdzi', 'mdoi', 'mdcx', 'mdtx', 'mdwx', 'mdzx', 'mdox']}),
                                       'cause': 'recipe error: the launcher appended an output directory that b13-afm does not take (usage, rc=2, before any AudioToolbox call)'}}
res['host'] = {'i386_packages': int(run('sh', '-c', "dpkg -l | awk '$4==\"i386\"' | wc -l")), 'foreign_architectures': run('dpkg', '--print-foreign-architectures').split(),
               'ld_so_cache_sha256': sha('/etc/ld.so.cache'), 'dpkg_status_sha256': sha('/var/lib/dpkg/status'),
               'usr_lib_i386_linux_gnu': Path('/usr/lib/i386-linux-gnu').exists(), 'mounts': int(run('sh', '-c', 'findmnt -rn | wc -l'))}
Out = Path(sys.argv[4]); Out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + '\n')
print('RESULTS matrix', len(res['matrix']), 'b13d', len(res['b13d']), 'b12', len(res['b12_non_regression']), res['defect3']['verify'][-1])
