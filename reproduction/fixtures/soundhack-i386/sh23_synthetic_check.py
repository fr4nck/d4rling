from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib,json,os,plistlib,stat,subprocess,sys

source=Path(__file__).with_name('sh23_llvm.py').read_text()
with TemporaryDirectory() as d:
 root=Path(d);val=root/'validation';val.mkdir()
 sh20=val/'soundhack-sh20.3OvPqBmm'/'replay';(sh20/'SoundHack.app'/'Contents'/'MacOS').mkdir(parents=True)
 tools=sh20.parent/'tools';tools.mkdir()
 app=sh20/'SoundHack.app'/'Contents'/'MacOS'/'SoundHack';app.write_bytes(b'NOT_REAL_SOUNDHACK')
 pin=hashlib.sha256(app.read_bytes()).hexdigest()
 origin=source.split("PIN='",1)[1].split("'",1)[0]
 source=source.replace(origin,pin)
 libs=[f'/usr/lib/libtest{i}.dylib' for i in range(7)];libs[0]='/System/Library/Frameworks/Carbon.framework/Versions/A/Carbon'
 direct=[f'_d{i:03d}' for i in range(57)];reexport=[f'_r{i:03d}' for i in range(125)];review=[f'_review{i:03d}' for i in range(211)]
 imports=[{'name':s,'library_name':libs[0]} for s in direct+reexport+review]
 record=[{'name':s,'library':libs[0],'weak':False,'SH22_class':t} for s,t in [(s,'DIRECT_NLIST_NAME') for s in direct]+[(s,'REEXPORT_GRAPH_NLIST_NAME') for s in reexport]+[(s,'NO_NAME_IN_BOUNDED_REEXPORT_GRAPH') for s in review]]
 parser=tools/'macho_audit.py'
 parser.write_text('''from pathlib import Path\nLIBS=%r\nIMPORTS=%r\nDIRECT=%r\nREEXPORT=%r\ndef inspect(path,arch):\n    path=Path(path);name=str(path);consumer=path.name=='SoundHack'\n    if consumer:return dict(sha256=%r,imports_nlist=[x['name'] for x in IMPORTS],imports_detail=IMPORTS,dylibs=[dict(name=x,kind='load') for x in LIBS])\n    i=next(i for i,x in enumerate(LIBS) if name.endswith(x))\n    return dict(filetype=6,install_name=LIBS[i],exports_nlist=(DIRECT if i==0 else REEXPORT if i==1 else []),dylibs=([dict(name=LIBS[1],kind='reexport')] if i==0 else []),sha256='f'*64)\n'''%(libs,imports,direct,reexport,pin))
 parser_bytes=parser.read_bytes();blob=hashlib.sha1(b'blob '+str(len(parser_bytes)).encode()+b'\0'+parser_bytes).hexdigest()
 old=source.split("BLOB='",1)[1].split("'",1)[0];source=source.replace(old,blob)
 (sh20/'SH20-summary.json').write_text(json.dumps(dict(status='SH20_OFFICIAL_APP_REPLAY_STATIC_PASS',verified_sha256=pin,nlist_import_count=393,dyld_dependency_count=7)))
 (sh20/'SoundHack.app'/'Contents'/'Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'SoundHack'}))
 sysroot=val/'sysroot';sysroot.mkdir()
 for lib in libs:
  f=sysroot/lib.lstrip('/');f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b'FAKE_MACHO')
 report22=val/'soundhack-sh22.PUTgbmR0'/'SH22-result.json';report22.parent.mkdir()
 report22.write_text(json.dumps({'status':'SH22_STATIC_LOT_COMPLETE','steps':[{'status':'PASS'} for i in range(9)],'imports':{'total':393,'direct':57,'reexport':125,'review':211},'import_393_closure':{'records':record}}))
 dump=root/'llvm-objdump-19';dump.write_text('#!/bin/sh\ncase "$1" in --help) echo "--exports-trie";; *) echo "Exports trie:"; echo "0x02 _review000";; esac\n');dump.chmod(0o700)
 nm=root/'llvm-nm-19';nm.write_text('#!/bin/sh\ncase "$1" in --help) echo "--arch";; *) echo "(indirect) _review001 (for _alias)";; esac\n');nm.chmod(0o700)
 stage=root/'stage';stage.mkdir()
 p=stage/'sh23_llvm.py';p.write_text(source)
 r=subprocess.run([sys.executable,'-B',str(p),str(val),str(sh20),str(sysroot),str(stage),str(dump),str(nm)],capture_output=True,text=True)
 print(r.stdout)
 if r.stderr:print('STDERR:',r.stderr)
 print('RC',r.returncode)
 report=json.load(open(stage/'SH23-result.json'))
 print('STATES',[(g['name'],g['state']) for g in report['steps']])
 print('CLASSES',report.get('recheck_211_imports',{}).get('classification'))
 assert r.returncode==0, r.stdout
 assert report['status']=='SH23_COMPOSITE_STATIC_PASS'
 print('SYNTHETIC_INTEGRATION=PASS')
