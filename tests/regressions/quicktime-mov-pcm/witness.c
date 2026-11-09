/* SPDX-License-Identifier: GPL-3.0-or-later
 * QT-MOV-02 / E3-A white-box witness: PCM owned by Movie objects.
 * Reads the private Movie layout (qt_movie_internal.h); exports nothing.
 * Native build: -DD4RL_NATIVE_HOOKS with QuickTime.c malloc/free redirected.
 */
#include <QuickTime/QuickTime.h>
#include "qt_movie_internal.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef __APPLE__
#include <malloc/malloc.h>
#endif

static unsigned checks, failures;
#define CHECK(e) do { ++checks; if (!(e)) { ++failures; printf("FAIL %d: %s\n", __LINE__, #e); } } while (0)

#ifdef D4RL_NATIVE_HOOKS
static long live_blocks, fail_at; /* fail_at = n: the n-th next allocation fails */
void *d4rl_test_malloc(size_t n)
{
    if (fail_at > 0 && --fail_at == 0)
        return NULL;
    void *p = malloc(n);
    if (p) ++live_blocks;
    return p;
}
void d4rl_test_free(void *p) { if (p) --live_blocks; free(p); }
#endif

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

static uint8_t buf[16384], ref[8192];
static uint32_t ref_flags = 1; /* dref entry version/flags: 1 = self reference */
static size_t len, ref_len, stco_field;
static void be32(uint8_t *p, uint32_t x) { p[0]=x>>24; p[1]=x>>16; p[2]=x>>8; p[3]=x; }
static void put8(uint8_t x) { buf[len++] = x; }
static void put16(uint16_t x) { put8(x >> 8); put8((uint8_t)x); }
static void put32(uint32_t x) { be32(buf + len, x); len += 4; }
static void put4(const char *s) { memcpy(buf + len, s, 4); len += 4; }
static void zero(size_t n) { memset(buf + len, 0, n); len += n; }
static size_t begin(const char *t) { size_t at = len; put32(0); put4(t); return at; }
static void end(size_t at) { be32(buf + at, (uint32_t)(len - at)); }

/* MOV with mvhd 600/75 and one sound track: frames of 16-bit PCM. */
static void build(const char *fmt, uint16_t channels, uint32_t hz, uint32_t frames,
                  int moov_first, uint32_t stsc_spc, unsigned salt)
{
    size_t a, t, m, s, st, e, data_off = 0, i;
    ref_len = (size_t)frames * channels * 2;
    for (i = 0; i < ref_len; ++i) ref[i] = (uint8_t)(i * 37u + 11u + (i >> 3) + salt);
    len = 0;
    a = begin("ftyp"); put4("qt  "); put32(0x20050300); put4("qt  "); end(a);
    for (int pass = 0; pass < 2; ++pass) {
        if (pass == (moov_first ? 1 : 0)) {
            a = begin("mdat"); zero(16); data_off = len; memcpy(buf + len, ref, ref_len); len += ref_len; zero(16); end(a);
            continue;
        }
        a = begin("moov");
        { size_t h = begin("mvhd"); put32(0); put32(0); put32(0); put32(600); put32(75); zero(80); end(h); }
        t = begin("trak");
        { size_t k = begin("tkhd"); put32(1); zero(80); end(k); }
        m = begin("mdia");
        { size_t k = begin("mdhd"); put32(0); put32(0); put32(0); put32(hz); put32(frames); put32(0); end(k); }
        { size_t k = begin("hdlr"); put32(0); put4("mhlr"); put4("soun"); zero(12); put8(0); end(k); }
        s = begin("minf");
        { size_t k = begin("smhd"); put32(0); put32(0); end(k); }
        { size_t k = begin("dinf"), d = begin("dref"); put32(0); put32(1);
          { size_t r = begin("alis"); put32(ref_flags); end(r); } end(d); end(k); }
        st = begin("stbl");
        { size_t k = begin("stsd"); put32(0); put32(1);
          e = begin(fmt); zero(6); put16(1); put16(0); put16(0); put32(0);
          put16(channels); put16(16); put16(0); put16(0); put32(hz << 16); end(e); end(k); }
        { size_t k = begin("stts"); put32(0); put32(1); put32(frames); put32(1); end(k); }
        { size_t k = begin("stsc"); put32(0); put32(1); put32(1); put32(stsc_spc); put32(1); end(k); }
        { size_t k = begin("stsz"); put32(0); put32(channels * 2u); put32(frames); end(k); }
        { size_t k = begin("stco"); put32(0); put32(1); stco_field = len; put32(0); end(k); }
        end(st); end(s); end(m); end(t); end(a);
    }
    be32(buf + stco_field, (uint32_t)data_off);
}

