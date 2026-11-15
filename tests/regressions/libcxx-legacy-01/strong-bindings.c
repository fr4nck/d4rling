/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _DARWIN_C_SOURCE 1
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
extern void legacy0(void) __asm__("__ZNSt3__119__shared_weak_count12__add_sharedEv");
extern void legacy1(void) __asm__("__ZNSt3__119__shared_weak_count10__add_weakEv");
extern void legacy2(void) __asm__("__ZNSt3__119__shared_weak_count16__release_sharedEv");
extern void legacy3(void) __asm__("__ZNSt3__114__shared_count12__add_sharedEv");
extern void legacy4(void) __asm__("__ZNSt3__114__shared_count16__release_sharedEv");
/* Address-only references: no private C++ object layout or call is invented. */
static void (*const imports[])(void)={legacy0,legacy1,legacy2,legacy3,legacy4};
int main(void) {
 setbuf(stdout,NULL);
 for(unsigned i=0;i<sizeof(imports)/sizeof(*imports);i++) {
  Dl_info image;
  if(!dladdr((void*)imports[i],&image)||strcmp(image.dli_fname,"/usr/lib/libc++.1.dylib"))return 2;
  printf("BOUND %u image=%s\n",i,image.dli_fname);
 }
 printf("LEGACY_STRONG_BIND_PASS count=5 pointer=%lu\n",(unsigned long)sizeof(void*));
 return 0;
}
