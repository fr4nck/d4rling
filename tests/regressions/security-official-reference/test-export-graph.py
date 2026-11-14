# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import json,os,re,subprocess,argparse,time
parser=argparse.ArgumentParser();parser.add_argument('--stage',required=True,type=Path);args=parser.parse_args();H=args.stage.resolve();S=H/'src/src/external/security';O=H/('exp-replay-'+str(time.time_ns()));O.mkdir();(O/'logs').mkdir();(O/'tmp').mkdir()
(O/'tools').mkdir(exist_ok=True)
clang=O/'tools/clang'
if not clang.exists():clang.symlink_to('/usr/bin/clang-19')
a=json.loads((H/'commands/official-exp-i386-0.json').read_text());start=a.index('objective-c')+1;last=max(i for i,x in enumerate(a) if x=='-target');flags=a[start:last]
env=dict(os.environ,TMPDIR=str(O/'tmp'));records=[]
for variant,source in [('official',(S/'OSX/CMakeLists.txt').read_text()),('before-exp-fix',subprocess.check_output(['git','-C',str(S),'show','a536cfff5b857b214d939415cf6040e347fcf785:OSX/CMakeLists.txt'],text=True))]:
 src=O/('export-graph-'+variant);nested=src/'src/external/security/OSX';nested.mkdir(parents=True,exist_ok=False)
 (src/'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.13)\nproject(export_graph C)\nadd_subdirectory(src/external/security/OSX)\n')
 (src/'dummy.c').write_text('int dummy;\n')
 commands=re.findall(r'add_custom_command\(\n\t\tOUTPUT.*?\n\t\)',source,re.S);assert len(commands)==2
 prereq=re.search(r'set\(SECURITY_EXP_IN_DEPENDS.*?\n\)',source,re.S)
 props=re.findall(r'set_property\(TARGET Security_.*?LINK_DEPENDS.*?\n\t\)',source,re.S)
 options=re.findall(r'target_link_options\(Security_.*?\n\t\)',source,re.S)
 text='set(APPLE_ARCH_32BIT i386)\nset(APPLE_ARCH_64BIT x86_64)\nset(APPLE_TARGET_TRIPLET_32BIT i386-apple-darwin20)\nset(APPLE_TARGET_TRIPLET_64BIT x86_64-apple-darwin20)\n'
 text+='set(EXP_IN_FLAGS '+ ' '.join('[['+x+']]' for x in flags)+')\n'
 if prereq:text+=prereq.group()+'\n'
 text+='\n'.join(commands)+'\nadd_custom_target(generate-security-exp DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/Security.i386.exp ${CMAKE_CURRENT_BINARY_DIR}/Security.x86_64.exp)\n'
 text+='add_library(Foundation SHARED IMPORTED)\nset_target_properties(Foundation PROPERTIES IMPORTED_LOCATION "'+str(H.parent/'upstream-sync-20261114/build-gui-i386/src/external/foundation/Foundation')+'")\n'
 for arch in ['i386','x86_64']:
  for suffix in ['','_firstpass']:
   text+='add_library(Security_'+arch+suffix+' SHARED EXCLUDE_FROM_ALL "'+str(src/'dummy.c')+'")\n'
 text+='\n'.join(props+options)+'\n';text=text.replace('${CMAKE_CURRENT_SOURCE_DIR}',str(S/'OSX'))
 (nested/'CMakeLists.txt').write_text(text)
 build=O/('export-make-'+variant)
 for label,cmd in [('configure',['cmake','-S',str(src),'-B',str(build),'-G','Unix Makefiles','-DCMAKE_C_COMPILER='+str(clang)]),('generate',['cmake','--build',str(build),'--target','generate-security-exp'])]:
  r=subprocess.run(cmd,env=env,capture_output=True,text=True);(O/'logs'/('export-'+variant+'-'+label+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,(label,r.stderr[-3000:])
 r=subprocess.run(['bash',str(S/'tests/exp-depends.sh'),str(build)],env=env,capture_output=True,text=True);(O/'logs'/('upstream-exp-depends-'+variant+'.log')).write_text(r.stdout+r.stderr)
 print('UPSTREAM_EXPORT_TEST',variant,'rc',r.returncode,r.stdout[-3000:],flush=True)
 assert (r.returncode==0)==(variant=='official')
 edges=[]
 for arch in ['i386','x86_64']:
  for suffix in ['','_firstpass']:
   target='Security_'+arch+suffix;makefile=build/'src/external/security/OSX/CMakeFiles'/(target+'.dir/build.make');txt=makefile.read_text();linked=any(l.startswith('src/external/security/OSX/lib'+target+'.so:') and ('Security.'+arch+'.exp') in l for l in txt.splitlines())
   assert linked==(variant=='official'),(variant,target,linked);edges.append({'target':target,'export_dependency':linked})
 records.append({'variant':variant,'upstream_test_rc':r.returncode,'link_edges':edges})
(O/'export-graph-results.json').write_text(json.dumps(records,indent=2)+'\n');print('OFFICIAL_EXPORT_GRAPH_PASS')