static void simple_no_sound(void)
{
    size_t a;
    len = 0;
    a = begin("ftyp"); put4("qt  "); end(a);
    a = begin("moov"); { size_t h = begin("mvhd"); put32(0); put32(0); put32(0); put32(600); put32(1500); zero(80); end(h); } end(a);
}

/* Opens a heap copy of buf (exact size), then poisons and frees that copy. */
static OSErr open_and_drop(Movie *m)
{
    uint8_t *heap = malloc(len);
    PointerDataRefRecord rec;
    PointerDataRefPtr recp = &rec;
    OSErr e;
    memcpy(heap, buf, len);
    rec.data = heap; rec.dataLength = (Size)len;
    e = NewMovieFromDataRef(m, 0, NULL, (Handle)&recp, PointerDataHandlerSubType);
    memset(heap, 0xEE, len);
    free(heap);
    return e;
}

static int pcm_is(Movie m, const uint8_t *want, size_t n, uint32_t fourcc, uint32_t hz, uint16_t ch, uint32_t frames)
{
    const struct MovieType *mt = *m;
    return mt->pcm != NULL && mt->pcm_info.format == fourcc && mt->pcm_info.sample_rate == hz &&
           mt->pcm_info.channels == ch && mt->pcm_info.bits_per_sample == 16 &&
           mt->pcm_info.frame_count == frames && mt->pcm_info.byte_count == n &&
           memcmp(mt->pcm, want, n) == 0;
}

