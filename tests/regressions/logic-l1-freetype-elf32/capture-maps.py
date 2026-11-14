import pathlib,sys,time,json,os
out=pathlib.Path(sys.argv[1]); parent=int(sys.argv[2]); records=set()
for i in range(200):
 for p in pathlib.Path('/proc').glob('[0-9]*/maps'):
  try:
   for line in p.read_text().splitlines():
    fields=line.split(None,5)
    if len(fields)==6 and fields[5].startswith('/') and ('.so' in fields[5] or fields[5].endswith('/mldr32')): records.add((p.parent.name,fields[5]))
  except (OSError,PermissionError): pass
 if not pathlib.Path('/proc',str(parent)).exists(): break
 time.sleep(.02)
out.write_text(json.dumps(sorted(records),indent=2)+'\n')
