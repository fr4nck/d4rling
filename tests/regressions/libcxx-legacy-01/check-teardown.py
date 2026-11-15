#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
import pathlib,json,sys,time
out=pathlib.Path(sys.argv[1]);ns=(out/'pid-namespace').read_text().strip();left=[]
for i in range(151):
 left=[]
 for p in pathlib.Path('/proc').glob('[0-9]*/ns/pid'):
  try:
   if str(p.readlink())==ns:left.append(p.parent.parent.name)
  except OSError:pass
 if not left:break
 time.sleep(.02)
(out/'teardown.json').write_text(json.dumps({'namespace':ns,'remaining':left,'polls':i+1},indent=2)+'\n')
assert not left,left
