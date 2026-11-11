#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile two contract-breaking modifications in temporary copies and require assertion failure."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
SUITE = Path(__file__).resolve().parent
SOURCE = ROOT / 'src/frameworks/CoreServices/src/CarbonCore/ResourcesImpl.cpp'
MEMORY = ROOT / 'src/frameworks/CoreServices/src/CarbonCore/MacMemory.cpp'
INC = ROOT / 'src/frameworks/CoreServices/include'
ORACLE = SUITE / 'test_rehydrate.cpp'
MUTANTS = (
 ('no automatic reload', 'else if (!*data)', 'else if (false && !*data)'),
 ('omit backing data copy', 'std::memcpy(*data, dataBacking.data(), dataBacking.size());', '(void)dataBacking.size();'),
)

def run(compiler):
    source = SOURCE.read_text(encoding='utf8')
    oracle_bytes = ORACLE.read_bytes()
    import hashlib
    oracle_blob = hashlib.sha1(b'blob '+str(len(oracle_bytes)).encode()+b'\0'+oracle_bytes).hexdigest()
    if oracle_blob != '598d801c19286faec5f9b05059e03d677f958a98':
        raise RuntimeError('I1 negative oracle changed')
    import hashlib
    encoded = source.encode('utf8')
    blob = hashlib.sha1(b'blob '+str(len(encoded)).encode()+b'\0'+encoded).hexdigest()
    if blob != 'f176a1f86d41a772b7fa034788dae2a4889a70eb':
        raise RuntimeError('production source changed: requalify mutants')
    with tempfile.TemporaryDirectory(prefix='d4-i1-mut-') as temporary:
        tmp = Path(temporary)
        for index,(name,needle,changed) in enumerate(MUTANTS,1):
            if source.count(needle)!=1:
                raise RuntimeError(f'ambiguous/missing mutation {name}')
            candidate=tmp/f'resources-mutant-{index}.cpp'
            candidate.write_text(source.replace(needle,changed,1),encoding='utf8')
            exe=tmp/f'contract-{index}'
            args=[compiler,'-std=c++17','-O0','-g0','-Wall','-Wextra','-Werror',
                  '-Wno-unused-parameter','-pthread','-fno-omit-frame-pointer',
                  '-fsanitize=address,undefined',f'-I{SUITE / "shims"}',f'-I{INC}',
                  f'-I{SOURCE.parent}',str(MEMORY),str(candidate),str(ORACLE),
                  '-Wl,--wrap=malloc','-o',str(exe)]
            build=subprocess.run(args,capture_output=True,text=True,timeout=55)
            if build.returncode:
                raise RuntimeError(f'mutant {name} did not compile: {build.stderr[-1300:]}')
            env=os.environ.copy()
            env.update(ASAN_OPTIONS='detect_leaks=1', UBSAN_OPTIONS='halt_on_error=1')
            trial=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15,env=env)
            if trial.returncode!=1 or 'I1_MUTANT_DETECTED' not in trial.stderr:
                raise RuntimeError(f'mutant {name} survived or crashed: rc={trial.returncode}\nstdout={trial.stdout[-600:]}\nstderr={trial.stderr[-1600:]}')
            print(f'I1_MUTANT_{index}: KILLED ({name})')
    print(f'I1_MUTANTS: {len(MUTANTS)}/{len(MUTANTS)} killed by assertions ({compiler})')

if __name__=='__main__':
    try: run(sys.argv[1] if len(sys.argv)>1 else 'g++')
    except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
        print(f'BLOCKED: {exc}',file=sys.stderr)
        sys.exit(2)
