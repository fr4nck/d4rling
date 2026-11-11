// SPDX-License-Identifier: GPL-3.0-or-later
#include <CarbonCore/MacMemory.h>
#include <CarbonCore/MacErrors.h>
#include <climits>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>
#include <atomic>
#include <vector>
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
  CHECK(MemError()==nilHandleErr && *h==nullptr);
  ReallocateHandle(h,4);
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
  CHECK(HandToHand(&duplicate)==nilHandleErr && duplicate==empty && *duplicate==nullptr);
  DisposeHandle(empty);
  Ptr t=NewPtr(1);
  CHECK(t!=nullptr && MemError()==noErr);
  std::thread worker([] { CHECK(NewHandle(-1)==nullptr && MemError()==memFullErr); });
  worker.join();
  CHECK(MemError()==noErr);
  DisposePtr(t);
  // M2: locked handles must not be emptied or reallocated.
  Handle locked = NewHandle(12);
  CHECK(locked && GetHandleSize(locked)==12);
  std::memcpy(*locked, "hello world!",12);
  Ptr lockedData=*locked;
  HLock(locked);
  CHECK(MemError()==noErr);
  HLock(locked);  // lock is a bit, not a reference count
  CHECK(MemError()==noErr);
  EmptyHandle(locked);
  CHECK(MemError()==memPurErr && *locked==lockedData);
  CHECK(GetHandleSize(locked)==12 && std::memcmp(*locked,"hello world!",12)==0);
  ReallocateHandle(locked, 100);
  CHECK(MemError()==memPurErr && *locked==lockedData && GetHandleSize(locked)==12);
  HUnlock(locked);
  CHECK(MemError()==noErr);
  EmptyHandle(locked);
  CHECK(MemError()==noErr && *locked==nullptr);
  EmptyHandle(locked);
  CHECK(MemError()==noErr && *locked==nullptr);
  HLock(locked);
  CHECK(MemError()==nilHandleErr);
  HUnlock(locked);
  CHECK(MemError()==nilHandleErr);
  SetHandleSize(locked,0);
  CHECK(MemError()==nilHandleErr && *locked==nullptr);
  ReallocateHandle(locked, 6);
  CHECK(MemError()==noErr && *locked && GetHandleSize(locked)==6);
  // A handle-owned block cannot be disposed as a nonrelocatable Ptr.
  lockedData=*locked;
  DisposePtr(lockedData);
  CHECK(MemError()==memAdrErr && *locked==lockedData);
  CHECK(GetHandleSize(locked)==6 && MemError()==noErr);
  // Both allocation steps are made before replacing the old block.
  fail_alloc=1;
  ReallocateHandle(locked, 1000);
  CHECK(MemError()==memFullErr && *locked==lockedData && GetHandleSize(locked)==6);
  fail_alloc=2;
  ReallocateHandle(locked, 1000);
  CHECK(MemError()==memFullErr && *locked==lockedData && GetHandleSize(locked)==6);
  ReallocateHandle(locked, 0);
  CHECK(MemError()==noErr && *locked && GetHandleSize(locked)==0);
  ReallocateHandle(locked, 10);
  CHECK(MemError()==noErr && GetHandleSize(locked)==10);
  DisposeHandle(locked);
  CHECK(MemError()==noErr);
  HLock(locked);
  CHECK(MemError()==memWZErr);
  HUnlock(locked);
  CHECK(MemError()==memWZErr);
  EmptyHandle(locked);
  CHECK(MemError()==memWZErr);
  ReallocateHandle(locked, 100);
  CHECK(MemError()==memWZErr);
  SetHandleSize(locked, 100);
  CHECK(MemError()==memWZErr);
  CHECK(GetHandleSize(locked)==0 && MemError()==memWZErr);
  // Passing a fake/stale handle never dereferences an unknown master pointer.
  char bogus=0;
  Ptr bogusPtr=&bogus;
  Handle fake=&bogusPtr;
  EmptyHandle(fake);
  CHECK(MemError()==memWZErr && *fake==bogusPtr);
  SetHandleSize(fake, 80);
  CHECK(MemError()==memWZErr && *fake==bogusPtr);
  ReallocateHandle(fake, 80);
  CHECK(MemError()==memWZErr && *fake==bogusPtr);
  HLock(fake);
  CHECK(MemError()==memWZErr);
  HUnlock(fake);
  CHECK(MemError()==memWZErr);
  DisposeHandle(fake);
  CHECK(MemError()==memWZErr);
  CHECK(GetHandleSize(fake)==0 && MemError()==memWZErr);
  CHECK(PtrToXHand("x", fake, 1)==memWZErr);
  CHECK(PtrAndHand("x", fake, 1)==memWZErr);
  Handle live=NewHandle(2);
  CHECK(HandAndHand(fake,live)==memWZErr);
  CHECK(HandAndHand(live,fake)==memWZErr);
  DisposeHandle(live);
  CHECK(*fake==bogusPtr);
  // A forged master pointer must not steal a tracked Ptr or a second handle.
  Handle owner=NewHandle(5);
  Ptr ownerData=*owner;
  Ptr foreign=NewPtr(5);
  CHECK(owner && foreign && GetHandleSize(owner)==5);
  *owner=foreign;
  CHECK(GetHandleSize(owner)==0 && MemError()==memWZErr);
  SetHandleSize(owner, 12);
  CHECK(MemError()==memWZErr && *owner==foreign);
  DisposeHandle(owner);
  CHECK(MemError()==memWZErr && *owner==foreign);
  EmptyHandle(owner);
  CHECK(MemError()==memWZErr && *owner==foreign);
  ReallocateHandle(owner, 8);
  CHECK(MemError()==memWZErr && *owner==foreign);
  CHECK(GetPtrSize(foreign)==5);
  *owner=ownerData;
  DisposeHandle(owner);
  CHECK(MemError()==noErr);
  DisposePtr(foreign);
  CHECK(MemError()==noErr);
  Handle one=NewHandle(2);
  Handle two=NewHandle(3);
  Ptr originalOne=*one;
  *one=*two;
  CHECK(GetHandleSize(one)==0 && MemError()==memWZErr);
  DisposeHandle(one);
  CHECK(MemError()==memWZErr && GetHandleSize(two)==3);
  *one=originalOne;
  DisposeHandle(one);
  DisposeHandle(two);
  CHECK(MemError()==noErr);
  // A zero-length allocated handle is distinct from a purged handle.
  Handle zeroHandle=NewHandle(0);
  CHECK(zeroHandle && *zeroHandle && GetHandleSize(zeroHandle)==0);
  HLock(zeroHandle);
  CHECK(MemError()==noErr);
  EmptyHandle(zeroHandle);
  CHECK(MemError()==memPurErr && *zeroHandle);
  HUnlock(zeroHandle);
  DisposeHandle(zeroHandle);
  CHECK(MemError()==noErr);
  // Parallel independent handle churn: registry updates and thread-local errors.
  std::atomic<int> workerFailures{0};
  std::vector<std::thread> workers;
  for (int tid=0; tid<4; ++tid) {
    workers.emplace_back([&] {
      for (int i=0; i<250; ++i) {
        Handle item=NewHandle(8);
        if (!item || MemError()!=noErr) { ++workerFailures; continue; }
        std::memset(*item, 0x5a, 8);
        SetHandleSize(item, 1024);
        if (MemError()!=noErr || GetHandleSize(item)!=1024 ||
            static_cast<unsigned char>((*item)[0])!=0x5a) ++workerFailures;
        HLock(item);
        if (MemError()!=noErr) ++workerFailures;
        HUnlock(item);
        DisposeHandle(item);
        if (MemError()!=noErr) ++workerFailures;
      }
    });
  }
  for (auto& worker : workers) worker.join();
  CHECK(workerFailures==0);
  // Explicitly attempt negative sizes and confirm they never destroy content.
  Handle intact=NewHandle(5);
  std::memcpy(*intact,"hello",5);
  Ptr before=*intact;
  SetHandleSize(intact,-1);
  CHECK(MemError()==memFullErr && *intact==before);
  CHECK(GetHandleSize(intact)==5 && std::memcmp(*intact,"hello",5)==0);
  ReallocateHandle(intact,-1);
  CHECK(MemError()==memFullErr && *intact==before);
  DisposeHandle(intact);
  std::printf("CARBONCORE_MEMORY_M2_HOST: %d PASS, %d FAIL\n",passed,failed);
  return failed?1:0;
}
