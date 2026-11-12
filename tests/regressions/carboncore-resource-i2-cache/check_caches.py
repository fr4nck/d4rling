#!/usr/bin/env python3
"""Host unit test of three ACTUAL cached lookup functions extracted from Resources.cpp.

The implementation is extracted from the production file; only types and fixtures
are host substitutes. This does not compile/link the whole CarbonCore framework.
Pin the source blob and treat host-extracted code, full C++ TU and Mach-O i386
as distinct qualification levels.
"""
import argparse
import pathlib
import subprocess
import tempfile

ROOT=pathlib.Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser()
p.add_argument('--source',type=pathlib.Path,default=ROOT/'src/frameworks/CoreServices/src/CarbonCore/Resources.cpp')
p.add_argument('--compiler',default='g++')
p.add_argument('--opt',choices=['-O0','-O2'],default='-O0')
p.add_argument('--expect-fail',action='store_true',help='verify baseline is rejected')
p.add_argument('--mutation',choices=['no-clear-list','no-clear-id','no-clear-name','wrong-name-cache'],default=None)
a=p.parse_args()
if not a.source.is_file(): raise SystemExit('Missing production file: '+str(a.source))
s=a.source.read_text()
start=s.index('static std::vector<Resources::ResourceData*> resourcesOfTypeCache;')
end=s.index('ResourceCount CountResources',start) if 'ResourceCount CountResources' in s[start:] else len(s)
fragment=s[start:end]
if a.source.resolve()==(ROOT/'src/frameworks/CoreServices/src/CarbonCore/Resources.cpp').resolve():
    check=subprocess.run(['git','hash-object','--stdin'],input=fragment,text=True,capture_output=True)
    if check.returncode or check.stdout.strip()!='fb81dbcfbeb931a4227737b8e93292e1023f0bc2':
        raise SystemExit('BLOCKED: resource lookup function blob changed; requalify this lot')
mutants={
'no-clear-list':('if (resourcesOfTypeCacheType != type)\n\t{\n\t\trv.clear();','if (resourcesOfTypeCacheType != type)\n\t{'),
'no-clear-id':('if (resourcesOfTypeMapCacheType != type)\n\t{\n\t\trv.clear();','if (resourcesOfTypeMapCacheType != type)\n\t{'),
'no-clear-name':('if (resourcesOfTypeNameMapCacheType != type)\n\t{\n\t\trv.clear();','if (resourcesOfTypeNameMapCacheType != type)\n\t{'),
'wrong-name-cache':('if (resourcesOfTypeNameMapCacheType != type)','if (resourcesOfTypeMapCacheType != type)'),
}
if a.mutation:
    old,new=mutants[a.mutation]
    if fragment.count(old)!=1:raise RuntimeError('mutation anchor not unique: '+a.mutation)
    fragment=fragment.replace(old,new,1)

header='''#include <memory>\n#include <vector>\n#include <string>\n#include <unordered_map>\n#include <cstdio>\nusing ResType=int; using ResID=int;
struct Resources {
 struct ResourceData {ResID id; ResType type; std::string name;};
 struct ResourceTypeData {std::vector<std::unique_ptr<ResourceData>> resources; std::unordered_map<ResID,ResourceData*> idMap; std::unordered_map<std::string,ResourceData*> nameMap;};
 std::unordered_map<ResType,ResourceTypeData> types;
 std::unordered_map<ResType,ResourceTypeData>& data(){return types;}
 void add(ResType type,ResID id,const char* name){
  ResourceTypeData& d=types[type]; auto e=std::make_unique<ResourceData>();
  e->id=id; e->type=type; e->name=name;auto* ptr=e.get();d.resources.push_back(std::move(e));d.idMap[id]=ptr;d.nameMap[name]=ptr;
 }
};
static std::unordered_map<int,Resources*> g_resources;
'''
body='''
static int pass=0, fail=0;
#define CHECK(x) do {if(x) ++pass;else {++fail;std::fprintf(stderr,"FAIL %d %s\\n",__LINE__,#x);}} while(0)
int main(){
 constexpr ResType A=1,B=2,C=3;
 Resources o;o.add(A,10,"alpha");o.add(B,20,"bravo");
 g_resources.emplace(1,&o);
 auto& a=resourcesOfType(A);CHECK(a.size()==1);CHECK(a.size()==1 && a[0]->id==10);
 auto& b=resourcesOfType(B);CHECK(b.size()==1);CHECK(b.size()==1 && b[0]->id==20);
 auto& c=resourcesOfType(C);CHECK(c.empty());
 auto& d=resourcesOfType(A);CHECK(d.size()==1);CHECK(d.size()==1 && d[0]->id==10);
 auto& ia=resourcesOfTypeMap(A);CHECK(ia.size()==1);CHECK(ia.count(10)==1);
 auto& ib=resourcesOfTypeMap(B);CHECK(ib.size()==1);CHECK(ib.count(20)==1);CHECK(ib.count(10)==0);
 auto& ic=resourcesOfTypeMap(C);CHECK(ic.empty());
 auto& na=resourcesOfTypeNameMap(A);CHECK(na.size()==1);CHECK(na.count("alpha")==1);
 auto& nb=resourcesOfTypeNameMap(B);CHECK(nb.size()==1);CHECK(nb.count("bravo")==1);CHECK(nb.count("alpha")==0);
 auto& nc=resourcesOfTypeNameMap(C);CHECK(nc.empty());
 auto& nd=resourcesOfTypeNameMap(A);CHECK(nd.size()==1);CHECK(nd.count("alpha")==1);
 std::printf("CARBONCORE_I2_CACHE_EXTRACTED: %d PASS, %d FAIL\\n",pass,fail);
 return fail?1:0;
}
'''
with tempfile.TemporaryDirectory(prefix='d4-i2-cache-') as td:
    src=pathlib.Path(td)/'test.cpp';binary=pathlib.Path(td)/'test';src.write_text(header+fragment+body)
    cmd=[a.compiler,'-std=c++17',a.opt,'-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(src),'-o',str(binary)]
    run=subprocess.run(cmd,text=True,capture_output=True)
    if run.returncode:raise SystemExit(f'COMPILE FAIL: {run.stderr}')
    run=subprocess.run([str(binary)],text=True,capture_output=True)
    print(f'{a.compiler} {a.opt} {run.stdout.strip()} expected_fail={a.expect_fail} mutation={a.mutation or "none"}')
    if run.stderr:print(run.stderr.strip())
    if a.expect_fail:
        if run.returncode==1 and 'FAIL ' in run.stderr:raise SystemExit(0)
        raise SystemExit('ERROR: expected functional failure was not detected')
    if run.returncode!=0:raise SystemExit(1)
