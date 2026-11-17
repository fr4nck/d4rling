from collections import Counter,defaultdict,deque
from pathlib import Path
import hashlib,importlib.util,json,os,plistlib,re,subprocess,sys,time

V,S,P,O,LLVM,NM=map(Path,sys.argv[1:])
APP=S/'SoundHack.app';BIN=APP/'Contents/MacOS/SoundHack';PARSER=S.parent/'tools/macho_audit.py'
SH22=V/'soundhack-sh22.PUTgbmR0/SH22-result.json'
PIN='6fb11c708079ca3b8f91dc53ab0d8ae732fbb8be32f0e22e34114764b9be089c'
BLOB='0ac6e95301ed563bfb12cadabb444fda520f3c09'
status=[];ctx={};out={'status':'PENDING','steps':status,'guest_run':False}

def hashfile(p,limit):
    if p.is_symlink() or not p.is_file() or p.stat().st_size>limit:raise ValueError('BAD_FILE')
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def gate(name,fn):
    print(f'STEP={len(status)+1}/12 {name} START',flush=True)
    begin=time.monotonic()
    try:
        result=fn();status.append({'name':name,'state':'PASS','elapsed':round(time.monotonic()-begin,2)})
        if result is not None:out[name.lower()]=result
        print('STEP='+name+' PASS',flush=True)
    except (Exception) as ex:
        status.append({'name':name,'state':'BLOCKED','reason':type(ex).__name__})
        print('STEP='+name+' BLOCKED='+type(ex).__name__,flush=True)

def original():
    assert hashfile(BIN,8<<20)==PIN
    raw=PARSER.read_bytes();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==BLOB
    sh20=json.loads((S/'SH20-summary.json').read_text())
    assert sh20['status']=='SH20_OFFICIAL_APP_REPLAY_STATIC_PASS' and sh20['verified_sha256']==PIN
    assert sh20['nlist_import_count']==393 and sh20['dyld_dependency_count']==7
    spec=importlib.util.spec_from_file_location('sh23_existing_macho',PARSER)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    c=m.inspect(BIN,'i386');assert c['sha256']==PIN and len(c['imports_nlist'])==393
    ctx.update(macho=m,consumer=c,original_sha=PIN,parser_sha=hashfile(PARSER,60000))
    return {'real_soundhack':'PASS','i386_nlist_imports':393}

def report22():
    r=json.loads(SH22.read_text())
    assert r['status']=='SH22_STATIC_LOT_COMPLETE' and len(r['steps'])==9
    assert all(x['status']=='PASS' for x in r['steps'])
    assert tuple(r['imports'][k] for k in ('total','direct','reexport','review'))==(393,57,125,211)
    rows=r['import_393_closure']['records'];assert len(rows)==393
    ctx.update(records=rows,sh22_sha=hashfile(SH22,2<<20))
    return {'SH22':'9/9_PASS','direct':57,'via_reexport':125,'remaining':211}

def reconcile():
    expected=Counter((d['name'],d['library_name']) for d in ctx['consumer']['imports_detail'])
    actual=Counter((d['name'],d['library']) for d in ctx['records'])
    assert expected==actual
    classes=Counter(r['SH22_class'] for r in ctx['records'])
    assert classes=={'DIRECT_NLIST_NAME':57,'REEXPORT_GRAPH_NLIST_NAME':125,'NO_NAME_IN_BOUNDED_REEXPORT_GRAPH':211}
    return {'matched':393,'classes':dict(classes)}

