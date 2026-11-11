// SPDX-License-Identifier: GPL-3.0-or-later
// Integration contracts: REAL M2 MacMemory.cpp + REAL R2 ResourcesImpl.cpp.
#include "ResourcesImpl.h"
#include <CarbonCore/MacErrors.h>
#include <cerrno>
#include <climits>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/stat.h>
#include <sys/xattr.h>
#include <unistd.h>
static int passed = 0, failed = 0;
#define CHECK(expr) do { if(expr){++passed;}else{++failed;std::fprintf(stderr,"I1 FAIL line %d: %s\n",__LINE__,#expr);} }while(0)
static int failMallocAt = 0;
extern "C" void* __real_malloc(size_t);
extern "C" void* __wrap_malloc(size_t size) {
    if (failMallocAt > 0 && --failMallocAt == 0) return nullptr;
    return __real_malloc(size);
}
ssize_t getxattr(const char*,const char*,void*,size_t,unsigned int,int) { errno=ENODATA; return -1; }
int setxattr(const char*,const char*,const void*,size_t,unsigned int,int) { errno=ENOTSUP; return -1; }
ssize_t listxattr(const char*,char*,size_t,int) { return 0; }
static void put16(std::vector<uint8_t>& f, size_t at, uint16_t v) {f.at(at)=uint8_t(v>>8);f.at(at+1)=uint8_t(v);}
static void put32(std::vector<uint8_t>& f, size_t at, uint32_t v) {f.at(at)=uint8_t(v>>24);f.at(at+1)=uint8_t(v>>16);f.at(at+2)=uint8_t(v>>8);f.at(at+3)=uint8_t(v);}
static std::vector<uint8_t> makeFork() {
  const size_t d=256, m=512;
  std::vector<uint8_t> f(m+55, 0);
  put32(f,0,d);put32(f,4,m);put32(f,8,7);put32(f,12,55);
  put32(f,d,3); f[d+4]='A'; f[d+5]='B'; f[d+6]='C';
  put16(f,m+22,0x123);put16(f,m+24,28);put16(f,m+26,50);
  put16(f,m+28,0);put32(f,m+30,0x53545220);put16(f,m+34,0);put16(f,m+36,10);
  put16(f,m+38,128);put16(f,m+40,0); f[m+42]=0x20;
  f[m+50]=4;f[m+51]='n';f[m+52]='a';f[m+53]='m';f[m+54]='e';
  return f;
}
static std::string makeFile(const std::vector<uint8_t>& bytes){
  std::string p = std::string(std::getenv("TMPDIR")?std::getenv("TMPDIR"):"/tmp")+"/d4-i1-XXXXXX";
  std::vector<char> name(p.begin(),p.end());name.push_back('\0');int fd=mkstemp(name.data());
  if(fd<0)throw std::runtime_error("mkstemp");
  size_t off=0;while(off<bytes.size()){
    ssize_t n=write(fd,bytes.data()+off,bytes.size()-off);
    if(n<=0){close(fd);unlink(name.data());throw std::runtime_error("write");}
    off+=static_cast<size_t>(n);
  }close(fd);return name.data();
}
int main(){
  const auto source=makeFork();
  const std::string path=makeFile(source);
  {
    Resources resources(path.c_str(),fsRdWrPerm,false);
    CHECK(resources.data().size()==1);
    auto* record=resources.data().at(0x53545220).idMap.at(128);
    Handle h=record->getHandle();
    CHECK(h && *h);
    CHECK(MemError()==noErr);
    CHECK(GetHandleSize(h)==3);
    CHECK(std::memcmp(*h,"ABC",3)==0);
    DisposePtr(*h);
    CHECK(MemError()==memAdrErr);
    CHECK(GetHandleSize(h)==3 && std::memcmp(*h,"ABC",3)==0);
    HLock(h);CHECK(MemError()==noErr);
    EmptyHandle(h); CHECK(MemError()==memPurErr);
    CHECK(*h && GetHandleSize(h)==3);
    HUnlock(h);CHECK(MemError()==noErr);
    EmptyHandle(h);CHECK(MemError()==noErr && *h==nullptr);
    // Apple's GetResource rehydrates a released/empty master pointer.
    Handle again=record->getHandle();
    CHECK(again==h);
    CHECK(again && *again && GetHandleSize(again)==3);
    if(again && *again)CHECK(std::memcmp(*again,"ABC",3)==0);
    else CHECK(false);
    if(again && *again){
      SetHandleSize(again,5);CHECK(MemError()==noErr);
      std::memcpy(*again,"HELLO",5);
      record->dataChanged();
      CHECK(record->dataBacking==std::vector<uint8_t>({'H','E','L','L','O'}));
    }
    CHECK(resources.save()==noErr);
  }
  {
    Resources back(path.c_str(),fsRdWrPerm,false);
    auto* record=back.data().at(0x53545220).idMap.at(128);
    Handle h=record->getHandle();
    CHECK(h && *h && GetHandleSize(h)==5);
    if(h && *h && GetHandleSize(h)==5)CHECK(std::memcmp(*h,"HELLO",5)==0);
    else CHECK(false);
    CHECK(back.readPartial(h,1,nullptr,0)==noErr);
    CHECK(back.readPartial(h,-1,nullptr,0)==paramErr);
    CHECK(back.writePartial(h,3,"XYZ",3)==paramErr);
    CHECK(back.writePartial(h,1,"oo",2)==noErr);
    if(h && *h && GetHandleSize(h)>=5) CHECK(std::memcmp(*h,"HELLO",5)==0); // TB40: stale handle
    else CHECK(false);
    char readback[6]{};
    CHECK(back.readPartial(h,0,readback,5)==noErr);
    CHECK(std::memcmp(readback,"HooLO",5)==0);
  }
  {
    Resources back(path.c_str(),fsRdPerm,false);
    auto* record=back.data().at(0x53545220).idMap.at(128);
    CHECK(record->dataBacking==std::vector<uint8_t>({'H','o','o','L','O'}));
    CHECK(back.save()==wPrErr);
  }
  // Lazy loading exercises actual M2 allocation failure and recovery paths.
  Resources::setCreateHandles(false);
  {
    Resources lazy(path.c_str(), fsRdWrPerm, false);
    CHECK(lazy.handleMap().empty());
    auto* data = lazy.data().at(0x53545220).idMap.at(128);
    failMallocAt = 1;
    CHECK(data->getHandle()==nullptr && MemError()==memFullErr);
    CHECK(lazy.handleMap().empty());
    Handle h = data->getHandle();
    CHECK(h && *h && GetHandleSize(h)==5);
    CHECK(h && *h && std::memcmp(*h,"HooLO",5)==0);
    CHECK(lazy.dataByHandle(h)==data);
    EmptyHandle(h);
    CHECK(MemError()==noErr && *h==nullptr);
    failMallocAt = 1; // failure of ReallocateHandle first allocation
    CHECK(data->getHandle()==nullptr && MemError()==memFullErr && *h==nullptr);
    failMallocAt = 2; // failure of ReallocateHandle bookkeeping allocation
    CHECK(data->getHandle()==nullptr && MemError()==memFullErr && *h==nullptr);
    Handle recovered = data->getHandle();
    CHECK(recovered==h && *recovered && GetHandleSize(recovered)==5);
    CHECK(std::memcmp(*recovered,"HooLO",5)==0);
    CHECK(lazy.dataByHandle(recovered)==data);
    data->releaseHandle(true);
    CHECK(lazy.dataByHandle(h)==nullptr);
    Handle again = data->getHandle();
    CHECK(again && *again && GetHandleSize(again)==5);
    CHECK(std::memcmp(*again,"HooLO",5)==0);
  }
  Resources::setCreateHandles(true);
  // Empty resource: a non-null master is returned with a logical zero-length
  // allocation. After a purge, it must be recoverable as zero bytes too.
  {
    Resources empty(path.c_str(), fsRdWrPerm, false);
    auto* entry=empty.data().at(0x53545220).idMap.at(128);
    Handle h=entry->getHandle();
    CHECK(h && *h);
    SetHandleSize(h,0);
    CHECK(MemError()==noErr && GetHandleSize(h)==0);
    entry->dataChanged();
    CHECK(entry->dataBacking.empty());
    CHECK(empty.save()==noErr);
    EmptyHandle(h);
    CHECK(MemError()==noErr && *h==nullptr);
    CHECK(entry->getHandle()==h && *h!=nullptr);
    CHECK(GetHandleSize(h)==0 && MemError()==noErr);
  }
  {
    Resources back(path.c_str(), fsRdPerm, false);
    auto* entry=back.data().at(0x53545220).idMap.at(128);
    CHECK(entry->dataBacking.empty());
    CHECK(entry->getHandle() && GetHandleSize(entry->getHandle())==0);
  }
  CHECK(unlink(path.c_str())==0);
  std::printf("CARBONCORE_I1_REAL_UNITS: %d PASS, %d FAIL\n",passed,failed);
  return failed?1:0;
}
