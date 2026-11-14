/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _DARWIN_C_SOURCE 1
#include <dlfcn.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <string.h>
int main(void) {
    const char *path = "/System/Library/Frameworks/Carbon.framework/Versions/A/Carbon";
    setbuf(stdout, NULL);
    printf("LOGIC_L1_PROBE pointer_size=%lu\n", (unsigned long)sizeof(void *));
    void *library = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!library) { fprintf(stderr, "DEPENDENCY_LOAD_FAIL %s\n", dlerror()); return 20; }
    printf("DEPENDENCY_LOAD_PASS %s\n", path);
    const char *symbols[] = { "GetCurrentEventLoop", "AEInteractWithUser", "HomeResFile" };
    for (unsigned i = 0; i < sizeof(symbols) / sizeof(symbols[0]); ++i) {
        void *symbol = dlsym(library, symbols[i]);
        Dl_info image;
        printf("SYMBOL %s found=%d", symbols[i], symbol != NULL);
        if (symbol && dladdr(symbol, &image)) printf(" image=%s", image.dli_fname);
        puts("");
    }
    return 0;
}
