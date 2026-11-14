/* SPDX-License-Identifier: GPL-3.0-or-later
 * QT-B11E-R2: GetMediaSample witness on the six B11E MOV files.
 *
 * Built natively (Linux, with the real QuickTime.c, qt_mov_*.c and the real
 * CarbonCore MacMemory.cpp) and as a Mach-O i386 executable linked against the
 * QuickTime.framework produced by the CMake/Ninja build (CoreServices for the
 * Memory Manager). Only public QuickTime and Memory Manager calls are used: the
 * PCM reaches the oracle exclusively through GetMediaSample's handle.
 *
 * Usage: b11e-r2-getmediasample MOV_DIR OUT_DIR [CYCLES]
 *   MOV_DIR holds mov-0.mov .. mov-5.mov (written by the R1 witness);
 *   OUT_DIR receives gms-N.bin (whole track) and gms-chunked-N.bin.
 * Exit status: number of failed checks (cap 100).
 */
#include <QuickTime/QuickTime.h>
#include <CarbonCore/MacMemory.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef __APPLE__
#include <dlfcn.h>
#include <malloc/malloc.h>
#include <mach-o/dyld.h>
#endif

enum {
    kParamErr = -50, kUnimpErr = -4, kNilHandleErr = -109, kMemWZErr = -111, kMemLockedErr = -117,
    kInvalidMedia = -2008, kUninitialized = -2020, kMaxSizeToGrowTooSmall = -2027, kTimeNotInMedia = -2032
};

static const char *const R0_SHA256[6] = {
    "6d9c54dee5660c46886f32d80e57e9dd0ffa57ee0cd2a762b036d9c8e0c3a33a",
    "c6e3eb0c609db9a2ba21081313aeade0e232c7d5bda0856aeb3ce0e9f0eb98a0",
    "757822aae431f8297c566874401a9d6fe2051e8aea48250c706102ada66b46b6",
    "cd2a71d1d9498dd51998c76bb6f513a074eefbb19fc5598c4ab3b2e4c7886fdd",
    "f63ecff3fad32efde29bacdeef6b0ad65187ebc143455fa372edd314cf94644f",
    "c27c294c4100eb436c07d5da79fed4c7f1a214e14803512431f25ea94cec1f18",
};

static unsigned checks, failures;
static void check(int ok, const char *sec, const char *name, int v, const char *detail)
{
    ++checks;
    if (!ok)
        ++failures;
    printf("R2 %s %s v%d %s %s\n", sec, name, v, ok ? "PASS" : "FAIL", detail ? detail : "");
}
#define CHECKF(ok, sec, name, v, ...) do { char d_[256]; snprintf(d_, sizeof d_, __VA_ARGS__); check((ok), sec, name, v, d_); } while (0)

