#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
import pathlib,json,sys,time,hashlib
out=pathlib.Path(sys.argv[1]);parent=int(sys.argv[2]);records=set();personalities=set();images=set()
for i in range(400):
 for p in pathlib.Path('/proc').glob('[0-9]*/maps'):
  try:
   exe=str((p.parent/'exe').readlink())
   if not pathlib.Path(exe).name.startswith('mldr'):continue
   with (p.parent/'exe').open('rb') as f:
    ident=f.read(5);f.seek(0);digest=hashlib.file_digest(f,'sha256').hexdigest()
   images.add((p.parent.name,exe,digest,ident[4]*32))
   try:personalities.add((p.parent.name,exe,(p.parent/'personality').read_text().strip()))
   except OSError:pass
   for line in p.read_text().splitlines():
    x=line.split(None,5)
    if len(x)==6 and x[5].startswith('/'):records.add((p.parent.name,x[5]))
  except OSError:pass
 if not pathlib.Path('/proc',str(parent)).exists():break
 time.sleep(.01)
out.write_text(json.dumps({'mappings':sorted(records),'personalities':sorted(personalities),'images':sorted(images)},indent=2)+'\n')