def expand():
    root=P.resolve(strict=True);m=ctx['macho'];libs={};pending=deque((d['name'],0) for d in ctx['consumer']['dylibs'])
    total=0;roots=[d['name'] for d in ctx['consumer']['dylibs']]
    assert len(roots)==7 and len(set(roots))==7
    while pending and len(libs)<96:
        name,depth=pending.popleft()
        if name in libs:continue
        item={'status':'UNAVAILABLE','exports':set(),'deps':[],'path':None}
        libs[name]=item
        if not name.startswith('/') or '..' in name.split('/'):
            item['status']='UNSAFE_INSTALL_NAME';continue
        path=(P/name.lstrip('/')).resolve(strict=False)
        if not path.is_relative_to(root):item['status']='SYMLINK_ESCAPE';continue
        if not path.is_file() or path.stat().st_size>128<<20:item['status']='MISSING_OR_OVERSIZE';continue
        total+=path.stat().st_size
        if total>640<<20:item['status']='READ_BUDGET';continue
        try:
            entry=m.inspect(path,'i386')
            if entry['filetype'] not in (6,9) or entry['install_name']!=name:raise ValueError('IDENTITY')
            item.update(status='I386_PARSED',exports=set(entry['exports_nlist']),
                        deps=[x['name'] for x in entry['dylibs'] if x['kind']=='reexport'],path=path,
                        sha256=entry['sha256'])
            if depth<7:
                for child in item['deps']:pending.append((child,depth+1))
            elif item['deps']:item['status']='DEPTH_LIMIT'
        except Exception as e:item['status']='UNPARSEABLE_'+type(e).__name__
        if len(libs)%10==0:print('PROVIDERS_SCANNED='+str(len(libs)),flush=True)
    ctx.update(libs=libs,roots=roots)
    return {'scanned':len(libs),'initial_parsed':sum(libs[n]['status']=='I386_PARSED' for n in roots),
            'all_parsed':sum(x['status']=='I386_PARSED' for x in libs.values()),'bound_reached':bool(pending)}

def selftest():
    # Match only complete symbol-token identifiers; never substring-match.
    pattern=re.compile(r'(?<![\w.$])(_[A-Za-z0-9_.$]+)(?![\w.$])')
    assert pattern.findall('0x15 _AEProcessAppleEvent [weak]')==['_AEProcessAppleEvent']
    assert '_ABC' not in pattern.findall('0x15 _ABCD')
    assert pattern.findall('[re-export] _foo (from Carbon)')==['_foo']
    assert re.findall(r'\(indirect\)\s+(_[A-Za-z0-9_.$]+)\s+\(for', '(indirect) _Alias (for _Target)')==['_Alias']
    ctx['pattern']=pattern
    return {'token_negative_controls':3}

def tool():
    if not LLVM.is_file() or not os.access(LLVM,os.X_OK):raise ValueError('LLVM_OBJDUMP_MISSING')
    if not NM.is_file() or not os.access(NM,os.X_OK):raise ValueError('LLVM_NM_MISSING')
    r=subprocess.run([str(LLVM),'--help'],capture_output=True,timeout=8)
    n=subprocess.run([str(NM),'--help'],capture_output=True,timeout=8)
    assert r.returncode==0 and b'--exports-trie' in r.stdout
    assert n.returncode==0 and b'--arch' in n.stdout
    return {'llvm_exports_trie':'AVAILABLE','llvm_nm_indirect':'AVAILABLE'}

def trie():
    libs=ctx['libs'];records={};valid=0;partial=0;total=0
    for i,(name,info) in enumerate(libs.items(),1):
        if info['status']!='I386_PARSED':records[name]={'status':'NO_PROVIDER','names':set()};partial+=1;continue
        try:
            command=[str(LLVM),'--macho','--arch=i386','--exports-trie',str(info['path'])]
            r=subprocess.run(command,capture_output=True,timeout=12)
            if r.returncode!=0 or len(r.stdout)>8<<20:raise ValueError('OBJDUMP_FAIL_OR_TOO_BIG')
            text=r.stdout.decode('utf8','replace')
            if 'Exports trie:' not in text:raise ValueError('NO_TRIE_SECTION_MARKER')
            data=text.split('Exports trie:',1)[1]
            names=set(ctx['pattern'].findall(data))
            records[name]={'status':'TRIE_OUTPUT_PARSED','names':names};valid+=1;total+=len(names)
        except Exception as e:records[name]={'status':'TRIE_UNAVAILABLE_'+type(e).__name__,'names':set()};partial+=1
        if i%10==0:print(f'TRIE_PROGRESS={i}/{len(libs)}',flush=True)
    ctx['trie']=records
    return {'trie_inspected':valid,'trie_unavailable':partial,'names_found':total,'providers':len(libs)}

def indirect():
    # Darwin format exposes N_INDR alias names, without claiming that the
    # target implementation exists or that dyld can bind it.
    hints={};failures=0
    for name in ctx['roots']:
        entry=ctx['libs'].get(name)
        if not entry or entry['status']!='I386_PARSED':failures+=1;continue
        try:
            r=subprocess.run([str(NM),'--arch=i386','-m','--no-dyldinfo',str(entry['path'])],
                             capture_output=True,timeout=12)
            if r.returncode!=0 or len(r.stdout)>8<<20:raise ValueError('NM_FAILED')
            text=r.stdout.decode('utf8','replace')
            hints[name]=set(re.findall(r'\(indirect\)\s+(_[A-Za-z0-9_.$]+)\s+\(for',text))
        except Exception:failures+=1
    ctx['indirect']=hints
    return {'root_dylibs_scanned':len(hints),'unavailable':failures,'alias_name_hints':sum(map(len,hints.values()))}

