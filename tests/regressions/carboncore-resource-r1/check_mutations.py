#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test-only source mutations: each must break a host assertion, not compilation."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'src/frameworks/CoreServices/src/CarbonCore/ResourcesImpl.cpp'
RUNNER=Path(__file__).with_name('run.sh')
MUTANTS=(
    ('wrong map attributes',
     'm_attributes = static_cast<ResFileAttributes>(be16(map + 22));',
     'm_attributes = 0;'),
    ('wrong resource attributes',
     'res.attributes = static_cast<ResAttributes>(reference[4]);',
     'res.attributes = 0;'),
    ('truncate high-bit Pascal names',
     'const size_t nameLength = map[namePos];',
     'const size_t nameLength = map[namePos] & 0x7f;'),
    ('accept duplicate resource IDs',
     'if (!typeData.idMap.emplace(entry->id, entry).second)',
     'if (!typeData.idMap.emplace(entry->id, entry).second && false)'),
    ('free removed resource handle',
     'target->releaseHandle(false);',
     'target->releaseHandle(true);'),
)
def main():
    compiler = sys.argv[1] if len(sys.argv)>1 else 'g++'
    text=SOURCE.read_text(encoding='utf8')
    with tempfile.TemporaryDirectory(prefix='d4-carbon-r1-mutants-') as temp:
        for i,(name,old,new) in enumerate(MUTANTS,1):
            if text.count(old)!=1: raise RuntimeError('ambiguous mutation: '+name)
            target=Path(temp)/f'mutant-{i}.cpp'
            target.write_text(text.replace(old,new,1),encoding='utf8')
            env=dict(os.environ,D4_R1_TEST_SOURCE=str(target))
            r=subprocess.run(['bash',str(RUNNER),compiler],env=env,text=True,
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                             timeout=40,check=False)
            if r.returncode!=1 or 'FAIL line ' not in r.stderr:
                raise RuntimeError('mutation did not fail assertions: '+name+'\n'+
                                   f'rc={r.returncode} stdout={r.stdout[-500:]} stderr={r.stderr[-800:]}')
            print(f'R1_MUTANT_{i}_KILLED: {name}')
        print(f'R1_MUTANTS: {len(MUTANTS)}/{len(MUTANTS)} killed ({compiler})')
if __name__=='__main__':
    try: main()
    except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
        print('BLOCKED: '+str(exc),file=sys.stderr)
        sys.exit(2)
