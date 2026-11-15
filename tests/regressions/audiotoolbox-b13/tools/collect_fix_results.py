#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""B13 (i386 phase and fixes): gather the executed results without personal paths.
Usage: collect_fix_results.py B13_STAGE AUDIO_STAGE B12_STAGE OUT.json"""
import hashlib, json, re, subprocess, sys
from pathlib import Path
T, A, B = (Path(x) for x in sys.argv[1:4])
H = str(Path.home())
def x(s): return s.replace(str(T), '<B13_STAGE>').replace(str(A), '<AUDIO_STAGE>').replace(str(B), '<B12_STAGE>').replace(H, '~')
def find(rx, s, g=1):
    m = re.search(rx, s, re.M)
    return m.group(g) if m else None
def guest(l):
    g = T / 'runs/guest' / l; m = (g / 'meta.txt').read_text(); err = (g / 'stderr.log').read_text(); so = (g / 'stdout.log').read_text()
    return {'label': l, 'rc': int((g / 'rc').read_text()), 'program_sha256': find(r'program=\S+ sha256=(\w+)', m),
            'args': x(find(r'^args=(.*)$', m) or ''), 'layer': x(find(r'^layer=(.*)$', m) or ''),
            'ns_ldcache': find(r'ns_ldcache=(\w+)', err), 'ns_audiotoolbox': find(r'ns_audiotoolbox=(\w+)', err),
            'summary': [s for s in so.splitlines() if 'SUMMARY' in s], 'last_enter': ([s for s in so.splitlines() if s.startswith('B13FIX_ENTER')] or [None])[-1],
            'failures': [s for s in so.splitlines() if ' FAIL ' in s],
            'end': re.findall(r'(host_mounts_after=\d+|darlingserver_after=\d+|residual_prefix_processes=\d+)', m)}
def verify(l, kind):
    a = ['python3', '-I', str(T / 'probe/verify_b13.py'), str(T / 'media'), str(T / 'runs/out' / l), str(T / 'runs/guest' / l / 'stdout.log')] \
        if kind == 'probe' else ['python3', '-I', str(T / 'probe/verify_b13_fix.py'), str(T / 'media'), str(T / 'runs/out' / l), kind]
    return subprocess.run(a, capture_output=True, text=True).stdout.splitlines()
def bitexact(ref, cap, start=None):
    return subprocess.run(['python3', '-I', str(B / 'probe/bitexact.py'), str(ref), str(cap)] + ([str(start)] if start else []), capture_output=True, text=True).stdout.strip()
def play(l, root, ref):
    d = root / l; s = (d / 'summary.txt').read_text()
    e = {'label': l, 'summary': [ln for ln in x(s).splitlines() if not ln.startswith('  seq')],
         'guest': [ln for ln in (d / 'guest.stdout.log').read_text().splitlines() if ln.startswith(('B13 ', 'B12 natural', 'B12 stop', 'B12 delivered'))],
         'ns_audiotoolbox': find(r'ns_audiotoolbox=(\w+)', (d / 'guest.stderr.log').read_text()), 'bitexact': bitexact(ref, d / 'monitor.raw')}
    if 'mode=stoprestart' in s:
        a = int(find(r'alignment_frame=(\d+)', e['bitexact']))
        e['bitexact_second_pass'] = bitexact(ref, d / 'monitor.raw', a + 44100)
    return e
P = T / 'private-ffmpeg-20261115'
elf = json.loads((P / 'elf32.json').read_text())
res = {'private_ffmpeg': {'packages': len(list((P / 'packages').glob('*.deb'))), 'bytes': sum(f.stat().st_size for f in (P / 'packages').glob('*.deb')),
                          'ld_so_conf': x((P / 'ld.so.conf').read_text()).splitlines(),
                          'ld_so_cache_sha256': hashlib.sha256((P / 'ld.so.cache').read_bytes()).hexdigest(),
                          'elf32_images': len(elf), 'unresolved': [e['file'] for e in elf if e['unresolved']]},
       'mapped_in_i386_guest_i3': [dict(zip(['process', 'sha256', 'file'], x(l).split(' ', 2))) for l in (T / 'runs/maps/i3.txt').read_text().splitlines()]}
res['i386_probe'] = []
for l in ['i2', 'i3']:
    r = guest(l); r['verify'] = verify(l, 'probe')
    r['guest'] = [s for s in (T / 'runs/guest' / l / 'stdout.log').read_text().splitlines() if s.startswith(('B13_IMAGE', 'B13_READABLE', 'B13_OBS', 'B13_LOADED', 'B13_PROPS'))]
    r['outputs_sha256'] = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((T / 'runs/out' / l).iterdir())}
    res['i386_probe'].append(r)
aiff, ulaw = T / 'media/ref-s16be.raw', T / 'media/ref-ulaw-s16be.raw'
res['i386_play'] = [play(l, T / 'runs/play', aiff) for l in ['di1', 'di2', 'di3', 'di4', 'di5']]
res['b13d_candidates'] = [play(l, T / 'runs/play', ulaw if l.endswith(('u', 's')) else aiff) for l in ['d1a', 'd1u', 'd2a', 'd3a', 'd3u', 'd3s', 'dx4u']]
res['b12_non_regression'] = []
for l in ['n1p', 'n2p', 'n3p', 'n3s']:
    res['b12_non_regression'].append(play(l, A / 'runs/b12', A / 'runs/b12' / l / 'gms.pcm'))
res['fix_matrix'] = []
for l in ['f1ri', 'f2ri', 'f1rx', 'f2rx', 'f1ci', 'f1cx', 'p1ci', 'p1cx', 'f2ci', 'f2cx', 'cbci', 'cbcx', 'p2ci', 'p2cx', 'p3ci', 'p3cx', 'f13i', 'f13x', 'f23i', 'f23x']:
    r = guest(l)
    kind = 'fix1' if l.startswith('f1') else 'fix2' if l.startswith('f2') else 'probe' if l.startswith('p') else None
    if kind and r['rc'] != 139:
        r['verify'] = verify(l, kind)
    if l.startswith('cb'):
        r['observation'] = [s for s in (T / 'runs/guest' / l / 'stdout.log').read_text().splitlines() if 'convertbuffer' in s]
    res['fix_matrix'].append(r)
res['candidates'] = {}
for c in ['ref', 'ref0', 'fix1', 'fix2', 'fix12']:
    j = json.loads((T / 'fix' / ('cand-' + c) / 'candidate.json').read_text())
    res['candidates'][c] = {'audiotoolbox_sha256': j['audiotoolbox_sha256'], 'reference_build_sha256': j['reference_build_sha256'],
                            'objects': {Path(k).name: {'candidate_source_sha256': v['candidate_sha256'], 'object_sha256': v['object_sha256']} for k, v in j['objects'].items()},
                            'build_tree_unchanged': j['build_tree_unchanged']}
Path(sys.argv[4]).write_text(json.dumps(res, indent=2, ensure_ascii=False) + '\n')
print('RESULTS', len(res['fix_matrix']), 'matrix runs')