int main(void)
{
    static uint8_t want1[8192], want2[8192];
    size_t n1, n2, before;
    Movie m1 = NULL, m2 = NULL, live[17];
    unsigned i;

    printf("D4RLING-QTMOV02-E3A-ENTRY sizeof(void*)=%u\n", (unsigned)sizeof(void *));
    build("twos", 1, 8000, 100, 0, 100, 0);
    CHECK(open_and_drop(&m1) == -2020 && m1 == NULL);
    CHECK(EnterMovies() == noErr);

    /* PCM kept exactly, independent of the caller's freed buffer. */
    memcpy(want1, ref, ref_len); n1 = ref_len;
    CHECK(open_and_drop(&m1) == noErr && m1 != NULL);
    CHECK(GetMovieTimeScale(m1) == 600 && GetMovieDuration(m1) == 75);
    CHECK(pcm_is(m1, want1, n1, 0x74776F73, 8000, 1, 100));
    memset(buf, 0x55, sizeof(buf)); memset(ref, 0x55, sizeof(ref));
    CHECK(pcm_is(m1, want1, n1, 0x74776F73, 8000, 1, 100));

    /* Second, independent movie: sowt stereo 44.1 kHz, moov first. */
    build("sowt", 2, 44100, 1000, 1, 1000, 3);
    memcpy(want2, ref, ref_len); n2 = ref_len;
    CHECK(open_and_drop(&m2) == noErr);
    CHECK(pcm_is(m2, want2, n2, 0x736F7774, 44100, 2, 1000));
    CHECK((*m1)->pcm != (*m2)->pcm);
    CHECK(pcm_is(m1, want1, n1, 0x74776F73, 8000, 1, 100));
    DisposeMovie(m1);
    CHECK(GetMoviesError() == noErr);
    CHECK(pcm_is(m2, want2, n2, 0x736F7774, 44100, 2, 1000));
    DisposeMovie(m2);

    /* Movies without usable PCM open as before, without samples. */
    simple_no_sound();
    CHECK(open_and_drop(&m1) == noErr && (*m1)->pcm == NULL && GetMovieDuration(m1) == 1500);
    DisposeMovie(m1);
    build("ima4", 1, 8000, 100, 0, 100, 0);
    CHECK(open_and_drop(&m1) == noErr && (*m1)->pcm == NULL && GetMovieDuration(m1) == 75);
    DisposeMovie(m1);
    build("twos", 1, 8000, 100, 0, 99, 0); /* stsc disagrees */
    CHECK(open_and_drop(&m1) == noErr && (*m1)->pcm == NULL && GetMovieTimeScale(m1) == 600);
    DisposeMovie(m1);
    /* External alias, stco inside the local mdat: opens, samples not copied. */
    ref_flags = 0;
    build("twos", 1, 8000, 100, 0, 100, 0);
    m1 = NULL;
    CHECK(open_and_drop(&m1) == noErr && m1 && (*m1)->pcm == NULL);
    CHECK(GetMovieDuration(m1) == 75 && GetMovieTimeScale(m1) == 600 && GetMoviesError() == noErr);
    DisposeMovie(m1);
    ref_flags = 1;
    m1 = NewMovie(0);
    CHECK(m1 && (*m1)->pcm == NULL && GetMovieTimeScale(m1) == 600 && GetMovieDuration(m1) == 0);
    DisposeMovie(m1);

    /* Malformed container: refused, no movie. */
    build("twos", 1, 8000, 100, 0, 100, 0); len -= 1;
    m1 = (Movie)1;
    CHECK(open_and_drop(&m1) == -2002 && m1 == NULL);
    GetMoviesError();

    /* Repeated open/dispose: no growth (1000 x 4000-byte PCM would be 4 MB). */
    build("sowt", 2, 44100, 1000, 1, 1000, 1);
    { Movie w; open_and_drop(&w); DisposeMovie(w); }
    before = heap_in_use();
#ifdef D4RL_NATIVE_HOOKS
    long blocks = live_blocks;
#endif
    for (i = 0; i < 1000; ++i) {
        Movie x = NULL;
        if (open_and_drop(&x) != noErr || !pcm_is(x, ref, ref_len, 0x736F7774, 44100, 2, 1000)) { CHECK(!"cycle"); break; }
        DisposeMovie(x);
    }
    printf("in_use before=%zu after=%zu\n", before, heap_in_use());
    CHECK(heap_in_use() <= before + 4096);
#ifdef D4RL_NATIVE_HOOKS
    CHECK(live_blocks == blocks);
#endif

    /* ExitMovies frees movies (and PCM) that were never disposed. */
    for (i = 0; i < 17; ++i) CHECK(open_and_drop(&live[i]) == noErr);
    ExitMovies();
    CHECK(heap_in_use() <= before + 4096);
#ifdef D4RL_NATIVE_HOOKS
    CHECK(live_blocks == blocks);
#endif
    CHECK(GetMovieDuration(live[0]) == 0 && GetMoviesError() == -2020);
    CHECK(EnterMovies() == noErr);

#ifdef D4RL_NATIVE_HOOKS
    /* Refused allocations: PCM copy (1st), then movie storage (2nd). */
    blocks = live_blocks;
    fail_at = 1; m1 = (Movie)1;
    CHECK(open_and_drop(&m1) == -108 && m1 == NULL && live_blocks == blocks);
    CHECK(GetMoviesError() == -108);
    fail_at = 2; m1 = (Movie)1;
    CHECK(open_and_drop(&m1) == -108 && m1 == NULL && live_blocks == blocks);
    fail_at = 0;
    CHECK(open_and_drop(&m1) == noErr && live_blocks == blocks + 2);
    DisposeMovie(m1);
    CHECK(live_blocks == blocks);
    simple_no_sound(); fail_at = 1; m1 = (Movie)1;
    CHECK(open_and_drop(&m1) == -108 && m1 == NULL && live_blocks == blocks); /* storage only */
    fail_at = 0;
    printf("native allocation hooks: on\n");
#endif
    ExitMovies();

    printf("checks=%u failures=%u\n", checks, failures);
    if (failures == 0)
        printf("D4RLING-QTMOV02-E3A-OK\n");
    return failures > 100 ? 100 : (int)failures;
}
