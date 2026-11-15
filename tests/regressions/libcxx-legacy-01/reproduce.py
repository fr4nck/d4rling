#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Private Darwin libc++ ABI qualification; no package installation or app launch."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import time

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--stage',required=True,type=Path)
p.add_argument('--run',action='store_true')
p.add_argument('--rebuild',action='store_true',help='rebuild libc++ and witnesses in fresh private output')
a=p.parse_args();H=a.stage.resolve();assert H.name=='libcxx-legacy-01' and H.parent.name=='validation'
HERE=Path(__file__).resolve().parent;Q=H.parent/'upstream-sync-20261114';S=H/'src'
O=H/('replay-'+str(time.time_ns()));O.mkdir();(O/'logs').mkdir()
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def call(c,log,**kw):
    r=subprocess.run([str(x) for x in c],capture_output=True,text=True,**kw)
    (O/'logs'/(log+'.log')).write_text(r.stdout+r.stderr)
    assert r.returncode==0,(log,r.returncode,r.stderr[-1800:])
    return r.stdout
sources=json.loads((HERE/'sources.json').read_text())
assert subprocess.check_output(['git','-C',str(S),'symbolic-ref','--short','HEAD'],text=True).strip()=='master'
for base,name in [(H,'stage-inputs.json'),(Q,'link-inputs.json')]:
    for relative,expected in json.loads((HERE/name).read_text()).items():assert sha(base/relative)==expected,relative
assert subprocess.check_output(['git','-C',str(Q/'src'),'rev-parse','HEAD'],text=True).strip()==sources['qualified_core_source']
module=H/'libcxx-src';assert subprocess.check_output(['git','-C',str(module),'rev-parse','HEAD'],text=True).strip()==sources['libcxx_after']
assert not subprocess.check_output(['git','-C',str(module),'status','--porcelain'],text=True)
assert subprocess.check_output(['git','hash-object',str(S/'tests/libcxx-legacy-exports.c')],text=True).strip()==sources['test_origin']['sha']
regressions=json.loads((HERE/'regressions.json').read_text())
for r in regressions:
    assert subprocess.check_output(['git','hash-object',str(module/r['path'])],text=True).strip()==r['git_blob']
protected=[Path('/etc/ld.so.cache'),Path('/var/lib/dpkg/status'),Path('/proc/sys/vm/mmap_min_addr'),Path('/proc/sys/kernel/randomize_va_space')]
before={str(x):sha(x) for x in protected}
libroot=H/'build/full';binroot=H/'bin'
if a.rebuild:
    call(['python3',HERE/'build.py','--stage',H,'--output',O/'libraries'],'build-libraries')
    libroot=O/'libraries'
    call(['python3',HERE/'build-witnesses.py','--stage',H,'--output',O/'witnesses','--library',libroot/'candidate/libc++.1.dylib'],'build-witnesses')
    binroot=O/'witnesses/bin'
expected=['_ZNSt3__119__shared_weak_count12__add_sharedEv','_ZNSt3__119__shared_weak_count10__add_weakEv','_ZNSt3__119__shared_weak_count16__release_sharedEv','_ZNSt3__114__shared_count12__add_sharedEv','_ZNSt3__114__shared_count16__release_sharedEv']
images={};exports={};delta={}
for variant in ['baseline','candidate']:
    images[variant]={};exports[variant]={};library=libroot/variant/'libc++.1.dylib'
    for arch in ['i386','x86_64']:
        text=call(['llvm-objdump-19','--macho','--arch='+arch,'--exports-trie',library],variant+'-'+arch+'-exports')
        names={m.group(1) for l in text.splitlines() if (m:=re.match(r'^0x[0-9A-Fa-f]+\s+(\S+)',l))};exports[variant][arch]=names
        assert all(('_'+x in names)==(variant=='candidate') for x in expected)
        header=call(['llvm-objdump-19','--macho','--arch='+arch,'--private-headers',library],variant+'-'+arch+'-headers')
        uuids=re.findall(r'uuid\s+([A-Fa-f0-9-]{36})',header);assert len(uuids)==1
        images[variant][arch]={'uuid':uuids[0],'sha256':sha(library),'export_count':len(names)}
for arch in ['i386','x86_64']:
    removed=exports['baseline'][arch]-exports['candidate'][arch];assert not removed
    delta[arch]={'added':sorted(exports['candidate'][arch]-exports['baseline'][arch]),'removed':sorted(removed)}
records=[]
if a.run:
    env=dict(os.environ,LIBCXX_LEGACY_STAGE=str(H),LIBCXX_LEGACY_LIBROOT=str(libroot),LIBCXX_LEGACY_BIN=str(binroot))
    for arch in ['i386','x86_64']:
        for name in ['legacy','bindings']+[x['name'] for x in regressions]:
            program=name+'-'+arch;binary=binroot/program
            with binary.open('rb') as f:ident=f.read(8)
            assert struct.unpack_from('<I',ident,4)[0]==(7 if arch=='i386' else 0x1000007)
            if name not in ['legacy','bindings']:
                undefined=call(['llvm-nm-19','--undefined-only',binary],program+'-assertions')
                assert 'assert_rtn' in undefined,program
            for variant in ['baseline','candidate']:
                label='cxx-'+O.name+'-'+variant+'-'+program.replace('_','-')
                call(['bash',HERE/'run-guest.sh',variant,label,program,'normal'],label,env=env)
                run=H/'runs'/label;rc=int((run/'rc').read_text());out=(run/'stdout.log').read_text();err=(run/'stderr.log').read_text()
                image=images[variant][arch];assert 'dyld: loaded: <'+image['uuid']+'> /usr/lib/libc++.1.dylib' in err
                expectation='EXPECTED_FAILURE' if variant=='baseline' and name in ['legacy','bindings'] else 'PASS'
                if name=='legacy':assert rc==(1 if variant=='baseline' else 0) and out.count(('FAIL' if variant=='baseline' else 'PASS')+': export ')==5
                elif name=='bindings' and variant=='baseline':assert rc==134 and 'Symbol not found' in err
                elif name=='bindings':assert rc==0 and 'LEGACY_STRONG_BIND_PASS count=5' in out
                else:assert rc==0,(name,arch,variant,out[-700:],err[-1300:])
                meta=dict(x.split('=',1) for x in (run/'meta.txt').read_text().splitlines() if '=' in x)
                assert meta['library_sha256']==image['sha256']
                assert meta['host_mounts_before']==meta['host_mounts_after']
                assert not json.loads((run/'teardown.json').read_text())['remaining']
                records.append({'name':name,'arch':arch,'variant':variant,'label':label,'rc':rc,'status':expectation,
                                'binary_sha256':sha(binary),'library':image,'host_mounts':[meta['host_mounts_before'],meta['host_mounts_after']],'remaining_pids':[]})
                (O/'native-results.json').write_text(json.dumps(records,indent=2)+'\n')
                print(program,variant,expectation,'rc='+str(rc),flush=True)
assert before=={str(x):sha(x) for x in protected}
for base,name in [(H,'stage-inputs.json'),(Q,'link-inputs.json')]:
    for relative,expected in json.loads((HERE/name).read_text()).items():assert sha(base/relative)==expected,relative
report={'verdict':'LIBCXX_LEGACY_01_PASS' if a.run else 'INPUTS_AND_EXPORTS_VERIFIED_ONLY','sources':sources,'images':images,'exports':delta,'runs':records,'regressions':regressions,'protected_host_files_unchanged':before}
(O/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(report['verdict'],O,flush=True)
