#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rebuild/replay MLD-ASLR-01 against the preserved private core/S4 bank."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--stage',required=True,type=Path)
p.add_argument('--run',action='store_true')
a=p.parse_args();H=a.stage.resolve();HERE=Path(__file__).resolve().parent
assert H.name=='mld-aslr-01' and H.parent.name=='validation'
S=H/'src';Q=H.parent/'upstream-sync-20261114';B=Q/'build-core-i386'
assert subprocess.check_output(['git','-C',str(S),'symbolic-ref','--short','HEAD'],text=True).strip()=='master'
O=H/('replay-'+str(time.time_ns()));O.mkdir()
for name in ['logs','commands','bin','build']:(O/name).mkdir()
for name in ['baseline','candidate']:(O/'build'/name).mkdir()

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def call(c,name,**kwargs):
    r=subprocess.run([str(x) for x in c],capture_output=True,text=True,**kwargs)
    (O/'logs'/(name+'.log')).write_text(r.stdout+r.stderr)
    assert r.returncode==0,(name,r.returncode,r.stderr[-1500:])
    return r.stdout

sources=json.loads((HERE/'sources.json').read_text())
assert sha(S/'src/startup/mldr/mldr.c')==sources['candidate_sha256']
for n,expected in json.loads((HERE/'stage-inputs.json').read_text()).items():assert sha(H/n)==expected,n
for n,expected in json.loads((HERE/'link-inputs.json').read_text()).items():assert sha(B/n)==expected,n
assert subprocess.check_output(['git','-C',str(Q/'src'),'rev-parse','HEAD'],text=True).strip()==sources['qualified_build_source']
assert not subprocess.check_output(['git','-C',str(S),'diff',sources['qualified_build_source'],sources['base'],'--','src/startup/mldr'],text=True)
assert subprocess.check_output(['git','hash-object',str(S/'tests/spawn-i386-flags.c')],text=True).strip()==sources['upstream_test']['sha']
# The only source changes are the upstream include and its block, after the
# strict budget check in ensure_top_range_free; an early clear in reexec32 fails.
candidate=(S/'src/startup/mldr/mldr.c').read_text();base=(H/'private/baseline-mldr.c').read_text()
start=candidate.index('static void ensure_top_range_free(')
block_start=candidate.index('\t// Without address space randomization')
block_end=candidate.index('\tchar selfpath[1024];',block_start)
assert block_start>start
assert candidate.replace('#include <sys/personality.h>\n','',1).replace(candidate[block_start:block_end],'',1)==base
protected=[Path('/etc/ld.so.cache'),Path('/var/lib/dpkg/status'),Path('/proc/sys/vm/mmap_min_addr'),Path('/proc/sys/kernel/randomize_va_space')]
before={str(x):sha(x) for x in protected}

# Reuse only identical unchanged objects from the qualified core build. All
# compilation, links and dependency files go to this new output, never to B.
for variant in ['baseline','candidate']:
    for program in ['mldr32','mldr']:
        for step in ['compile','link']:
            c=json.loads((H/'commands'/(variant+'-'+program+'-'+step+'.json')).read_text())
            c=[x.replace(str(H/'build')+'/',str(O/'build')+'/') for x in c]
            for flag in ['-o','-MF','-MT']:
                if flag in c:assert Path(c[c.index(flag)+1]).is_relative_to(O)
            (O/'commands'/(variant+'-'+program+'-'+step+'.json')).write_text(json.dumps(c,indent=2)+'\n')
            call(c,variant+'-'+program+'-'+step,cwd=B)
for name,source in [('spawn-i386-flags',S/'tests/spawn-i386-flags.c'),('counter-spawn',HERE/'counter-spawn.c'),('child-i386',HERE/'child.c')]:
    for step in ['compile','link']:
        c=json.loads((H/'commands'/(name+'-'+step+'.json')).read_text())
        c=[x.replace(str(H/'bin')+'/',str(O/'bin')+'/') for x in c]
        if step=='compile':c[c.index('-c')+1]=str(source)
        for flag in ['-o','-MF']:
            if flag in c:assert Path(c[c.index(flag)+1]).is_relative_to(O)
        (O/'commands'/(name+'-'+step+'.json')).write_text(json.dumps(c,indent=2)+'\n')
        call(c,name+'-'+step)
call(['python3',HERE/'test-guard.py','--source',S/'src/startup/mldr/mldr.c','--output',O/'guards'],'guard-tests')
text_hashes={}
for program in ['mldr','mldr32']:
    text_hashes[program]={}
    for variant in ['baseline','candidate']:
        out=O/(variant+'-'+program+'.text')
        call(['objcopy','--dump-section','.text='+str(out),O/'build'/variant/program],variant+'-'+program+'-text')
        text_hashes[program][variant]=sha(out)
