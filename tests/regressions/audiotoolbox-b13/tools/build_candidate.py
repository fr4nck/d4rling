#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""B13 fixes: build a private AudioToolbox candidate from the B11E build tree, read-only.

  build_candidate.py BUILD_DIR COMPDB LINK_CMD OUT_DIR [ORIG_SOURCE=CANDIDATE_SOURCE ...]

Recompiles only the listed sources (FAT i386+x86_64, the exact compile command of the
build tree, with the candidate file substituted and every output redirected to
OUT_DIR), then relinks AudioToolbox with the exact link command (other objects taken
from the build tree as they are), signs it with the tree's adhoc-sign, and lays it out
as an overlay layer: OUT_DIR/layer/System/Library/Frameworks/AudioToolbox.framework/...
With no substitution it rebuilds the reference (procedure check). Asserts that no file
of the build tree changed (SHA-256 of every object, the linked framework and build.ninja).
"""
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path

G, COMPDB, LINK, OUT = (Path(a).resolve() for a in sys.argv[1:5])
SUBS = dict(a.split('=', 1) for a in sys.argv[5:])
OUT.mkdir()
(OUT / 'obj').mkdir()


def sha(p):
    with open(p, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


watch = sorted((G / 'src/CoreAudio/AudioToolbox/CMakeFiles/AudioToolbox.dir').glob('*.o')) + \
    [G / 'src/CoreAudio/AudioToolbox/AudioToolbox', G / 'build.ninja']
before = {str(p): sha(p) for p in watch}
log = {'build_dir': str(G), 'substitutions': SUBS, 'objects': {}, 'commands': []}

entries = json.loads(COMPDB.read_text())
replaced = {}
for orig, cand in SUBS.items():
    e = [x for x in entries if x['file'] == orig and '/AudioToolbox.dir/' in x['output']]
    assert len(e) == 1, orig
    e = e[0]
    argv = shlex.split(e['command'])
    obj = OUT / 'obj' / Path(e['output']).name
    new = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '-o':
            new += ['-o', str(obj)]; i += 2; continue
        if a == '-MF':
            new += ['-MF', str(obj) + '.d']; i += 2; continue
        if a == '-c' and argv[i + 1] == orig:
            new += ['-c', str(Path(cand).resolve())]; i += 2; continue
        new.append(a); i += 1
    assert str(Path(cand).resolve()) in new and str(obj) in new
    r = subprocess.run(new, cwd=e['directory'], capture_output=True, text=True)
    (OUT / (obj.name + '.log')).write_text(r.stdout + r.stderr)
    assert r.returncode == 0, (orig, r.stderr[-3000:])
    replaced[e['output']] = str(obj)
    log['objects'][e['output']] = {'candidate_source': str(Path(cand).resolve()), 'candidate_sha256': sha(cand),
                                   'object': str(obj), 'object_sha256': sha(obj)}
    log['commands'].append(new)

steps = [s.strip() for s in LINK.read_text().split('&&')]
assert steps[0] == ':' and steps[1].startswith('/usr/bin/clang++') and steps[3].split()[0].endswith('adhoc-sign')
argv = shlex.split(steps[1])
out_bin = OUT / 'AudioToolbox'
k = argv.index('-o')
assert argv[k + 1] == 'src/CoreAudio/AudioToolbox/AudioToolbox'
argv[k + 1] = str(out_bin)
argv = [replaced.get(a, a) for a in argv]
assert all(v in argv for v in replaced.values())
r = subprocess.run(argv, cwd=G, capture_output=True, text=True)
(OUT / 'link.log').write_text(r.stdout + r.stderr)
assert r.returncode == 0, r.stderr[-3000:]
sign = shlex.split(steps[3])
assert sign[-1].endswith('/src/CoreAudio/AudioToolbox/AudioToolbox')
sign[-1] = str(out_bin)
r = subprocess.run(sign, cwd=OUT, capture_output=True, text=True)
(OUT / 'sign.log').write_text(r.stdout + r.stderr)
assert r.returncode == 0, r.stderr
layer = OUT / 'layer/System/Library/Frameworks/AudioToolbox.framework/Versions/A'
layer.mkdir(parents=True)
(layer / 'AudioToolbox').write_bytes(out_bin.read_bytes())
log['link_command'] = argv
log['audiotoolbox_sha256'] = sha(out_bin)
log['reference_build_sha256'] = before[str(G / 'src/CoreAudio/AudioToolbox/AudioToolbox')]
after = {str(p): sha(p) for p in watch}
assert before == after, 'build tree changed'
log['build_tree_unchanged'] = True
(OUT / 'candidate.json').write_text(json.dumps(log, indent=2) + '\n')
print('CANDIDATE', OUT.name, 'audiotoolbox_sha256=' + log['audiotoolbox_sha256'],
      'reference_build_sha256=' + log['reference_build_sha256'], 'objects=' + ','.join(
          f"{Path(k).name}:{v['object_sha256'][:12]}" for k, v in log['objects'].items()))
