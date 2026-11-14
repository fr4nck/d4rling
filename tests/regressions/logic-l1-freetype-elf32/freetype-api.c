/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _DARWIN_C_SOURCE 1
#include <dlfcn.h>
#include <stdio.h>
#include <unistd.h>
typedef void *FT_Library;
typedef void *FT_Face;
int main(void) {
    setbuf(stdout, NULL);
    printf("FT_API_BEGIN pointer_size=%lu\n", (unsigned long)sizeof(void *));
    void *module = dlopen("/usr/lib/native/libFreeType.dylib", RTLD_NOW | RTLD_LOCAL);
    if (!module) { fprintf(stderr, "FT_DYLD_FAIL %s\n", dlerror()); return 20; }
    int (*init)(FT_Library *) = dlsym(module, "FT_Init_FreeType");
    void (*version)(FT_Library, int *, int *, int *) = dlsym(module, "FT_Library_Version");
    int (*newface)(FT_Library, const char *, long, FT_Face *) = dlsym(module, "FT_New_Face");
    int (*done)(FT_Library) = dlsym(module, "FT_Done_FreeType");
    Dl_info image;
    if (!init || !version || !newface || !done || !dladdr((void *)init, &image)) return 21;
    printf("FT_WRAPPER image=%s\n", image.dli_fname);
    FT_Library library = NULL;
    int rc = init(&library);
    printf("FT_INIT rc=%d library_nonnull=%d\n", rc, library != NULL);
    if (rc || !library) return 22;
    int major = 0, minor = 0, patch = 0;
    version(library, &major, &minor, &patch);
    printf("FT_VERSION %d.%d.%d\n", major, minor, patch);
    if (major != 2 || minor != 13 || patch != 3) return 23;
    FT_Face face = NULL;
    rc = newface(library, "/logic-l1-deliberately-missing-font-20261114.ttf", 0, &face);
    printf("FT_MISSING_FACE rc=%d face_null=%d\n", rc, face == NULL);
    if (rc == 0 || face != NULL) return 24;
    rc = done(library);
    printf("FT_DONE rc=%d\n", rc);
    if (rc) return 25;
    puts("FT_API_PASS init/version/missing-face/done");
    sleep(2); /* bounded observation window for Linux /proc mappings */
    return 0;
}
