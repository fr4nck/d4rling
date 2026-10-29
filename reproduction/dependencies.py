#!/usr/bin/env python3
"""Inspect or install the documented Debian 13 build prerequisites."""
import argparse,json,platform,subprocess,sys
from pathlib import Path
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--mode",choices=["check","print","simulate","install"],default="check")
 p.add_argument("--exact",action="store_true",help="require every recorded package version")
 a=p.parse_args(); lock=json.loads(Path(__file__).with_name("dependencies.lock.json").read_text())
 packages=lock["packages"]; args=[]
 for x in packages:
  version=x["version_observed"]
  if a.exact and version=="NOT_INSTALLED":
   raise SystemExit("Exact profile incomplete for "+x["package"]+"; consult the documented gap.")
  args.append(x["package"]+("="+version if a.exact else ""))
 if a.mode=="print": print(" ".join(args));return 0
 release={}
 for line in Path("/etc/os-release").read_text().splitlines():
  if "=" in line:
   k,v=line.split("=",1);release[k]=v.strip('"')
 if release.get("ID")!="debian" or release.get("VERSION_ID")!="13" or platform.machine()!="x86_64":
  raise SystemExit("Use Debian 13 amd64; other platforms are not the recorded reference.")
 if a.mode=="check":
  mismatches=[];missing=[]
  for x in packages:
   r=subprocess.run(["dpkg-query","-W","-f=${Version}",x["package"]],capture_output=True,text=True)
   version=r.stdout.strip() if r.returncode==0 else None
   if version is None:missing.append(x["package"])
   elif x["version_observed"]!="NOT_INSTALLED" and version!=x["version_observed"]:mismatches.append(x["package"])
  print(json.dumps({"missing":missing,"version_drift":mismatches,"qualified_reference":not missing and not mismatches},indent=2))
  return 1 if missing or (a.exact and mismatches) else 0
 command=["apt-get","install","--no-install-recommends",*args]
 if a.mode=="simulate":return subprocess.call(["apt-get","-s",*command[1:]])
 # This explicit mode changes only the machine on which the user runs it.
 subprocess.run(["sudo","apt-get","update"],check=True)
 return subprocess.call(["sudo",*command])
if __name__=="__main__":sys.exit(main())
