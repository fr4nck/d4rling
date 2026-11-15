#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test the extracted production retry function with controlled syscall failures."""
import argparse
import json
from pathlib import Path
import subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source',required=True,type=Path)
p.add_argument('--output',required=True,type=Path)
a=p.parse_args();a.output.mkdir(exist_ok=False)
s=a.source.read_text();start=s.index('static void ensure_top_range_free(');brace=s.index('{',start);depth=1;end=brace+1
while depth:
    if s[end]=='{':depth+=1
    elif s[end]=='}':depth-=1
    end+=1
function=s[start:end]
assert function.index('personality(0xffffffff)')>function.index('if (retries >= LAYOUT_RETRY_MAX)')
assert 'if (setenv(LAYOUT_RETRY_ENV, count, 1) != 0)' in function
fixture=Path(__file__).with_name('guard-harness.c.in').read_text().replace('/* MLDR_FUNCTION */',function)
c=a.output/'guard.c';c.write_text(fixture);results=[]
for compiler in ['gcc','clang-19']:
    for arch in ['64','32']:
        out=a.output/(compiler+'-'+arch)
        command=[compiler,'-std=c11','-Wall','-Wextra','-Werror','-g','-m'+arch,str(c),'-o',str(out)]
        build=subprocess.run(command,capture_output=True,text=True)
        (a.output/(out.name+'-compile.log')).write_text(build.stdout+build.stderr)
        assert build.returncode==0,(command,build.stderr)
        run=subprocess.run([str(out)],capture_output=True,text=True,timeout=10)
        (a.output/(out.name+'-run.log')).write_text(run.stdout+run.stderr)
        results.append({'command':command,'rc':run.returncode,'output':run.stdout})
        assert run.returncode==0 and 'MLD_ASLR_GUARD_PASS' in run.stdout,(command,run.stdout,run.stderr)
        print(out.name,run.stdout.strip(),flush=True)
(a.output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
