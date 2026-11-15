#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only facts on the ELF32 loader used by mldr32, and on what libc6:i386 would ship.

Usage: loader_facts.py INDEX_DIR MLDR32 OUT.json
Reads the filesystem, the dpkg database (dpkg -S / md5sums) and the verified
Contents-i386 index. Changes nothing.
"""
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

D, MLDR32, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])


def sha(p):
    with open(p, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def owner(p):
    r = subprocess.run(['dpkg', '-S', p], capture_output=True, text=True)
    return r.stdout.strip().splitlines()[0] if r.returncode == 0 else None


def path_fact(p):
    f = {'path': p, 'exists': os.path.lexists(p), 'symlink_target': os.readlink(p) if os.path.islink(p) else None,
         'realpath': os.path.realpath(p), 'owner': owner(p)}
    if os.path.isfile(p):
        f['sha256'] = sha(p)
    return f


interp = re.search(r'Requesting program interpreter: (\S+)\]',
                   subprocess.run(['readelf', '-l', MLDR32], capture_output=True, text=True).stdout).group(1)
facts = {'mldr32': {'sha256': sha(MLDR32), 'pt_interp': interp},
         'paths': [path_fact(p) for p in ['/lib', '/lib32', interp, '/usr/lib/ld-linux.so.2',
                                          '/usr/lib32/ld-linux.so.2', '/usr/lib32/libc.so.6',
                                          '/usr/lib32/libgcc_s.so.1', '/usr/lib/i386-linux-gnu',
                                          '/etc/ld.so.cache']],
         'lib32_loader_md5_matches_dpkg': None, 'ld_so_conf_d': {}, 'libc6_i386_contents': [],
         'foreign_architectures': subprocess.run(['dpkg', '--print-foreign-architectures'],
                                                 capture_output=True, text=True).stdout.split()}
md5 = hashlib.md5(open('/usr/lib32/ld-linux.so.2', 'rb').read()).hexdigest()
listed = Path('/var/lib/dpkg/info/libc6-i386.md5sums').read_text()
facts['lib32_loader_md5_matches_dpkg'] = f'{md5}  usr/lib32/ld-linux.so.2' in listed
for f in sorted(Path('/etc/ld.so.conf.d').glob('*.conf')):
    facts['ld_so_conf_d'][f.name] = {'dirs': [l.strip() for l in f.read_text().splitlines() if l.strip() and not l.lstrip().startswith('#')],
                                     'owner': owner(str(f))}
contents = D / 'raw' / 'trixie-main-Contents-i386.gz'
with gzip.open(contents, 'rt') as g:
    for line in g:
        path, _, pkgs = line.rstrip('\n').rpartition(' ')
        if 'libs/libc6' in pkgs.split(',') and re.search(r'(ld-linux|ld\.so\.conf\.d|/libc\.so\.6$)', path):
            facts['libc6_i386_contents'].append(path.strip())
OUT.write_text(json.dumps(facts, indent=2) + '\n')
print(json.dumps(facts, indent=1))