/* ---------------------------------------------------------------- sha256 */
typedef struct { uint32_t h[8]; uint64_t len; uint8_t buf[64]; size_t n; } sha256_t;
static const uint32_t K256[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
#define ROR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))
static void sha_block(sha256_t *s, const uint8_t *p)
{
    uint32_t w[64], a, b, c, d, e, f, g, h;
    int i;
    for (i = 0; i < 16; ++i)
        w[i] = (uint32_t)p[4 * i] << 24 | (uint32_t)p[4 * i + 1] << 16 | (uint32_t)p[4 * i + 2] << 8 | p[4 * i + 3];
    for (i = 16; i < 64; ++i) {
        uint32_t s0 = ROR(w[i - 15], 7) ^ ROR(w[i - 15], 18) ^ (w[i - 15] >> 3);
        uint32_t s1 = ROR(w[i - 2], 17) ^ ROR(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    a = s->h[0]; b = s->h[1]; c = s->h[2]; d = s->h[3]; e = s->h[4]; f = s->h[5]; g = s->h[6]; h = s->h[7];
    for (i = 0; i < 64; ++i) {
        uint32_t t1 = h + (ROR(e, 6) ^ ROR(e, 11) ^ ROR(e, 25)) + ((e & f) ^ (~e & g)) + K256[i] + w[i];
        uint32_t t2 = (ROR(a, 2) ^ ROR(a, 13) ^ ROR(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
        h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    s->h[0] += a; s->h[1] += b; s->h[2] += c; s->h[3] += d; s->h[4] += e; s->h[5] += f; s->h[6] += g; s->h[7] += h;
}
static void sha_init(sha256_t *s)
{
    static const uint32_t iv[8] = {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    memcpy(s->h, iv, sizeof iv);
    s->len = 0;
    s->n = 0;
}
static void sha_update(sha256_t *s, const void *data, size_t len)
{
    const uint8_t *p = data;
    s->len += len;
    while (len) {
        size_t k = 64 - s->n < len ? 64 - s->n : len;
        memcpy(s->buf + s->n, p, k);
        s->n += k; p += k; len -= k;
        if (s->n == 64) { sha_block(s, s->buf); s->n = 0; }
    }
}
static void sha_hex(sha256_t *s, char out[65])
{
    uint64_t bits = s->len * 8;
    uint8_t pad = 0x80, z = 0, l[8];
    int i;
    sha_update(s, &pad, 1);
    while (s->n != 56)
        sha_update(s, &z, 1);
    for (i = 0; i < 8; ++i)
        l[i] = (uint8_t)(bits >> (56 - 8 * i));
    sha_update(s, l, 8);
    for (i = 0; i < 8; ++i)
        snprintf(out + 8 * i, 9, "%08x", s->h[i]);
}
static void sha_mem(const void *p, size_t n, char out[65])
{
    sha256_t s;
    sha_init(&s);
    sha_update(&s, p, n);
    sha_hex(&s, out);
}

/* ---------------------------------------------------------------- files */
static uint8_t *read_file(const char *dir, const char *name, size_t *n)
{
    char path[4096];
    FILE *f;
    long size;
    uint8_t *p;
    snprintf(path, sizeof path, "%s/%s", dir, name);
    if (!(f = fopen(path, "rb")))
        return NULL;
    if (fseek(f, 0, SEEK_END) || (size = ftell(f)) <= 0 || fseek(f, 0, SEEK_SET)) { fclose(f); return NULL; }
    p = malloc((size_t)size);
    if (p && fread(p, 1, (size_t)size, f) != (size_t)size) { free(p); p = NULL; }
    fclose(f);
    *n = (size_t)size;
    return p;
}
static int write_file(const char *dir, const char *name, const void *p, size_t n)
{
    char path[4096];
    FILE *f;
    snprintf(path, sizeof path, "%s/%s", dir, name);
    if (!(f = fopen(path, "wb")))
        return 0;
    if (fwrite(p, 1, n, f) != n) { fclose(f); return 0; }
    return fclose(f) == 0;
}

static size_t heap_in_use(void)
{
#ifdef __APPLE__
    malloc_statistics_t st;
    malloc_zone_statistics(NULL, &st);
    return st.size_in_use;
#else
    return 0;
#endif
}

/* ---------------------------------------------------------------- movie */
struct opened { Movie movie; Track track; Media media; };

/* dataRef: a real Memory Manager handle holding the pointer record. */
static OSErr open_movie(uint8_t *data, size_t n, struct opened *o)
{
    PointerDataRefRecord rec;
    Handle ref = NewHandle((long)sizeof rec);
    OSErr e;
    memset(o, 0, sizeof *o);
    if (!ref)
        return MemError();
    rec.data = data;
    rec.dataLength = (Size)n;
    memcpy(*ref, &rec, sizeof rec);
    e = NewMovieFromDataRef(&o->movie, 0, NULL, ref, PointerDataHandlerSubType);
    DisposeHandle(ref);
    if (e != noErr)
        return e;
    o->track = GetMovieIndTrack(o->movie, 1);
    o->media = o->track ? GetTrackMedia(o->track) : NULL;
    return o->media ? noErr : GetMoviesError();
}

struct outs { SInt32 size, desc_index, count; TimeValue time, duration; SInt16 flags; };
static void poison(struct outs *x) { memset(x, 0xA5, sizeof *x); }
static int poisoned(const struct outs *x)
{
    const uint8_t *p = (const uint8_t *)x;
    size_t i;
    for (i = 0; i < sizeof *x; ++i)
        if (p[i] != 0xA5)
            return 0;
    return 1;
}
static OSErr gms(Media m, Handle h, SInt32 max_grow, TimeValue t, SInt32 max_n, struct outs *x)
{
    return GetMediaSample(m, h, max_grow, &x->size, t, &x->time, &x->duration, NULL,
                          &x->desc_index, max_n, &x->count, &x->flags);
}

/* Handle state used to prove error paths leave dataOut unchanged. */
static int handle_is(Handle h, Size want_size, uint8_t fill)
{
    Size s = GetHandleSize(h);
    Size i;
    if (MemError() != noErr || s != want_size)
        return 0;
    for (i = 0; i < s; ++i)
        if ((uint8_t)(*h)[i] != fill)
            return 0;
    return 1;
}

static void per_vector(int v, uint8_t *file, size_t n, const char *out)
{
    struct opened o;
    struct outs x;
    Handle h, e, big, tiny;
    char hex[65];
    OSErr st;
    uint8_t whole[200], chunked[200];
    size_t got;
    int calls, last;
    TimeValue t;

    sha_mem(file, n, hex);
    printf("R2_MOV v%d bytes=%zu sha256=%s\n", v, n, hex);
    st = open_movie(file, n, &o);
    CHECKF(st == noErr && o.media, "T", "open_track_media", v, "status=%d", st);
    if (st != noErr || !o.media)
        return;
    CHECKF(GetMovieTrackCount(o.movie) == 1 && GetMediaTimeScale(o.media) == 8000 &&
           GetMediaSampleCount(o.media) == 100 && GetMovieTimeScale(o.movie) == 600 &&
           GetMovieDuration(o.movie) == 75, "T", "scales_counts", v,
           "tracks=%ld media_scale=%ld samples=%ld movie_scale=%ld duration=%ld",
           (long)GetMovieTrackCount(o.movie), (long)GetMediaTimeScale(o.media),
           (long)GetMediaSampleCount(o.media), (long)GetMovieTimeScale(o.movie), (long)GetMovieDuration(o.movie));

    /* The movie owns its samples: scribble and free the caller's MOV first. */
    memset(file, 0x5A, n);
    free(file);

    h = NewHandle(1);
    poison(&x);
    st = gms(o.media, h, 0, 0, 0, &x);
    if (st == noErr && x.size == 200)
        memcpy(whole, *h, 200);
    sha_mem(st == noErr ? (const void *)*h : (const void *)"", st == noErr ? (size_t)x.size : 0, hex);
    CHECKF(st == noErr && x.size == 200 && x.count == 100 && x.time == 0 && x.duration == 1 &&
           x.desc_index == 1 && x.flags == 0 && GetHandleSize(h) == 200 && GetMoviesError() == noErr,
           "S", "whole_track", v, "status=%d size=%ld count=%ld time=%ld dur=%ld desc=%ld flags=%d handle=%ld",
           st, (long)x.size, (long)x.count, (long)x.time, (long)x.duration, (long)x.desc_index, x.flags,
           (long)GetHandleSize(h));
    CHECKF(strcmp(hex, R0_SHA256[v]) == 0, "S", "whole_track_sha256_equals_r0", v, "sha256=%s", hex);
    if (st == noErr) {
        char name[64];
        snprintf(name, sizeof name, "gms-%d.bin", v);
        CHECKF(write_file(out, name, whole, 200), "S", "write_gms", v, "%s", name);
    }

    /* Chunks of 7 samples: 14 full calls + a final partial block of 2. */
    got = 0; calls = 0; last = -1;
    for (t = 0; t < 100 && calls < 200; ++calls) {
        poison(&x);
        st = gms(o.media, h, 0, t, 7, &x);
        if (st != noErr || x.count < 1 || x.count > 7 || x.size != 2 * x.count || x.time != t ||
            GetHandleSize(h) != x.size || got + (size_t)x.size > sizeof chunked)
            break;
        memcpy(chunked + got, *h, (size_t)x.size);
        got += (size_t)x.size;
        last = x.count;
        t += x.count;
    }
    sha_mem(chunked, got, hex);
    CHECKF(t == 100 && got == 200 && calls == 15 && last == 2 && strcmp(hex, R0_SHA256[v]) == 0,
           "C", "chunks_of_7_partial_last", v, "calls=%d bytes=%zu last=%d status=%d sha256=%s", calls, got, last, st, hex);
    if (got == 200) {
        char name[64];
        snprintf(name, sizeof name, "gms-chunked-%d.bin", v);
        write_file(out, name, chunked, 200);
    }
    /* maxSizeToGrow 30 bytes = 15 frames: 6 calls of 15, last of 10. */
    got = 0; calls = 0; last = -1;
    for (t = 0; t < 100 && calls < 200; ++calls) {
        st = gms(o.media, h, 30, t, 0, &x);
        if (st != noErr || x.count < 1 || x.size > 30 || x.time != t || got + (size_t)x.size > sizeof chunked)
            break;
        memcpy(chunked + got, *h, (size_t)x.size);
        got += (size_t)x.size;
        last = x.count;
        t += x.count;
    }
    sha_mem(chunked, got, hex);
    CHECKF(t == 100 && calls == 7 && last == 10 && strcmp(hex, R0_SHA256[v]) == 0,
           "C", "max_size_to_grow_30", v, "calls=%d last=%d sha256=%s", calls, last, hex);

    /* Last sample, end of media, negative time: handle and outputs intact. */
    st = gms(o.media, h, 0, 99, 0, &x);
    CHECKF(st == noErr && x.count == 1 && x.size == 2 && memcmp(*h, whole + 198, 2) == 0,
           "E", "last_sample", v, "status=%d count=%ld", st, (long)x.count);
    memset(*h, 0xEE, 2);
    poison(&x);
    st = gms(o.media, h, 0, 100, 0, &x);
    CHECKF(st == kTimeNotInMedia && poisoned(&x) && handle_is(h, 2, 0xEE) && GetMoviesError() == kTimeNotInMedia,
           "E", "time_at_end_timeNotInMedia", v, "status=%d", st);
    st = gms(o.media, h, 0, -1, 0, &x);
    CHECKF(st == kTimeNotInMedia && poisoned(&x) && handle_is(h, 2, 0xEE), "E", "negative_time", v, "status=%d", st);
    st = gms(o.media, h, 1, 0, 0, &x);
    CHECKF(st == kMaxSizeToGrowTooSmall && poisoned(&x) && handle_is(h, 2, 0xEE), "E", "max_size_1_too_small", v, "status=%d", st);
    st = gms(o.media, NULL, 0, 0, 0, &x);
    CHECKF(st == kParamErr && poisoned(&x), "E", "null_handle_paramErr", v, "status=%d", st);
    st = gms(o.media, h, -1, 0, 0, &x);
    CHECKF(st == kParamErr && poisoned(&x) && handle_is(h, 2, 0xEE), "E", "negative_max_size", v, "status=%d", st);
    st = gms(o.media, h, 0, 0, -1, &x);
    CHECKF(st == kParamErr && poisoned(&x) && handle_is(h, 2, 0xEE), "E", "negative_max_samples", v, "status=%d", st);
    {
        SampleDescriptionHandle desc = (SampleDescriptionHandle)NewHandle(4);
        st = GetMediaSample(o.media, h, 0, &x.size, 0, &x.time, &x.duration, desc, &x.desc_index, 0, &x.count, &x.flags);
        CHECKF(st == kUnimpErr && poisoned(&x) && handle_is(h, 2, 0xEE), "E", "sample_description_unimp", v, "status=%d", st);
        DisposeHandle((Handle)desc);
    }
    /* Handles: empty (reallocated), larger (resized to the data), locked
     * (Memory Manager refusal passed through), foreign (never written). */
    e = NewEmptyHandle();
    st = gms(o.media, e, 0, 0, 0, &x);
    CHECKF(st == noErr && *e && GetHandleSize(e) == 200 && memcmp(*e, whole, 200) == 0, "H", "empty_handle_reallocated", v,
           "status=%d size=%ld", st, (long)GetHandleSize(e));
    big = NewHandle(4096);
    st = gms(o.media, big, 0, 10, 5, &x);
    CHECKF(st == noErr && GetHandleSize(big) == 10 && memcmp(*big, whole + 20, 10) == 0 && x.time == 10,
           "H", "large_handle_resized_exactly", v, "status=%d size=%ld", st, (long)GetHandleSize(big));
    tiny = NewHandle(1);
    (*tiny)[0] = (char)0xEE;
    HLock(tiny);
    poison(&x);
    st = gms(o.media, tiny, 0, 0, 0, &x);
    CHECKF(st == kMemLockedErr && poisoned(&x) && handle_is(tiny, 1, 0xEE) && GetMoviesError() == kMemLockedErr,
           "H", "locked_handle_growth_refused", v, "status=%d", st);
    HUnlock(tiny);
    {
        char *block = malloc(64), **foreign = malloc(sizeof(char *));
        memset(block, 0xEE, 64);
        *foreign = block;
        poison(&x);
        st = gms(o.media, (Handle)foreign, 0, 0, 0, &x);
        CHECKF(st == kMemWZErr && poisoned(&x) && *foreign == block && block[0] == (char)0xEE && block[63] == (char)0xEE,
               "H", "foreign_handle_memWZErr", v, "status=%d", st);
        free(block);
        free(foreign);
    }
    st = GetMediaSample(o.media, h, 0, NULL, 50, NULL, NULL, NULL, NULL, 3, NULL, NULL);
    CHECKF(st == noErr && GetHandleSize(h) == 6 && memcmp(*h, whole + 100, 6) == 0, "H", "null_outputs_allowed", v, "status=%d", st);
    DisposeHandle(e);
    DisposeHandle(big);
    DisposeHandle(tiny);

    /* A media handle dies with its movie. */
    DisposeMovie(o.movie);
    poison(&x);
    st = gms(o.media, h, 0, 0, 0, &x);
    CHECKF(st == kInvalidMedia && poisoned(&x) && GetHandleSize(h) == 6 && memcmp(*h, whole + 100, 6) == 0,
           "E", "disposed_movie_invalidMedia", v, "status=%d", st);
    DisposeHandle(h);
}

/* Open/extract/close cycles over the six files; heap stable on Darwin. */
static void cycles(uint8_t *const files[6], const size_t sizes[6], int n)
{
    size_t warm = 0, end;
    int i, v, bad = 0;
    for (i = 0; i < n; ++i) {
        for (v = 0; v < 6; ++v) {
            struct opened o;
            struct outs x;
            Handle h = NewHandle(0);
            char hex[65];
            OSErr st = open_movie(files[v], sizes[v], &o);
            if (st == noErr)
                st = gms(o.media, h, 0, 0, 0, &x);
            sha_mem(*h, (size_t)GetHandleSize(h), hex);
            if (st != noErr || strcmp(hex, R0_SHA256[v]) != 0)
                ++bad;
            if (o.movie)
                DisposeMovie(o.movie);
            DisposeHandle(h);
        }
        if (i == 9)
            warm = heap_in_use();
    }
    end = heap_in_use();
    CHECKF(bad == 0 && (n < 10 || end == warm), "L", "open_extract_close_cycles", n,
           "cycles=%d calls=%d bad=%d heap_after_10=%zu heap_end=%zu", n, n * 6, bad, warm, end);
}

static void loaded_images(void)
{
#ifdef __APPLE__
    Dl_info qi, mi;
    uint32_t i, count = _dyld_image_count();
    int ok_q = dladdr((const void *)GetMediaSample, &qi), ok_m = dladdr((const void *)GetHandleSize, &mi);
    printf("R2_IMAGE GetMediaSample %s\n", ok_q ? qi.dli_fname : "?");
    printf("R2_IMAGE GetHandleSize %s\n", ok_m ? mi.dli_fname : "?");
    for (i = 0; i < count; ++i)
        printf("R2_LOADED %s\n", _dyld_get_image_name(i));
    CHECKF(ok_q && strstr(qi.dli_fname, "QuickTime.framework/") != NULL, "I", "getmediasample_from_quicktime_framework", 0,
           "%s", ok_q ? qi.dli_fname : "?");
    CHECKF(ok_m && strstr(mi.dli_fname, "CarbonCore.framework/") != NULL, "I", "memory_manager_from_carboncore", 0,
           "%s", ok_m ? mi.dli_fname : "?");
#endif
}

int main(int argc, char **argv)
{
    uint8_t *files[6] = {0};
    size_t sizes[6] = {0};
    int v, n = argc > 3 ? atoi(argv[3]) : 100;
    struct outs x;
    OSErr st;

    if (argc < 3) {
        fprintf(stderr, "usage: %s MOV_DIR OUT_DIR [CYCLES]\n", argv[0]);
        return 2;
    }
    printf("R2_ABI pointer_bits=%zu SInt32=%zu TimeValue=%zu Size=%zu\n", sizeof(void *) * 8,
           sizeof(SInt32) * 8, sizeof(TimeValue) * 8, sizeof(Size) * 8);
    loaded_images();
    poison(&x);
    st = gms((Media)&x, NULL, 0, 0, 0, &x);
    CHECKF(st == kUninitialized && poisoned(&x), "E", "before_enter_movies", 0, "status=%d", st);
    CHECKF(EnterMovies() == noErr, "T", "enter_movies", 0, "%s", "");
    st = gms((Media)&x, NULL, 0, 0, 0, &x);
    CHECKF(st == kInvalidMedia && poisoned(&x), "E", "unknown_media", 0, "status=%d", st);
    for (v = 0; v < 6; ++v) {
        char name[32];
        uint8_t *p;
        snprintf(name, sizeof name, "mov-%d.mov", v);
        p = read_file(argv[1], name, &sizes[v]);
        CHECKF(p != NULL, "T", "read_mov", v, "%s bytes=%zu", name, sizes[v]);
        if (!p)
            continue;
        files[v] = malloc(sizes[v]);
        memcpy(files[v], p, sizes[v]);
        per_vector(v, p, sizes[v], argv[2]); /* frees p */
    }
    if (files[0] && files[1] && files[2] && files[3] && files[4] && files[5])
        cycles(files, sizes, n);
    ExitMovies();
    st = gms((Media)&x, NULL, 0, 0, 0, &x);
    CHECKF(st == kUninitialized, "E", "after_exit_movies", 0, "status=%d", st);
    for (v = 0; v < 6; ++v)
        free(files[v]);
    printf("R2_SUMMARY checks=%u failures=%u\n", checks, failures);
    if (failures == 0)
        printf("B11E_R2_WITNESS_OK\n");
    return failures > 100 ? 100 : (int)failures;
}
