#!/usr/bin/env python3
"""Verify a private recovery tar.gz against its JSONL file manifest."""
import argparse,hashlib,json,tarfile
from pathlib import Path
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("archive",type=Path);p.add_argument("manifest",type=Path);a=p.parse_args()
 expected={v["path"]:v for line in a.manifest.read_text().splitlines() if line for v in [json.loads(line)]}
 seen=set();fail=[]
 with tarfile.open(a.archive,"r|gz") as tar:
  for member in tar:
   name=member.name;seen.add(name);e=expected.get(name)
   if e is None:fail.append({"path":name,"error":"not_in_manifest"});continue
   if member.isfile():
    h=hashlib.sha256();f=tar.extractfile(member)
    for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    if h.hexdigest()!=e.get("sha256"):fail.append({"path":name,"error":"content_mismatch"})
   elif member.issym() or member.islnk():
    if member.linkname!=e["link"]:fail.append({"path":name,"error":"link_mismatch"})
 missing=sorted(set(expected)-seen)
 result={"entries":len(seen),"missing":missing,"failures":fail,"verified":not missing and not fail}
 print(json.dumps(result,indent=2))
 if not result["verified"]:raise SystemExit(1)
if __name__=="__main__":main()
