#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""B13: DT_NEEDED closure of host amd64 libraries (proxy for the same Debian versions in i386).
Usage: elf_closure_amd64.py OUT.json SONAME...   Read-only (readelf, dpkg -S)."""
import json, os, re, subprocess, sys
base = '/usr/lib/x86_64-linux-gnu'
def find(n, runpath):
    for d in runpath + [base, '/lib/x86_64-linux-gnu']:
        p = os.path.join(d, n)
        if os.path.exists(p):
            return p
seen, todo = {}, [(n, []) for n in sys.argv[2:]]
while todo:
    n, rp = todo.pop()
    if n in seen:
        continue
    p = find(n, rp)
    if not p:
        seen[n] = None; continue
    out = subprocess.run(['readelf', '-d', p], capture_output=True, text=True).stdout
    need = re.findall(r'\(NEEDED\).*\[(.+?)\]', out)
    runpath = [x for r in re.findall(r'\((?:RUNPATH|RPATH)\).*\[(.+?)\]', out) for x in r.split(':')]
    real = os.path.realpath(p)
    pkg = subprocess.run(['dpkg', '-S', real], capture_output=True, text=True).stdout.split(':')[0] or \
          subprocess.run(['dpkg', '-S', p], capture_output=True, text=True).stdout.split(':')[0]
    seen[n] = {'path': real, 'package': pkg, 'needed': need, 'runpath': runpath}
    todo += [(x, runpath) for x in need]
json.dump(seen, open(sys.argv[1], 'w'), indent=2)
pk = sorted({v['package'] for v in seen.values() if v})
print('SONAMES', len(seen), 'MISSING', [k for k, v in seen.items() if v is None])
print('PACKAGES', len(pk)); print(' '.join(pk))
