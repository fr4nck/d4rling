/* SPDX-License-Identifier: GPL-3.0-or-later
 * QT-MOV-02 / E3-B1 witness: GetMovieTrackCount, GetMovieIndTrack,
 * GetTrackMedia, GetMediaSampleCount, GetMediaTimeScale.
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
static long live_blocks, fail_at;
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

static uint8_t buf[32768], pcm_ref[8192];
static size_t len, pcm_len;
static void be32(uint8_t *p, uint32_t x) { p[0]=x>>24; p[1]=x>>16; p[2]=x>>8; p[3]=x; }
static void put8(uint8_t x) { buf[len++] = x; }
static void put16(uint16_t x) { put8(x >> 8); put8((uint8_t)x); }
static void put32(uint32_t x) { be32(buf + len, x); len += 4; }
static void put4(const char *s) { memcpy(buf + len, s, 4); len += 4; }
static void zero(size_t n) { memset(buf + len, 0, n); len += n; }
static size_t begin(const char *t) { size_t at = len; put32(0); put4(t); return at; }
static void end(size_t at) { be32(buf + at, (uint32_t)(len - at)); }

struct trk { char kind; uint32_t scale, samples; uint16_t channels; int stsz; };  /* kind: s=sound, v=video, n=no media */
/* stsz variants: 0 constant size, no table (default); 1 variable, N entries; 2 variable, N-1 entries;
 * 3 variable, N+1 entries; 4 constant size with a table; 5 version 1; 6 flags 1; 7 huge count, short table */
static size_t stco_fields[4];

static void trak(const struct trk *k, int idx)
{
    size_t t = begin("trak"), m, s, st, e, a;
    a = begin("tkhd"); put32(1); zero(80); end(a);
    if (k->kind == 'n') { end(t); return; }
    m = begin("mdia");
    a = begin("mdhd"); put32(0); put32(0); put32(0); put32(k->scale); put32(k->samples); put32(0); end(a);
    a = begin("hdlr"); put32(0); put4("mhlr"); put4(k->kind == 's' ? "soun" : "vide"); zero(12); put8(0); end(a);
    s = begin("minf");
    a = begin(k->kind == 's' ? "smhd" : "vmhd"); put32(0); put32(0); end(a);
    a = begin("dinf"); e = begin("dref"); put32(0); put32(1); { size_t r = begin("alis"); put32(1); end(r); } end(e); end(a);
    st = begin("stbl");
    a = begin("stsd"); put32(0); put32(1);
    if (k->kind == 's') {
        e = begin("twos"); zero(6); put16(1); put16(0); put16(0); put32(0);
        put16(k->channels); put16(16); put16(0); put16(0); put32(k->scale << 16); end(e);
    } else {
        e = begin("jpeg"); zero(6); put16(1); zero(70); end(e);
    }
    end(a);
    a = begin("stts"); put32(0); put32(1); put32(k->samples); put32(1); end(a);
    a = begin("stsc"); put32(0); put32(1); put32(1); put32(k->samples); put32(1); end(a);
    a = begin("stsz");
    {
        uint32_t size = k->kind == 's' ? k->channels * 2u : 100u, count = k->samples, entries = 0, q;
        uint32_t vf = k->stsz == 5 ? 0x01000000u : k->stsz == 6 ? 1u : 0u;
        if (k->stsz >= 1 && k->stsz <= 3) { size = 0; entries = k->samples + (k->stsz == 2 ? -1 : k->stsz == 3 ? 1 : 0); }
        if (k->stsz == 4) entries = k->samples;
        if (k->stsz == 7) { size = 0; count = 0x40000001u; entries = 2; }
        put32(vf); put32(size); put32(count);
        for (q = 0; q < entries; ++q) put32(90u + q);
    }
    end(a);
    a = begin("stco"); put32(0); put32(1); stco_fields[idx] = len; put32(0); end(a);
    end(st); end(s); end(m); end(t);
}

