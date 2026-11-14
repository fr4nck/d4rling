/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _DARWIN_C_SOURCE 1
#include <dlfcn.h>
#include <stdio.h>
struct symbol_request { const char *provider; const char *name; };
#include "logic-system-imports.h"
int main(void) {
    unsigned missing = 0, checked = 0;
    setbuf(stdout, NULL);
    for (unsigned i = 0; i < sizeof(requests)/sizeof(requests[0]); ++i) {
        const struct symbol_request *r = &requests[i];
        void *library = dlopen(r->provider, RTLD_NOW | RTLD_LOCAL);
        if (!library) { printf("PROVIDER_LOAD_FAIL %s %s\n", r->provider, dlerror()); return 20; }
        void *symbol = dlsym(library, r->name);
        printf("LOOKUP provider=%s name=%s found=%d\n", r->provider, r->name, symbol != NULL);
        missing += symbol == NULL;
        checked++;
    }
    printf("LOGIC_SYMBOL_LOOKUP_COMPLETE checked=%u missing=%u\n", checked, missing);
    return 0; /* Completion of an inventory, not a functional API verdict. */
}
