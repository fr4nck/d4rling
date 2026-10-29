#!/usr/bin/env python3
"""Restore a private project snapshot below a NEW directory; never install it."""
import argparse,hashlib,json,os,shutil,tarfile
from pathlib import Path,PurePosixPath
def safe(root,name):
 p=PurePosixPath(name)
 if p.is_absolute() or ".." in p.parts or not p.parts:raise ValueError("unsafe archive path")
 target=root.joinpath(*p.parts)
 if root not in target.parents and target!=root:raise ValueError("archive path escapes output")
 return target
def link_target(root,target):
 # Rebase known archived locations. Keep guest-absolute paths as guest paths.
 for prefix,new in [("/usr/local/libexec/darling",root/"system/usr/local/libexec/darling"),("/opt/d4rling-qt-i386",root/"system/opt/d4rling-qt-i386")]:
  if target==prefix or target.startswith(prefix+"/"):return str(new)+target[len(prefix):]
 p=PurePosixPath(target)
 if p.is_absolute() and len(p.parts)>=4 and p.parts[1]=="home":
  return str(root/"home"/Path(*p.parts[3:]))
 return target
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("archive",type=Path);p.add_argument("--output",type=Path,required=True)
 p.add_argument("--expected-sha256");p.add_argument("--supplement",type=Path)
 a=p.parse_args();out=a.output.absolute()
 if out.exists() or out.is_symlink():raise SystemExit("REFUSE_EXISTING_OUTPUT")
 if a.expected_sha256:
  h=hashlib.sha256()
  with a.archive.open("rb") as f:
   for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
  if h.hexdigest()!=a.expected_sha256:raise SystemExit("ARCHIVE_DIGEST_MISMATCH")
 # Validate member names before creating the destination.
 archives=[a.archive]+([a.supplement] if a.supplement else [])
 for archive in archives:
  with tarfile.open(archive,"r:gz") as tar:
   for member in tar:
    safe(out,member.name)
    if member.islnk():safe(out,member.linkname)
    if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
     raise SystemExit("UNSUPPORTED_SPECIAL_MEMBER")
 out.mkdir(mode=0o700,parents=True)
 symlinks=[];hardlinks=[];count=0
 for archive in archives:
  with tarfile.open(archive,"r|gz") as tar:
   for member in tar:
    dst=safe(out,member.name)
    if member.isdir():dst.mkdir(mode=0o700,parents=True,exist_ok=True)
    elif member.issym():symlinks.append((dst,member.linkname))
    elif member.islnk():hardlinks.append((dst,safe(out,member.linkname)))
    elif member.isfile():
     dst.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
     with dst.open("xb") as stream:shutil.copyfileobj(tar.extractfile(member),stream)
     dst.chmod(member.mode&0o777)
    count+=1
 # No symlink is present while writing archive file data.
 for dst,target in hardlinks:
  dst.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
  if not target.is_file() or target.is_symlink():raise SystemExit("INVALID_HARDLINK")
  os.link(target,dst)
 for dst,target in symlinks:
  dst.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
  if dst.exists() or dst.is_symlink():raise SystemExit("DUPLICATE_SYMLINK_PATH")
  os.symlink(link_target(out,target),dst)
 print(json.dumps({"restored_entries":count,"output":str(out),"system_installation_performed":False,"runtime_started":False},indent=2))
if __name__=="__main__":main()