/* ftyp, moov{mvhd 600/75, traks...}, mdat holding the sound PCM. */
static void build(const struct trk *ks, int n)
{
    size_t a, i, data_off;
    int j, sound = -1;
    len = 0;
    a = begin("ftyp"); put4("qt  "); end(a);
    a = begin("moov");
    { size_t h = begin("mvhd"); put32(0); put32(0); put32(0); put32(600); put32(75); zero(80); end(h); }
    for (j = 0; j < n; ++j) { trak(&ks[j], j); if (ks[j].kind == 's') sound = j; }
    end(a);
    pcm_len = 0;
    a = begin("mdat"); zero(16); data_off = len;
    if (sound >= 0) {
        pcm_len = (size_t)ks[sound].samples * ks[sound].channels * 2;
        for (i = 0; i < pcm_len; ++i) pcm_ref[i] = (uint8_t)(i * 29u + 5u + (i >> 4));
        memcpy(buf + len, pcm_ref, pcm_len); len += pcm_len;
    }
    zero(64); end(a);
    for (j = 0; j < n; ++j) if (ks[j].kind != 'n') be32(buf + stco_fields[j], (uint32_t)(ks[j].kind == 's' ? data_off : data_off + pcm_len));
}

static OSErr open_buf(Movie *m)
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

static int media_is(Track t, TimeScale scale, SInt32 samples)
{
    Media md = GetTrackMedia(t);
    return md != NULL && GetMoviesError() == noErr && GetMediaTimeScale(md) == scale &&
           GetMediaSampleCount(md) == samples && GetMoviesError() == noErr;
}

