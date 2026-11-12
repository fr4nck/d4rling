#!/usr/bin/env python3
"""I2-B: verify actual production cache, SetResInfo and clearCaches functions.

Host EXTRACTED functions, never a substitute for complete CarbonCore linkage.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, default=ROOT/'src/frameworks/CoreServices/src/CarbonCore/Resources.cpp')
p.add_argument('--compiler', choices=['g++','clang++'], default='g++')
p.add_argument('--opt', choices=['-O0','-O2'], default='-O0')
p.add_argument('--expect-fail', action='store_true')
p.add_argument('--mutation', choices=['missing-invalidation'], default=None)
a = p.parse_args()
s = a.source.read_text()

def excerpt(start, end, expected=None):
    i = s.index(start)
    j = s.index(end, i + len(start))
    t = s[i:j]
    if expected:
        r = subprocess.run(['git','hash-object','--stdin'], input=t, text=True, capture_output=True)
        if r.returncode or r.stdout.strip() != expected: raise RuntimeError('Unexpected snippet '+start)
    return t

# Never rebuild these functions from a local handwritten approximation when
# using the checkout: pin exactly what the GitHub revision contains.
full_source = a.source.resolve() == (ROOT/'src/frameworks/CoreServices/src/CarbonCore/Resources.cpp').resolve()
cache = excerpt('static std::vector<Resources::ResourceData*> resourcesOfTypeCache;', 'ResourceCount CountResources' if full_source else 'void SetResInfo(', 'fb81dbcfbeb931a4227737b8e93292e1023f0bc2' if full_source else None)
set_info = excerpt('void SetResInfo(', 'void SetResAttrs(' if full_source else 'static void clearCaches()\n{', '1a94fafd537d96d7b63b7cd305172894ca0aa6be' if full_source else None)
clear = excerpt('static void clearCaches()\n{', 'void WriteResource(', '66d54449ecd9d005dd46fb9d7d1201d1e08f51f5') if full_source else s[s.index('static void clearCaches()\n{'):] 
if a.mutation:
    anchor = '\tclearCaches();\n'
    if set_info.count(anchor) != 1: raise RuntimeError('Invalid mutation anchor')
    set_info = set_info.replace(anchor, '', 1)

header = '''#include <unordered_map>
#include <vector>
#include <memory>
#include <string>
#include <set>
#include <mutex>
#include <cstdio>
using Handle = char**; using ResID=int; using ResType=int;using ConstStr255Param=const unsigned char*;
constexpr int noErr=0, resNotFound=-192;
struct Resources {
 struct ResourceData { ResID id; ResType type; std::string name; Handle handle; };
 struct ResourceTypeData { std::vector<std::unique_ptr<ResourceData>> resources; std::unordered_map<ResID, ResourceData*> idMap; std::unordered_map<std::string,ResourceData*> nameMap; };
 std::unordered_map<ResType,ResourceTypeData> types;
 auto& data() { return types; }
 void add(ResType t,ResID id,const std::string& name,Handle h){
  auto& d=types[t]; auto r=std::make_unique<ResourceData>();r->id=id;r->type=t;r->name=name;r->handle=h;
  auto* ptr=r.get();d.resources.push_back(std::move(r));d.idMap[id]=ptr;d.nameMap[name]=ptr;
 }
};
static std::unordered_map<int,Resources*> g_resources;
static std::mutex g_resourcesLock;
static int g_lastError=noErr;
static std::set<ResType> allTypesCache;
static void clearCaches();
static Resources::ResourceData* findResourceDataByHandle(Handle h,Resources** out=nullptr){
 for(auto& [ref,owner]:g_resources)for(auto& [t,group]:owner->data())for(auto& record:group.resources)
 if(record->handle==h){if(out)*out=owner;return record.get();}
 return nullptr;
}
'''
body = '''
static int pass=0, fail=0;
#define CHECK(x) do { if(x)++pass;else {++fail;fprintf(stderr,"FAIL %d %s\\n",__LINE__,#x);} } while(0)
int main(){
 Resources rs; char* block=nullptr;Handle h=&block;char* block2=nullptr;Handle h2=&block2;
 rs.add(100,10,"alpha",h);rs.add(100,12,"beta",h2);g_resources[1]=&rs;
 auto& orig=resourcesOfTypeMap(100);
 CHECK(orig.count(10)==1); CHECK(orig.count(12)==1);
 auto& named=resourcesOfTypeNameMap(100);
 CHECK(named.count("alpha")==1);CHECK(named.count("beta")==1);
 const unsigned char delta[]={5,'d','e','l','t','a'};
 SetResInfo(h,11,delta);
 CHECK(g_lastError==noErr);
 CHECK(rs.data().at(100).idMap.count(11)==1);
 CHECK(rs.data().at(100).idMap.count(10)==0);
 CHECK(rs.data().at(100).nameMap.count("delta")==1);
 CHECK(rs.data().at(100).nameMap.count("alpha")==0);
 auto& latestId=resourcesOfTypeMap(100);
 CHECK(latestId.count(11)==1);
 CHECK(latestId.count(10)==0);
 CHECK(latestId.count(12)==1);
 auto& latestName=resourcesOfTypeNameMap(100);
 CHECK(latestName.count("delta")==1);
 CHECK(latestName.count("alpha")==0);
 CHECK(latestName.count("beta")==1);
 const unsigned char echo[]={4,'e','c','h','o'};
 SetResInfo(h2,12,echo);
 CHECK(g_lastError==noErr);
 CHECK(resourcesOfTypeNameMap(100).count("echo")==1);
 CHECK(resourcesOfTypeNameMap(100).count("beta")==0);
 SetResInfo(nullptr,5,delta);
 CHECK(g_lastError==resNotFound);
 CHECK(resourcesOfTypeMap(100).count(11)==1);
 std::printf("CARBONCORE_I2_SETRESINFO_EXTRACTED: %d PASS, %d FAIL\\n",pass,fail);
 return fail?1:0;
}
'''
with tempfile.TemporaryDirectory(prefix='d4-i2-setresinfo-') as tmp:
    path = Path(tmp)/'harness.cpp';exe=Path(tmp)/'test'
    path.write_text(header+cache+set_info+clear+body)
    command=[a.compiler,'-std=c++17',a.opt,'-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(path),'-o',str(exe)]
    built=subprocess.run(command,text=True,capture_output=True)
    if built.returncode:raise RuntimeError('COMPILATION FAILED: '+built.stderr)
    run=subprocess.run([str(exe)],text=True,capture_output=True)
    print(run.stdout.strip())
    if run.stderr:print(run.stderr.strip())
    if a.expect_fail:
        if run.returncode==1 and 'FAIL ' in run.stderr:raise SystemExit(0)
        raise SystemExit('EXPECTED FUNCTIONAL FAILURE NOT SEEN')
    if run.returncode:raise SystemExit(1)
