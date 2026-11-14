# SPDX-License-Identifier: GPL-3.0-or-later
"""Metadata-only reuse of the privately owned Logic audit. Never executes Apple code."""
from pathlib import Path
import collections,csv,hashlib,importlib.util,json,posixpath,re,sys,argparse
sys.dont_write_bytecode=True
parser=argparse.ArgumentParser();parser.add_argument('--stage',required=True,type=Path);parser.add_argument('--audit',required=True,type=Path);args=parser.parse_args();H=args.stage.resolve()
A=args.audit.resolve()
known=json.loads((H/'l1-frozen-inputs.json').read_text())
for name in ['macho_reader.py','binary-analysis.json','binary-audit-validation.json']:
 path=A/name
 assert hashlib.sha256(path.read_bytes()).hexdigest()==known[str(path)], str(path)
ROOT=H/'logic-runtime/libexec/darling';B=H.parent/'upstream-sync-20261114/build-gui-i386'
MAIN='/Applications/Logic Pro.app/Contents/MacOS/Logic Pro'
spec=importlib.util.spec_from_file_location('owned_metadata_reader',A/'macho_reader.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
report=json.loads((A/'binary-analysis.json').read_text());cache={};owned={};input_hashes={}
def thin(meta):return next((x for x in meta['slices'] if x['architecture']=='i386'),None)
def load(path):
 path=Path(path)
 if str(path) not in cache:
  try:cache[str(path)]=reader.parse(path.read_bytes())
  except (OSError,ValueError,IndexError):cache[str(path)]=None
 return cache[str(path)]
for record in report['binaries']:
 raw=record['local_path'].replace('\\\\','/').replace('\\','/');path=Path('/mnt/c'+raw[2:]);meta=load(path)
 if not meta:continue
 assert meta['sha256']==record['sha256'],record['guest_path'];input_hashes[str(path)]=meta['sha256']
 owned[record['guest_path']]={'path':str(path),'meta':meta,'slice':thin(meta),'package':record['package']}
main=owned[MAIN]['slice'];built={}
lines=(B/'build.ninja').read_text().splitlines()
for i,line in enumerate(lines):
 if not line.startswith('build ') or 'SHARED_LIBRARY_LINKER' not in line:continue
 p=B/line[6:].split(': ',1)[0]
 if 'firstpass' in str(p).lower():continue
 flags=next((x for x in lines[i+1:i+12] if x.startswith('  LINK_FLAGS = ')),'');match=re.search(r'-Wl,-dylib_install_name,([^ ]+)',flags)
 if not match:continue
 for path in (p,p.with_name(p.name.replace('_i386','').replace('_x86_64',''))):
  meta=load(path)
  if meta and thin(meta):built.setdefault(match[1],{})[str(path)]=meta

def resolve(name,owner):
 for token,base in [('@executable_path',posixpath.dirname(MAIN)),('@loader_path',posixpath.dirname(owner))]:
  if name.startswith(token+'/'):return posixpath.normpath(base+name[len(token):])
 return posixpath.normpath(name)

def provider(guest,mode):
 actual=ROOT/guest.lstrip('/');meta=load(actual)
 if meta and thin(meta):return {'state':'runtime-i386','path':str(actual),'meta':meta,'slice':thin(meta)}
 if guest in owned and owned[guest]['slice']:return dict(owned[guest],state='owned-original-static-only')
 if mode=='available' and built.get(guest):
  path,meta=sorted(built[guest].items(),key=lambda item:(Path(item[0]).name!=posixpath.basename(guest),len(item[0])))[0]
  return {'state':'built-i386-not-installed','path':path,'meta':meta,'slice':thin(meta)}
 return {'state':'runtime-other-architecture' if meta else 'missing','path':str(actual),'meta':meta,'slice':None}

def exports(guest,mode,seen=frozenset()):
 if guest in seen:return set(),set()
 p=provider(guest,mode);sl=p['slice']
 if not sl:return set(),{guest}
 names=set(sl['exports']);missing=set()
 for dep in sl['dependencies']:
  stem=posixpath.basename(dep['path']).split('.')[0]
  if dep['kind']=='reexport' or stem in sl['sub_umbrellas'] or stem in sl['sub_libraries']:
   ns,ms=exports(resolve(dep['path'],guest),mode,seen|{guest});names|=ns;missing|=ms
 return names,missing

matrix=[];symbol_rows=[]
for dep in main['dependencies']:
 guest=resolve(dep['path'],MAIN);refs=[x for x in main['imports'] if x['provider']==dep['path']];required=[x for x in refs if not x['weak'] and dep['kind']!='weak'];row={'ordinal':dep['ordinal'],'dependency':dep['path'],'load_kind':dep['kind'],'imports':len(refs),'required_imports':len(required)}
 for mode in ['runtime','available']:
  p=provider(guest,mode);names,missing=exports(guest,mode);notfound=[x['name'] for x in required if x['name'] not in names]
  row[mode+'_state']=p['state'];row[mode+'_names_found']=len(required)-len(notfound);row[mode+'_names_not_found']=len(notfound);row[mode+'_unresolved_reexports']=sorted(missing-{guest});row[mode+'_first_name_not_found']=notfound[0] if notfound else None
  if mode=='available':
   row['provider_sha256']=p['meta']['sha256'] if p['slice'] else None;row['provider_path_private']=p['path'] if p['slice'] else None
   for item in refs:symbol_rows.append({'dependency':dep['path'],'name':item['name'],'weak':item['weak'] or dep['kind']=='weak','state':'name-found-unqualified' if item['name'] in names else 'name-not-found' if p['slice'] else 'provider-missing'})
 row['load_test']='NOT_RUN';row['implementation']='NOT_GLOBALLY_QUALIFIED'
 matrix.append(row)
# Trace the declared strong graph from the already audited metadata; order is retained.
# This is a declared-image graph, never a claim that Logic itself reached a particular image.
queue=[MAIN];seen=set();graph=[]
while queue:
 guest=queue.pop(0)
 if guest in seen:continue
 seen.add(guest);p=provider(guest,'available');sl=p['slice']
 if not sl:continue
 for dep in sl['dependencies']:
  child=resolve(dep['path'],guest);q=provider(child,'available');graph.append({'parent':guest,'ordinal':dep['ordinal'],'path':dep['path'],'resolved':child,'kind':dep['kind'],'state':q['state']})
  if q['slice'] and dep['kind']!='weak':queue.append(child)
classes=sorted({i['name'].removeprefix('.objc_class_name_') for i in main['imports'] if i['name'].startswith('.objc_class_name_')})
dynamic=[i['name'] for i in main['imports'] if any(s in i['name'] for s in ['dlopen','NSAddImage','CFBundleGetBundleWithIdentifier','CFBundleLoadExecutable','CFBundleGetFunctionPointerForName'])]
summary={'source':'existing private audit 2026-11-04; 73 copied input hashes rechecked','main_sha256':owned[MAIN]['meta']['sha256'],'main_bytes':owned[MAIN]['meta']['bytes'],'architectures':[x['architecture'] for x in owned[MAIN]['meta']['slices']],'direct_dependencies':len(matrix),'strong_dependencies':sum(r['load_kind']!='weak' for r in matrix),'weak_dependencies':sum(r['load_kind']=='weak' for r in matrix),'main_i386_imports':len(main['imports']),'direct_required_imports':sum(r['required_imports'] for r in matrix),'declared_graph_images':len(seen),'declared_graph_edges':len(graph),'class_imports':len(classes),'cocoa_NS_class_imports':sum(c.startswith('NS') for c in classes),'dynamic_loader_imports':dynamic,'states_runtime':dict(collections.Counter(r['runtime_state'] for r in matrix)),'states_available':dict(collections.Counter(r['available_state'] for r in matrix)),'first_system_image_not_installed':next(r['dependency'] for r in matrix if r['load_kind']!='weak' and r['dependency'].startswith('/System') and r['runtime_state']!='runtime-i386'),'logic_execution':'NOT_RUN_L2_NOT_AUTHORIZED'}
for name,value in [('logic-direct-matrix.json',matrix),('logic-symbol-matrix.json',symbol_rows),('logic-declared-graph.json',graph),('logic-class-imports.json',classes),('logic-input-sha256.json',input_hashes)]:
 (H/'private'/name).write_text(json.dumps(value,indent=2)+'\n')
(H/'reports/logic-l1-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(H/'private/built-provider-index.json').write_text(json.dumps({key:list(value) for key,value in built.items()},indent=2)+'\n')
print(json.dumps(summary,indent=2))
for row in matrix:
 print(row['ordinal'],row['available_state'],str(row['available_names_found'])+'/'+str(row['required_imports']),row['available_first_name_not_found'],row['dependency'])
print('CARBON_DEPENDENCY_GAPS',[r for r in graph if '/Carbon.framework/Versions/A/Carbon'==r['parent'].removeprefix('/System/Library/Frameworks') and r['state']=='missing'])

# Generate only a private list of public symbol names for the eight S4 providers.
# This header is not published and contains no Apple implementation code.
selected={row['dependency'] for row in matrix if load(H/'runtime/libexec/darling'/resolve(row['dependency'],MAIN).lstrip('/')) and thin(load(H/'runtime/libexec/darling'/resolve(row['dependency'],MAIN).lstrip('/')))}
requests=[row for row in symbol_rows if row['dependency'] in selected and not row['weak']]
header='static const struct symbol_request requests[] = {\n'+''.join('    {'+json.dumps(row['dependency'])+','+json.dumps(row['name'][1:] if row['name'].startswith('_') else row['name'])+'},\n' for row in requests)+'};\n'
(H/'logic-system-imports.h').write_text(header)