int main(void)
{
    static const struct trk mono[] = { { 's', 8000, 100, 1 } };
    static const struct trk stereo[] = { { 's', 44100, 1000, 2 } };
    static const struct trk mixed[] = { { 'v', 30000, 10, 0 }, { 's', 44100, 1000, 2 } };
    static const struct trk nomedia[] = { { 'n', 0, 0, 0 }, { 's', 8000, 100, 1 } };
    Movie m, a, b, live[9];
    Track t1, t2, ta, tb;
    Media ma, mb;
    size_t before;
    unsigned i;
    SInt32 bad[] = { 0, -1, 2, INT32_MAX, INT32_MIN };

    printf("D4RLING-QTMOV02-E3B1-ENTRY sizeof(Track)=%u sizeof(SInt32)=%u\n", (unsigned)sizeof(Track), (unsigned)sizeof(SInt32));
    CHECK(GetMovieTrackCount(NULL) == 0 && GetMoviesError() == -2020);
    CHECK(GetTrackMedia((Track)0x10) == NULL && GetMoviesError() == -2020);
    CHECK(EnterMovies() == noErr);

    /* Empty movie: zero tracks. */
    m = NewMovie(0);
    CHECK(GetMovieTrackCount(m) == 0 && GetMoviesError() == noErr);
    CHECK(GetMovieIndTrack(m, 1) == NULL && GetMoviesError() == -2028);
    DisposeMovie(m);

    /* Mono PCM: one sound track, media 8000 Hz, 100 samples; movie stays 600. */
    build(mono, 1);
    CHECK(open_buf(&m) == noErr);
    CHECK(GetMovieTrackCount(m) == 1 && GetMoviesError() == noErr);
    t1 = GetMovieIndTrack(m, 1);
    CHECK(t1 != NULL && GetMoviesError() == noErr);
    CHECK(media_is(t1, 8000, 100));
    CHECK(GetMovieTimeScale(m) == 600);
    CHECK(GetMovieIndTrack(m, 1) == t1 && GetTrackMedia(t1) == GetTrackMedia(t1)); /* stable */
    for (i = 0; i < sizeof(bad) / sizeof(bad[0]); ++i)
        CHECK(GetMovieIndTrack(m, bad[i]) == NULL && GetMoviesError() == -2028);
    CHECK((*m)->pcm && (*m)->pcm_info.frame_count == 100 && memcmp((*m)->pcm, pcm_ref, pcm_len) == 0);
    CHECK(GetMediaSampleCount(GetTrackMedia(t1)) == (SInt32)(*m)->pcm_info.frame_count);
    DisposeMovie(m);
    /* Invalidated after DisposeMovie: no dereference, explicit errors. */
    CHECK(GetTrackMedia(t1) == NULL && GetMoviesError() == -2009);

    /* Stereo PCM. */
    build(stereo, 1);
    CHECK(open_buf(&m) == noErr && GetMovieTrackCount(m) == 1);
    CHECK(media_is(GetMovieIndTrack(m, 1), 44100, 1000));
    CHECK((*m)->pcm && memcmp((*m)->pcm, pcm_ref, pcm_len) == 0);
    DisposeMovie(m);

    /* Video then sound: order kept, distinct media. */
    build(mixed, 2);
    CHECK(open_buf(&m) == noErr);
    CHECK(GetMovieTrackCount(m) == 2);
    t1 = GetMovieIndTrack(m, 1); t2 = GetMovieIndTrack(m, 2);
    CHECK(t1 && t2 && t1 != t2);
    CHECK(media_is(t1, 30000, 10));
    CHECK(media_is(t2, 44100, 1000));
    CHECK(GetTrackMedia(t1) != GetTrackMedia(t2));
    CHECK(GetMovieIndTrack(m, 3) == NULL && GetMoviesError() == -2028);
    CHECK((*m)->pcm && (*m)->pcm_info.frame_count == 1000 && memcmp((*m)->pcm, pcm_ref, pcm_len) == 0);
    DisposeMovie(m);

    /* Track without media, then sound. */
    build(nomedia, 2);
    CHECK(open_buf(&m) == noErr && GetMovieTrackCount(m) == 2);
    t1 = GetMovieIndTrack(m, 1);
    CHECK(t1 != NULL && GetTrackMedia(t1) == NULL && GetMoviesError() == -2008);
    CHECK(media_is(GetMovieIndTrack(m, 2), 8000, 100));
    DisposeMovie(m);

    /* Movie with only mvhd: zero tracks. Unreadable track table: explicit error. */
    len = 0;
    { size_t x = begin("moov"), h = begin("mvhd"); put32(0); put32(0); put32(0); put32(600); put32(1500); zero(80); end(h); end(x); }
    CHECK(open_buf(&m) == noErr && GetMovieTrackCount(m) == 0 && GetMoviesError() == noErr);
    DisposeMovie(m);
    len = 0;
    { size_t x = begin("moov"), h = begin("mvhd"); put32(0); put32(0); put32(0); put32(600); put32(1500); zero(80); end(h); put32(4); put4("junk"); end(x); }
    CHECK(open_buf(&m) == noErr && GetMovieDuration(m) == 1500);
    CHECK(GetMovieTrackCount(m) == 0 && GetMoviesError() == -2002);
    CHECK(GetMovieIndTrack(m, 1) == NULL && GetMoviesError() == -2002);
    DisposeMovie(m);

    /* stsz validation (R1): malformed tables make the media unavailable,
     * the track stays listed and other tracks are unaffected. */
    {
        struct { int mode; int media_ok; } cases[] = { {0,1}, {1,1}, {2,0}, {3,0}, {4,0}, {5,0}, {6,0}, {7,0} };
        for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
            struct trk ks[2] = { { 'v', 30000, 10, 0, cases[i].mode }, { 's', 44100, 1000, 2, 0 } };
            Track tv, ts;
            build(ks, 2);
            CHECK(open_buf(&m) == noErr && GetMovieTrackCount(m) == 2 && GetMoviesError() == noErr);
            tv = GetMovieIndTrack(m, 1); ts = GetMovieIndTrack(m, 2);
            CHECK(tv != NULL && ts != NULL);
            if (cases[i].media_ok) {
                CHECK(media_is(tv, 30000, 10));
            } else {
                ++checks; if (GetTrackMedia(tv) != NULL || GetMoviesError() != -2008) { ++failures; printf("FAIL %d: stsz mode %d accepted\n", __LINE__, cases[i].mode); }
            }
            CHECK(media_is(ts, 44100, 1000));
            CHECK((*m)->pcm && memcmp((*m)->pcm, pcm_ref, pcm_len) == 0);
            DisposeMovie(m);
        }
        /* Variable-size sound table: media valid with N samples (PCM copy not supported). */
        {
            struct trk ks[1] = { { 's', 8000, 100, 1, 1 } };
            build(ks, 1);
            CHECK(open_buf(&m) == noErr && media_is(GetMovieIndTrack(m, 1), 8000, 100) && (*m)->pcm == NULL);
            DisposeMovie(m);
        }
    }

    /* Two independent movies; references of one never resolve in the other. */
    build(mixed, 2); CHECK(open_buf(&a) == noErr);
    build(mono, 1); CHECK(open_buf(&b) == noErr);
    ta = GetMovieIndTrack(a, 2); tb = GetMovieIndTrack(b, 1);
    ma = GetTrackMedia(ta); mb = GetTrackMedia(tb);
    CHECK(ta != tb && ma != mb && GetMediaTimeScale(ma) == 44100 && GetMediaTimeScale(mb) == 8000);
    CHECK(GetTrackMedia((Track)ma) == NULL && GetMoviesError() == -2009); /* media is not a track */
    CHECK(GetMediaTimeScale((Media)ta) == 0 && GetMoviesError() == -2008); /* track is not a media */
    CHECK(GetMediaTimeScale((Media)0x10) == 0 && GetMoviesError() == -2008);
    DisposeMovie(a);
    CHECK(GetTrackMedia(ta) == NULL && GetMoviesError() == -2009);
    CHECK(GetMediaSampleCount(ma) == 0 && GetMoviesError() == -2008);
    CHECK(GetMediaSampleCount(mb) == 100 && GetMoviesError() == noErr);
    DisposeMovie(b);

    /* Cycles: no growth. */
    build(mixed, 2);
    { Movie w; open_buf(&w); DisposeMovie(w); }
    before = heap_in_use();