assert text_hashes['mldr']['baseline']==text_hashes['mldr']['candidate']
negatives=[]
for program in ['mldr32','mldr']:
    for state,value,marker in [('missing',None,'__mldr_sockpath is missing'),('empty','','__mldr_sockpath is missing'),('set','/nonexistent.sock','Cannot open /nonexistent')]:
        env={'PATH':'/usr/bin:/bin','HOME':str(H/'home'),'LANG':'C.UTF-8'}
        if value is not None:env['__mldr_sockpath']=value
        c=[str(O/'build/candidate'/program),'/nonexistent']
        r=subprocess.run(c,env=env,capture_output=True,text=True,timeout=5)
        assert r.returncode==1 and marker in r.stdout+r.stderr,(program,state,r)
        negatives.append({'program':program,'state':state,'rc':r.returncode,'stderr':r.stderr})

records=[]
if a.run:
    cases=[('baseline','official-before','spawn-i386-flags','normal',1,'FAIL: i386 child spawned with no-ASLR'),
           ('candidate','official-after','spawn-i386-flags','normal',0,'PASS: i386 child spawned with no-ASLR'),
           ('candidate','counter-real','counter-spawn','normal',0,'MLD_COUNTER_REAL_PASS cases=12 failures=0'),
           ('candidate','home-normal','witness','normal',0,'HOME_RES_I386_PASS checks=88 failures=0'),
           ('candidate','home-bypass','witness','bypass',0,'HOME_RES_I386_PASS checks=88 failures=0'),
           ('candidate','carbon-normal','carbon','normal',0,'D4RLING-CARBON-EVENT-I386-OK'),
           ('candidate','carbon-bypass','carbon','bypass',0,'D4RLING-CARBON-EVENT-I386-OK')]
    env=dict(os.environ,MLD_ASLR_STAGE=str(H),MLD_ASLR_BUILD=str(O/'build'),MLD_ASLR_BIN=str(O/'bin'))
    for variant,name,program,mode,expected,marker in cases:
        label='mld-'+O.name+'-'+name
        call(['bash',HERE/'run-guest.sh',variant,label,program,mode],name,env=env)
        run=H/'runs'/label;rc=int((run/'rc').read_text());out=(run/'stdout.log').read_text();err=(run/'stderr.log').read_text()
        assert rc==expected and marker in out,(name,rc,out[-1000:],err[-1000:])
        if name=='official-before':assert out.count('FAIL:')==1 and 'Cannot mmap commpage: File exists' in err
        if name=='official-after':assert out.count('PASS:')==9 and 'FAIL:' not in out
        if name=='counter-real':assert err.count('Cannot mmap commpage: File exists')==8
        meta=dict(x.split('=',1) for x in (run/'meta.txt').read_text().splitlines() if '=' in x)
        assert meta['host_mounts_before']==meta['host_mounts_after']
        teardown=json.loads((run/'teardown.json').read_text());assert not teardown['remaining']
        observation=json.loads((run/'native-images.json').read_text())
        allowed={(sha(O/'build'/variant/'mldr32'),32),(sha(O/'build'/variant/'mldr'),64)}
        observed={(x[2],x[3]) for x in observation['images']}
        assert observed and observed<=allowed,(name,observed,allowed)
        if name in ['official-before','official-after','counter-real']:
            assert any(bits==32 for digest,bits in observed),name
        records.append({'name':name,'variant':variant,'mode':mode,'rc':rc,'expected_rc':expected,'label':label,
                        'binary_sha256':meta['program_sha256'],'native_images':sorted(observed),
                        'personality_values_observed':sorted({x[2] for x in observation['personalities']}),
                        'namespace_remaining':teardown['remaining'],'host_mounts':[meta['host_mounts_before'],meta['host_mounts_after']]})
        (O/'native-results.json').write_text(json.dumps(records,indent=2)+'\n')
        print(name,'OBSERVED_EXPECTED_FAILURE' if expected else 'PASS','rc='+str(rc),flush=True)
assert before=={str(x):sha(x) for x in protected}
for n,expected in json.loads((HERE/'link-inputs.json').read_text()).items():assert sha(B/n)==expected,n
report={'verdict':'MLD_ASLR_01_PASS' if a.run else 'BUILD_AND_HOST_TESTS_ONLY','sources':sources,'runs':records,
        'host_negatives':negatives,'elf_text_sha256':text_hashes,'protected_host_files_unchanged':before,
        'binaries':{variant:{name:sha(O/'build'/variant/name) for name in ['mldr32','mldr']} for variant in ['baseline','candidate']}}
(O/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(report['verdict'],O,flush=True)
