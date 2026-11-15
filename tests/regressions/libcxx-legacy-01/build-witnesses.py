#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
import argparse
import json
from pathlib import Path
import shlex
import subprocess
p=argparse.ArgumentParser()
p.add_argument('--stage',required=True,type=Path)
p.add_argument('--output',required=True,type=Path)
p.add_argument('--library',required=True,type=Path)
a=p.parse_args();H=a.stage.resolve();O=a.output.resolve();assert O.is_relative_to(H);O.mkdir(exist_ok=False)
for n in ['bin','logs','commands']:(O/n).mkdir()
HERE=Path(__file__).resolve().parent;Q=H.parent/'upstream-sync-20261114';B=Q/'build-core-i386';module=H/'libcxx-src';old=Q/'src/src/external/libcxx';s4=H.parent/'security-s4-logic-l1-20261114'
cc_base=shlex.split(next(l for l in (H/'private/cxx-commands.txt').read_text().splitlines() if '/libcxx/src/' in l and ' -c ' in l))
records=[]
for arch in ['i386','x86_64']:
    template='native-freetype-'+arch
    c_compile=json.loads((s4/'commands'/(template+'-compile.json')).read_text())
    c_link=json.loads((s4/'commands'/(template+'-link.json')).read_text())
    programs=[('legacy',H/'src/tests/libcxx-legacy-exports.c',False),('bindings',HERE/'strong-bindings.c',False)]
    programs += [(x['name'],module/x['path'],True) for x in json.loads((HERE/'regressions.json').read_text())]
    for name,source,cpp in programs:
        target=name+'-'+arch;obj=O/'bin'/(target+'.o');exe=O/'bin'/target
        if cpp:
            original=cc_base;c=[];i=0
            while i<len(original):
                value=original[i]
                if value=='-arch':i+=2;continue
                if value in ['-D_LIBCPP_BUILDING_LIBRARY=1','-DLIBCXX_BUILDING_LIBCXXABI=1','-fvisibility=hidden','-fvisibility-inlines-hidden']:i+=1;continue
                c.append(value.replace(str(old),str(module)));i+=1
            for j,value in enumerate(c):
                if value=='-target':c[j+1]=arch+'-apple-darwin20'
            c+=['-I'+str(module/'test/support')]
            c[c.index('-MT')+1]=str(obj)
        else:c=list(c_compile)
        c[c.index('-c')+1]=str(source);c[c.index('-o')+1]=str(obj);c[c.index('-MF')+1]=str(O/'bin'/(target+'.d'))
        link=[str(exe) if x==str(s4/'bin'/template) else str(obj) if x==str(s4/'bin'/(template+'.o')) else x for x in c_link]
        link+=[str(a.library.resolve()),str(B/'src/external/libcxxabi/libc++abi.dylib')]
        if name=='bindings':link+=['-Wl,-bind_at_load']
        for step,command in [('compile',c),('link',link)]:
            (O/'commands'/(target+'-'+step+'.json')).write_text(json.dumps(command,indent=2)+'\n')
            r=subprocess.run(command,cwd=B,capture_output=True,text=True);(O/'logs'/(target+'-'+step+'.log')).write_text(r.stdout+r.stderr)
            records.append({'program':target,'step':step,'rc':r.returncode})
            if r.returncode:print('FAILED',target,step,r.stderr[-2200:],flush=True)
            assert r.returncode==0,(target,step)
        print('BUILT',target,flush=True)
(O/'results.json').write_text(json.dumps(records,indent=2)+'\n')