#ifdef D4RL_NATIVE_HOOKS
    long blocks = live_blocks;
#endif
    for (i = 0; i < 1000; ++i) {
        Movie x = NULL;
        if (open_buf(&x) != noErr || !media_is(GetMovieIndTrack(x, 2), 44100, 1000)) { CHECK(!"cycle"); break; }
        DisposeMovie(x);
    }
    printf("in_use before=%zu after=%zu\n", before, heap_in_use());
    CHECK(heap_in_use() <= before + 4096);
#ifdef D4RL_NATIVE_HOOKS
    CHECK(live_blocks == blocks);
#endif

    /* ExitMovies frees live movies and invalidates their references. */
    for (i = 0; i < 9; ++i) CHECK(open_buf(&live[i]) == noErr);
    t1 = GetMovieIndTrack(live[0], 1); ma = GetTrackMedia(t1);
    ExitMovies();
    CHECK(heap_in_use() <= before + 4096);
#ifdef D4RL_NATIVE_HOOKS
    CHECK(live_blocks == blocks);
#endif
    CHECK(GetTrackMedia(t1) == NULL && GetMoviesError() == -2020);
    CHECK(EnterMovies() == noErr);
    CHECK(GetTrackMedia(t1) == NULL && GetMoviesError() == -2009);
    CHECK(GetMediaTimeScale(ma) == 0 && GetMoviesError() == -2008);

#ifdef D4RL_NATIVE_HOOKS
    /* Allocation order: PCM, track infos, track table, movie storage. */
    blocks = live_blocks;
    for (i = 1; i <= 4; ++i) {
        fail_at = (long)i; m = (Movie)1;
        CHECK(open_buf(&m) == -108 && m == NULL && live_blocks == blocks);
        GetMoviesError();
    }
    fail_at = 0;
    CHECK(open_buf(&m) == noErr && live_blocks == blocks + 3);
    DisposeMovie(m);
    CHECK(live_blocks == blocks);
    printf("native allocation hooks: on\n");
#endif
    ExitMovies();

    printf("checks=%u failures=%u\n", checks, failures);
    if (failures == 0)
        printf("D4RLING-QTMOV02-E3B1-OK\n");
    return failures > 100 ? 100 : (int)failures;
}
