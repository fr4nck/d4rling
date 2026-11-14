/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _DARWIN_C_SOURCE 1
#include <dlfcn.h>
#include <stdio.h>
int main(void) {
    setbuf(stdout, NULL);
    printf("NATIVE_FREETYPE_BEGIN pointer_size=%lu\n", (unsigned long)sizeof(void *));
    void *module = dlopen("/usr/lib/native/libFreeType.dylib", RTLD_NOW | RTLD_LOCAL);
    if (!module) { fprintf(stderr, "NATIVE_FREETYPE_DYLD_FAIL %s\n", dlerror()); return 20; }
    void *symbol = dlsym(module, "FT_Init_FreeType");
    Dl_info image;
    if (!symbol || !dladdr(symbol, &image)) return 21;
    printf("NATIVE_FREETYPE_LOAD_PASS image=%s\n", image.dli_fname);
    return 0;
}
