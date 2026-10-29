#!/usr/bin/env python3
"""Rebuild the QT-1980 @loader_path Carbon i386 witness; do not execute it."""
import argparse,json,subprocess,os
from pathlib import Path
HERE=Path(__file__).resolve().parent
def run(args,log):
 r=subprocess.run([str(x) for x in args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 log.write_bytes(r.stdout)
 if r.returncode:raise SystemExit("FAILED: "+str(log))
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ["source","build","installation","output"]:p.add_argument("--"+name,type=Path,required=True)
 a=p.parse_args()
 src=a.source.resolve();build=a.build.resolve();install=a.installation.resolve();out=a.output.absolute()
 if out.exists() or out.is_symlink():raise SystemExit("REFUSE_EXISTING_OUTPUT")
 root=install/"libexec/darling";cf=root/"System/Library/Frameworks/CoreFoundation.framework/CoreFoundation";libsys=root/"usr/lib/libSystem.B.dylib"
 linker=build/"src/external/cctools-port/cctools/ld64/src/x86_64-apple-darwin20-ld"
 for path in [cf,libsys,linker,src/"src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c"]:
  if not path.is_file():raise SystemExit("MISSING_INPUT: "+str(path))
 for image in [cf,libsys]:
  arch=subprocess.check_output(["llvm-lipo-19","-archs",str(image)],text=True)
  if "i386" not in arch.split():raise SystemExit("I386_SLICE_MISSING: "+str(image))
 out.mkdir(mode=0o700)
 sdk=src/"Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
 includes=[src/"src/frameworks/Carbon/HIToolbox/include",src/"src/frameworks/Carbon/include",src/"src/frameworks/CoreServices/include",src/"src/frameworks/CoreFoundation/include",src/"src/external/corefoundation/include",build/"src/external/corefoundation"]
 flags=["-isysroot",sdk] if (sdk/"usr/include/stdio.h").is_file() else []
 for d in includes:
  if d.is_dir():flags+=["-I",d]
 for d in [sdk/"System/Library/Frameworks",root/"System/Library/Frameworks"]:
  if d.is_dir():flags+=["-F",d]
 cc=["clang-19","-target","i386-apple-darwin","-std=gnu11","-O2","-fPIC","-fno-stack-protector","-fno-builtin"]
 obj=out/"CarbonEventsCore.o";probe=out/"carbon-event.o";dylib=out/"libD4CarbonEvents.dylib";exe=out/"carbon-dynamic-i386"
 run([*cc,*flags,"-Werror=implicit-function-declaration","-include",HERE/"fixtures/atomic-bridge.h","-c",src/"src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c","-o",obj],out/"carbon-compile.log")
 run([*cc,"-c",HERE/"fixtures/carbon-event.c","-o",probe],out/"probe-compile.log")
 common=[linker,"-arch","i386","-macosx_version_min","10.9","-syslibroot",root,"-L",root/"usr/lib","-F",root/"System/Library/Frameworks"]
 run([*common,"-dylib","-install_name","@loader_path/libD4CarbonEvents.dylib","-compatibility_version","1.0.0","-current_version","1.0.0","-o",dylib,obj,cf,libsys],out/"dylib-link.log")
 run([*common,"-pie","-e","_main","-o",exe,probe,dylib,libsys],out/"probe-link.log")
 exe.chmod(0o700);dylib.chmod(0o700)
 (out/"result.json").write_text(json.dumps({"built":True,"runtime_executed":False,"expected_marker":"D4RLING-CARBON-EVENT-I386-OK","expected_exit":0},indent=2)+"\n")
 print("CARBON_I386_PROBE_BUILD=PASS\nRUNTIME_EXECUTED=NO")
if __name__=="__main__":main()