def review():
    recs=[r for r in ctx['records'] if r['SH22_class']=='NO_NAME_IN_BOUNDED_REEXPORT_GRAPH']
    assert len(recs)==211
    libs=ctx['libs'];trie=ctx['trie'];counts=Counter();examples=[];full=[]
    for idx,rec in enumerate(recs,1):
        name=rec['name'];owner=rec['library'];visited=set();queue=deque([owner]);found=[];unknown=False
        while queue and len(visited)<96:
            lib=queue.popleft()
            if lib in visited:continue
            visited.add(lib)
            info=libs.get(lib);observed=trie.get(lib)
            if not info or info['status']!='I386_PARSED' or not observed or observed['status']!='TRIE_OUTPUT_PARSED':
                unknown=True;continue
            if name in observed['names']:found.append(lib)
            queue.extend(info['deps'])
        if queue:unknown=True
        if found:state='NAME_IN_TRIE_TEXT_EXPECTED_REEXPORT_GRAPH'
        elif name in ctx.get('indirect',{}).get(owner,set()):state='NINDR_NAME_HINT_IN_DIRECT_PROVIDER'
        elif unknown:state='INCONCLUSIVE_UNSCANNED_PROVIDER_OR_TRIE'
        else:state='NO_NAME_IN_SCANNED_NLIST_OR_TRIE'
        counts[state]+=1
        if state!='NAME_IN_TRIE_TEXT_EXPECTED_REEXPORT_GRAPH' and len(examples)<5:examples.append(name+'@'+owner.rsplit('/',1)[-1])
        full.append({'name':name,'library':owner,'weak':bool(rec['weak']), 'classification':state})
        if idx%50==0:print(f'IMPORT_PROGRESS={idx}/211',flush=True)
    ctx['remaining']=full
    return {'total':211,'classification':dict(counts),'sample':examples}

def weak():
    all_=ctx['records'];remain=[r for r in all_ if r['SH22_class']=='NO_NAME_IN_BOUNDED_REEXPORT_GRAPH']
    return {'original_weak':sum(bool(r['weak']) for r in all_), 'original_strong':sum(not bool(r['weak']) for r in all_),
            'remaining_weak':sum(bool(r['weak']) for r in remain),'remaining_strong':sum(not bool(r['weak']) for r in remain)}

def carbon():
    recs=ctx['remaining'];ls=[r for r in recs if r['library'].endswith('/Carbon')]
    if not ls:raise ValueError('CARBON_NOT_PRESENT')
    return {'remaining_carbon':len(ls),'states':dict(Counter(r['classification'] for r in ls)),
            'examples':[r['name'] for r in ls[:5]]}

def integrity():
    assert hashfile(BIN,8<<20)==PIN
    assert hashfile(PARSER,60000)==ctx['parser_sha']
    assert hashfile(SH22,2<<20)==ctx['sh22_sha']
    return {'inputs_unchanged':True,'guest_run':False,'audio':False}

gate('PINNED_ORIGINAL',original)
gate('SH22_REPORT',report22)
gate('RECONCILE_IMPORTS',reconcile)
gate('EXPAND_7_I386_DYLIBS',expand)
gate('TOKEN_PARSER_SELFTEST',selftest)
gate('LLVM_EXPORT_TRIE_SUPPORT',tool)
gate('READ_EXPORT_TRIES',trie)
gate('NINDR_ALIAS_INVENTORY',indirect)
gate('RECHECK_211_IMPORTS',review)
gate('WEAK_STRONG',weak)
gate('CARBON_DIAGNOSTIC',carbon)
gate('FINAL_INTEGRITY',integrity)
out['status']='SH23_COMPOSITE_STATIC_PASS' if all(s['state']=='PASS' for s in status) else 'SH23_COMPOSITE_STATIC_PARTIAL'
(O/'SH23-result.json').write_text(json.dumps(out,indent=2,sort_keys=True,default=lambda x:sorted(x) if isinstance(x,set) else str(x)))
print('RESULT='+out['status'],flush=True)
if out['status']!='SH23_COMPOSITE_STATIC_PASS':sys.exit(2)
