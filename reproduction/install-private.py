#!/usr/bin/env python3
"""Build and stage an explicitly configured private installation; never use sudo."""
import argparse,subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--build-dir",type=Path,required=True)
 p.add_argument("--build",action="store_true");p.add_argument("--jobs",type=int,default=2)
 a=p.parse_args();build=a.build_dir.resolve()
 cache={}
 for line in (build/"CMakeCache.txt").read_text().splitlines():
  if line and not line.startswith(("#","//")) and "=" in line:
   k,v=line.split("=",1);cache[k.split(":")[0]]=v
 prefix=Path(cache.get("CMAKE_INSTALL_PREFIX","/")).resolve()
 if cache.get("DEBIAN_PACKAGING")!="ON":raise SystemExit("SHUTDOWN_HOOK_NOT_DISABLED")
 if prefix!=build/"private-install":raise SystemExit("UNEXPECTED_INSTALL_PREFIX")
 if prefix.exists() or prefix.is_symlink():raise SystemExit("REFUSE_EXISTING_INSTALLATION")
 if not 1<=a.jobs<=64:raise SystemExit("INVALID_JOB_COUNT")
 for script in build.rglob("cmake_install.cmake"):
  if "shutdown-user.sh" in script.read_text():raise SystemExit("UNSAFE_INSTALL_HOOK_PRESENT")
 if a.build:subprocess.run(["cmake","--build",str(build),"--parallel",str(a.jobs)],check=True)
 subprocess.run(["cmake","--install",str(build)],check=True)
 for relative in ["bin/darling","libexec/darling/usr/libexec/darling/mldr","libexec/darling/usr/lib/dyld","libexec/darling/usr/lib/libSystem.B.dylib"]:
  if not (prefix/relative).is_file():raise SystemExit("INCOMPLETE_INSTALLATION: "+relative)
 print("PRIVATE_INSTALLATION="+str(prefix))
 print("RUNTIME_EXECUTED=NO")
if __name__=="__main__":main()
