/* SPDX-License-Identifier: GPL-3.0-or-later
 * AUDIO-I386: native ELF32 check of the private libpulse (no Darling). dlopen with
 * RTLD_NOW (every symbol bound), library version, mapped file, then a real
 * connection to the server named by PULSE_SERVER and its server info. Plays nothing.
 * Prototypes follow the public PulseAudio API (pulse/context.h, introspect.h). */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct { int format; uint32_t rate; uint8_t channels; } ss_t;
typedef struct { const char *user_name, *host_name, *server_version, *server_name; ss_t sample_spec;
                 const char *default_sink_name; } server_info_t;
static int done;
static void info_cb(void *c, const server_info_t *i, void *u)
{
    (void)c; (void)u;
    printf("PA32_SERVER name=%s version=%s default_sink=%s rate=%u channels=%u\n", i->server_name,
           i->server_version, i->default_sink_name, i->sample_spec.rate, i->sample_spec.channels);
    done = 1;
}

int main(void)
{
    void *h = dlopen("libpulse.so.0", RTLD_NOW | RTLD_LOCAL);
    if (!h) { printf("PA32_DLOPEN_FAIL %s\n", dlerror()); return 3; }
    printf("PA32_ABI pointer_bits=%u\n", (unsigned)(sizeof(void *) * 8));
    const char *(*ver)(void) = dlsym(h, "pa_get_library_version");
    void *(*ml_new)(void) = dlsym(h, "pa_mainloop_new");
    void *(*ml_api)(void *) = dlsym(h, "pa_mainloop_get_api");
    int (*ml_iter)(void *, int, int *) = dlsym(h, "pa_mainloop_iterate");
    void *(*ctx_new)(void *, const char *) = dlsym(h, "pa_context_new");
    int (*ctx_connect)(void *, const char *, int, void *) = dlsym(h, "pa_context_connect");
    int (*ctx_state)(void *) = dlsym(h, "pa_context_get_state");
    void *(*get_info)(void *, void (*)(void *, const server_info_t *, void *), void *) = dlsym(h, "pa_context_get_server_info");
    void (*op_unref)(void *) = dlsym(h, "pa_operation_unref");
    void (*disc)(void *) = dlsym(h, "pa_context_disconnect");
    Dl_info di;
    dladdr((void *)ver, &di);
    printf("PA32_LIB version=%s file=%s\n", ver(), di.dli_fname);
    FILE *m = fopen("/proc/self/maps", "r");
    char line[512], last[512] = "";
    while (m && fgets(line, sizeof line, m)) {
        char *p = strchr(line, '/');
        if (p && strstr(p, ".so") && strcmp(p, last)) { printf("PA32_MAP %s", p); strcpy(last, p); }
    }
    if (m) fclose(m);
    void *ml = ml_new(), *c = ctx_new(ml_api(ml), "d4rling-audio-i386-native");
    if (ctx_connect(c, NULL, 0, NULL) < 0) { printf("PA32_CONNECT_FAIL\n"); return 4; }
    int st = 0, rc = 0, asked = 0;
    for (int n = 0; n < 2000 && !done; n++) {
        if (ml_iter(ml, 1, &rc) < 0) break;
        st = ctx_state(c);
        if (st == 4 && !asked) { op_unref(get_info(c, info_cb, NULL)); asked = 1; }
        if (st == 5 || st == 6) break;
    }
    disc(c);
    printf("PA32_RESULT %s state=%d\n", done ? "CONNECTED" : "NOT_CONNECTED", st);
    return done ? 0 : 5;
}
