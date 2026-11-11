#include <CarbonCore/MacMemory.h>
#include <CarbonCore/MacErrors.h>
#include <climits>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>
#include <malloc/malloc.h>
static int passed=0, failed=0;
#define CHECK(x) do { if(x) ++passed; else { ++failed; std::fprintf(stderr,"FAIL %d: %s\n",__LINE__,#x); }} while(0)
static int fail_alloc=0, fail_resize=0;
extern "C" void* __real_malloc(size_t);
extern "C" void* __real_realloc(void*,size_t);
extern "C" void* __wrap_malloc(size_t n) {
  if(fail_alloc && --fail_alloc==0) return nullptr;
  return __real_malloc(n);
}
extern "C" void* __wrap_realloc(void* p,size_t n) {
  if(fail_resize && --fail_resize==0) return nullptr;
  return __real_realloc(p,n);
}
int main() {
  CHECK(NewPtr(-1)==nullptr && MemError()==memFullErr);
  CHECK(NewPtrClear(-1)==nullptr && MemError()==memFullErr);
  Ptr p=NewPtr(3);
  CHECK(p && GetPtrSize(p)==3);
  std::memcpy(p,"abc",3);
  SetPtrSize(p,1);
  CHECK(MemError()==noErr && GetPtrSize(p)==1 && p[0]=='a');
  SetPtrSize(p,static_cast<long>(malloc_size(p))+1);
  CHECK(MemError()==memFullErr && GetPtrSize(p)==1);
  DisposePtr(p);
  CHECK(MemError()==noErr);
  DisposePtr(p);
  CHECK(MemError()==memAdrErr);
  CHECK(GetPtrSize(p)==0 && MemError()==memAdrErr);
  Ptr zero=NewPtr(0);
  CHECK(zero && GetPtrSize(zero)==0);
  DisposePtr(zero);
  Ptr cleared=NewPtrClear(8);
  CHECK(cleared && GetPtrSize(cleared)==8);
  CHECK(cleared && std::memcmp(cleared,"\0\0\0\0\0\0\0\0",8)==0);
  DisposePtr(cleared);
  fail_alloc=1;
  CHECK(NewPtr(10)==nullptr && MemError()==memFullErr);
  fail_alloc=2;
  CHECK(NewPtr(10)==nullptr && MemError()==memFullErr);
  fail_alloc=1;
  CHECK(NewEmptyHandle()==nullptr && MemError()==memFullErr);
  fail_alloc=2;
  CHECK(NewEmptyHandle()==nullptr && MemError()==memFullErr);
  fail_alloc=3;
  CHECK(NewHandle(99)==nullptr && MemError()==memFullErr);
  Handle h=NewHandle(3);
  CHECK(h && *h && GetHandleSize(h)==3);
  std::memcpy(*h,"abc",3);
  SetHandleSize(h,80);
  CHECK(MemError()==noErr && GetHandleSize(h)==80);
  CHECK(std::memcmp(*h,"abc",3)==0);
  SetHandleSize(h,1);
  CHECK(MemError()==noErr && GetHandleSize(h)==1 && (*h)[0]=='a');
  Ptr old=*h;
  fail_resize=1;
  SetHandleSize(h,32768);
  CHECK(MemError()==memFullErr && *h==old);
  CHECK(GetHandleSize(h)==1 && (*h)[0]=='a');
  HLock(h);
  CHECK(MemError()==noErr);
  SetHandleSize(h,32768);
  CHECK(MemError()==memLockedErr && *h==old && GetHandleSize(h)==1);
  HUnlock(h);
  CHECK(MemError()==noErr);
  SetHandleSize(h,32768);
  CHECK(MemError()==noErr && GetHandleSize(h)==32768 && (*h)[0]=='a');
  fail_alloc=1;
  old=*h;
  ReallocateHandle(h,100);
  CHECK(MemError()==memFullErr && *h==old && GetHandleSize(h)==32768);
  ReallocateHandle(h,100);
  CHECK(MemError()==noErr && GetHandleSize(h)==100 && *h!=old);
  EmptyHandle(h);
  CHECK(MemError()==noErr && !*h);
  CHECK(GetHandleSize(h)==0 && MemError()==nilHandleErr);
  SetHandleSize(h,4);
  CHECK(MemError()==noErr && GetHandleSize(h)==4);
  DisposeHandle(h);
  CHECK(MemError()==noErr);
  DisposeHandle(h);
  CHECK(MemError()==memWZErr);
  CHECK(GetHandleSize(h)==0 && MemError()==memWZErr);
  Handle copy=nullptr;
  CHECK(PtrToHand("abc",&copy,3)==noErr);
  Handle original=copy;
  CHECK(HandToHand(&copy)==noErr && copy!=original);
  CHECK(GetHandleSize(copy)==3 && std::memcmp(*copy,"abc",3)==0);
  CHECK(HandAndHand(copy,copy)==noErr);
  CHECK(GetHandleSize(copy)==6 && std::memcmp(*copy,"abcabc",6)==0);
  CHECK(PtrAndHand(*copy+1,copy,2)==noErr);
  CHECK(GetHandleSize(copy)==8 && std::memcmp(*copy,"abcabcbc",8)==0);
  CHECK(PtrToXHand(*copy+3,copy,3)==noErr);
  CHECK(GetHandleSize(copy)==3 && std::memcmp(*copy,"abc",3)==0);
  CHECK(HandAndHand(original,copy)==noErr);
  CHECK(GetHandleSize(copy)==6 && std::memcmp(*copy,"abcabc",6)==0);
  CHECK(PtrAndHand(nullptr,copy,3)==paramErr);
  CHECK(GetHandleSize(copy)==6);
  CHECK(HandToHand(nullptr)==paramErr);
  DisposeHandle(original);
  DisposeHandle(copy);
  CHECK(NewHandle(-1)==nullptr && MemError()==memFullErr);
  Handle empty=NewEmptyHandle();
  CHECK(empty && *empty==nullptr);
  Handle duplicate=empty;
  CHECK(HandToHand(&duplicate)==noErr && duplicate!=empty && *duplicate==nullptr);
  DisposeHandle(duplicate);
  DisposeHandle(empty);
  Ptr t=NewPtr(1);
  CHECK(t!=nullptr && MemError()==noErr);
  std::thread worker([] { CHECK(NewHandle(-1)==nullptr && MemError()==memFullErr); });
  worker.join();
  CHECK(MemError()==noErr);
  DisposePtr(t);
  std::printf("CARBONCORE_MEMORY_M1_HOST: %d PASS, %d FAIL\n",passed,failed);
  return failed?1:0;
}
