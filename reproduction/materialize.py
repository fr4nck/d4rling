#!/usr/bin/env python3
"""Materialize the historical source snapshot in a NEW directory."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
BASE="b7d0cb6a79fe196657deb9711647f8486bcc5e5e"
HERE=Path(__file__).resolve().parent
def run(args,**kwargs):return subprocess.run([str(x) for x in args],check=True,**kwargs)
def git(repo,*args):return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--output",type=Path,required=True)
 p.add_argument("--from-local",type=Path,help="copy an existing complete work tree offline, including its partial Git store")
 p.add_argument("--with-rpc-fix",action="store_true")
 a=p.parse_args();out=a.output.absolute()
 if out.exists() or out.is_symlink():raise SystemExit("REFUSE_EXISTING_DESTINATION")
 if not out.parent.is_dir():raise SystemExit("PARENT_DIRECTORY_MISSING")
 source=str(a.from_local.resolve()) if a.from_local else "https://github.com/fr4nck/d4rling.git"
 if a.from_local and (out==a.from_local.resolve() or a.from_local.resolve() in out.parents):
  raise SystemExit("DESTINATION_MUST_BE_OUTSIDE_SOURCE")
 lock=json.loads((HERE/"submodules.lock.json").read_text())
 if a.from_local:
  if git(a.from_local,"rev-parse","HEAD")!=BASE:raise SystemExit("LOCAL_SOURCE_BASE_MISMATCH")
  # A promisor clone can have a complete work tree but lack old Git objects.
  # Copying the work tree avoids a network fetch and preserves ignored inputs.
  shutil.copytree(a.from_local,out,symlinks=True)
 else:
  run(["git","clone","--no-checkout",source,out],env={**os.environ,"GIT_LFS_SKIP_SMUDGE":"1"})
  run(["git","-C",out,"checkout","--detach",BASE])
  run(["git","-C",out,"submodule","update","--init","--recursive"])
 for m in lock["submodules"]:
  if git(out/m["path"],"rev-parse","HEAD")!=m["commit"]:raise SystemExit("SUBMODULE_IDENTITY_MISMATCH:"+m["path"])
 patch=HERE/"patches/carbon-local.patch"
 already=subprocess.run(["git","-C",str(out),"apply","--reverse","--check",str(patch)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
 if not already:
  run(["git","-C",out,"apply","--check",patch])
  run(["git","-C",out,"apply",patch])
 target=out/"tests/regressions/carbon-events/parameters.c"
 data=(HERE/"snapshots/parameters.c").read_bytes()
 if target.exists() and target.read_bytes()!=data:raise SystemExit("PARAMETERS_SNAPSHOT_MISMATCH")
 if not target.exists():target.write_bytes(data)
 if a.with_rpc_fix:(out/"src/startup/mldr/mldr.c").write_bytes((HERE/"snapshots/mldr-pr6.c").read_bytes())
 state={"base":BASE,"historical_local_overlay":True,"ignored_parameters_restored":True,"submodules_verified":len(lock["submodules"]),"rpc_fix":a.with_rpc_fix,"source":str(out)}
 (out/"D4RLING-REPRODUCTION.json").write_text(json.dumps(state,indent=2)+"\n")
 print(json.dumps(state,indent=2))
if __name__=="__main__":main()
