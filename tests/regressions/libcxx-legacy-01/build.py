#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rebuild libc++ only, from the existing qualified core command graph."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--stage',required=True,type=Path)
p.add_argument('--output',required=True,type=Path)
a=p.parse_args();H=a.stage.resolve();O=a.output.resolve()
assert H.name=='libcxx-legacy-01' and H.parent.name=='validation'
assert O.is_relative_to(H);O.mkdir(exist_ok=False)
Q=H.parent/'upstream-sync-20261114';B=Q/'build-core-i386';old=Q/'src/src/external/libcxx';new=H/'libcxx-src'
assert subprocess.check_output(['git','-C',str(old),'rev-parse','HEAD'],text=True).strip()=='caf34a8ca7837354e7bd49f9ae28018943bb7dd3'
assert subprocess.check_output(['git','-C',str(new),'rev-parse','HEAD'],text=True).strip()=='061279ebb3944b11bbbc76ae7fd77077841f8c74'
for source in [old,new]:assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True)
assert subprocess.check_output(['git','-C',str(new),'diff','--name-only','caf34a8c','061279eb'],text=True).splitlines()==['include/__config_site']
lines=(H/'private/cxx-commands.txt').read_text().splitlines()
compiles=[shlex.split(l) for l in lines if '/libcxx/src/' in l and ' -c ' in l]
assert len(compiles)==46
linkline=shlex.split(next(l for l in lines if '-o src/external/libcxx/libc++.1.dylib ' in l))
link=linkline[2:linkline.index('&&',2)]
signer=B/'src/buildtools/adhoc-sign'
results=[]
for variant,source in [('baseline',old),('candidate',new)]:
    V=O/variant;V.mkdir();(V/'logs').mkdir();(V/'commands').mkdir()
    def compile_one(item):
        index,c=item;c=[x.replace(str(old),str(source)) for x in c]
        for flag in ['-o','-MF','-MT']:
            i=c.index(flag)+1;original=c[i];assert original.startswith('src/external/libcxx/CMakeFiles/cxx_obj.dir/')
            c[i]=str(V/Path(original).relative_to('src/external/libcxx/CMakeFiles/cxx_obj.dir'));Path(c[i]).parent.mkdir(parents=True,exist_ok=True)
        output=Path(c[c.index('-o')+1]);name=str(output.relative_to(V)).replace('/','_')
        (V/'commands'/(name+'.json')).write_text(json.dumps(c,indent=2)+'\n')
        r=subprocess.run(c,cwd=B,capture_output=True,text=True)
        (V/'logs'/(name+'.log')).write_text(r.stdout+r.stderr)
        assert r.returncode==0,(variant,name,r.stderr[-2000:])
        dep=Path(c[c.index('-MF')+1]);assert str(source/'include/__config_site') in dep.read_text(),name
        return {'object':str(output.relative_to(O)),'source':Path(c[c.index('-c')+1]).name,'rc':r.returncode,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for index,result in enumerate(pool.map(compile_one,enumerate(compiles)),1):
            results.append(result)
            if index%10==0 or index==46:print(variant,index,'/46 FAT objects',flush=True)
    c=[]
    for x in link:
        if x.startswith('src/external/libcxx/CMakeFiles/cxx_obj.dir/'):
            x=str(V/Path(x).relative_to('src/external/libcxx/CMakeFiles/cxx_obj.dir'))
        elif x=='src/external/libcxx/libc++.1.dylib':x=str(V/'libc++.1.dylib')
        elif x.startswith('src/') and x.endswith('.dylib'):x=str(B/x)
        else:x=x.replace(str(old),str(source))
        c.append(x)
    assert Path(c[c.index('-o')+1])==V/'libc++.1.dylib'
    (V/'commands/link.json').write_text(json.dumps(c,indent=2)+'\n')
    r=subprocess.run(c,cwd=B,capture_output=True,text=True);(V/'logs/link.log').write_text(r.stdout+r.stderr);assert r.returncode==0,(variant,r.stderr[-2500:])
    r=subprocess.run([str(signer),'--identifier=',str(V/'libc++.1.dylib')],capture_output=True,text=True);(V/'logs/sign.log').write_text(r.stdout+r.stderr);assert r.returncode==0
    print(variant,'LINK_SIGN_PASS',hashlib.sha256((V/'libc++.1.dylib').read_bytes()).hexdigest(),flush=True)
(O/'compile-results.json').write_text(json.dumps(results,indent=2)+'\n')
print('LIBCXX_BUILD_COMPLETE',O,flush=True)
