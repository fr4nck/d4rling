/* SPDX-License-Identifier: GPL-3.0-or-later
 * QT-NEXT witness: NewMovieFromDataRef (ptr data ref) + GetMovieDuration, Darwin i386.
 */
#include <QuickTime/QuickTime.h>
#include <malloc/malloc.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static unsigned checks, failures;
#define CHECK(e) do { ++checks; if (!(e)) { ++failures; printf("FAIL %d: %s\n", __LINE__, #e); } } while (0)

static uint8_t buf[4096];
static size_t len;
static void be32(uint8_t *p, uint32_t x) { p[0]=x>>24; p[1]=x>>16; p[2]=x>>8; p[3]=x; }
static void put32(uint32_t x) { be32(buf + len, x); len += 4; }
static void put(const char *s) { memcpy(buf + len, s, 4); len += 4; }
static void zero(size_t n) { memset(buf + len, 0, n); len += n; }
static size_t begin(const char *type) { size_t at = len; put32(0); put(type); return at; }
static void end(size_t at) { be32(buf + at, (uint32_t)(len - at)); }

/* mvhd v0 with the standard 100-byte payload. */
static void mvhd0(uint32_t scale, uint32_t duration)
{
    size_t a = begin("mvhd");
    put32(0); put32(0); put32(0); put32(scale); put32(duration);
    zero(100 - 20);
    end(a);
}
static void mvhd1(uint32_t scale, uint64_t duration)
{
    size_t a = begin("mvhd");
    put32(0x01000000); zero(16); put32(scale);
    put32((uint32_t)(duration >> 32)); put32((uint32_t)duration);
    zero(112 - 32);
    end(a);
}
/* ftyp, wide, 64-bit sized mdat with PCM bytes, then moov{trak, mvhd}. */
static void realistic(uint32_t scale, uint32_t duration)
{
    size_t a, i;
    len = 0;
    a = begin("ftyp"); put("qt  "); put32(0x20050300); put("qt  "); end(a);
    put32(8); put("wide");
    put32(1); put("mdat"); put32(0); put32(16 + 512);
    for (i = 0; i < 512; ++i) buf[len++] = (uint8_t)(i * 7);
    a = begin("moov");
    { size_t t = begin("trak"); size_t k = begin("tkhd"); zero(84); end(k); end(t); }
    mvhd0(scale, duration);
    end(a);
}
static void simple0(uint32_t scale, uint32_t duration)
{
    size_t a;
    len = 0;
    a = begin("ftyp"); put("qt  "); end(a);
    a = begin("moov"); mvhd0(scale, duration); end(a);
}

static PointerDataRefRecord rec;
static PointerDataRefPtr recp = &rec;
static Handle ref = (Handle)&recp;

static OSErr open_buf(const void *data, Size n, Movie *m, short *id)
{
    rec.data = (void *)data; rec.dataLength = n;
    return NewMovieFromDataRef(m, 0, id, ref, PointerDataHandlerSubType);
}

static size_t in_use(void)
{
    malloc_statistics_t st;
    malloc_zone_statistics(NULL, &st);
    return st.size_in_use;
}

/* Every refused input: exact code, NULL movie, error consumed once. */
static void expect_err(OSErr want, int line)
{
    Movie m = (Movie)1;
    short id = 77;
    OSErr e = open_buf(buf, (Size)len, &m, &id);
    ++checks; if (e != want) { ++failures; printf("FAIL %d: err %d want %d\n", line, e, want); }
    CHECK(m == NULL);
    CHECK(id == 77);
    CHECK(GetMoviesError() == want);
    CHECK(GetMoviesError() == noErr);
}
#define EXPECT_ERR(w) expect_err((w), __LINE__)

int main(void)
{
    Movie m = (Movie)1, m2 = NULL;
    short id = 0;
    size_t before;
    uint32_t seed = 12345;
    unsigned i, accepted = 0;

    printf("D4RLING-QTNEXT-I386-ENTRY sizeof(void*)=%u sizeof(Size)=%u sizeof(PointerDataRefRecord)=%u sizeof(TimeValue)=%u\n",
           (unsigned)sizeof(void *), (unsigned)sizeof(Size), (unsigned)sizeof(PointerDataRefRecord), (unsigned)sizeof(TimeValue));
    CHECK(sizeof(void *) == 4 && sizeof(Size) == 4 && sizeof(PointerDataRefRecord) == 8 && sizeof(TimeValue) == 4);

    /* Before EnterMovies. */
    simple0(600, 1500);
    CHECK(open_buf(buf, (Size)len, &m, NULL) == -2020);
    CHECK(m == NULL);
    CHECK(GetMoviesError() == -2020);
    CHECK(EnterMovies() == noErr);

    /* Positive: minimal v0 file. */
    m = (Movie)1; id = 0;
    CHECK(open_buf(buf, (Size)len, &m, &id) == noErr);
    CHECK(m != NULL && m != (Movie)1);
    CHECK(id == 0); /* id left unchanged */
    CHECK(GetMoviesError() == noErr);
    CHECK(GetMovieTimeScale(m) == 600);
    CHECK(GetMovieDuration(m) == 1500);
    CHECK(GetMoviesError() == noErr);
    { Movie m3 = NULL; short keep = 123;
      CHECK(open_buf(buf, (Size)len, &m3, &keep) == noErr && keep == 123);
      DisposeMovie(m3); }
    /* Bytes are not retained. */
    memset(buf, 0xA5, len);
    CHECK(GetMovieDuration(m) == 1500 && GetMovieTimeScale(m) == 600);
    /* Parsed duration: rescale refused, unchanged. */
    SetMovieTimeScale(m, 1200);
    CHECK(GetMoviesError() == -4);
    CHECK(GetMovieTimeScale(m) == 600 && GetMovieDuration(m) == 1500);

    /* Positive: realistic layout, 8 kHz PCM-like 0.25 s at timescale 1000. */
    realistic(1000, 250);
    CHECK(open_buf(buf, (Size)len, &m2, NULL) == noErr);
    CHECK(GetMovieTimeScale(m2) == 1000 && GetMovieDuration(m2) == 250);
    CHECK(GetMovieDuration(m) == 1500); /* independent objects */
    DisposeMovie(m2);
    CHECK(GetMoviesError() == noErr);
    CHECK(GetMovieDuration(m2) == 0 && GetMoviesError() == -2010);

    /* Positive: v1 header, bare moov atom, limits, zero duration. */
    len = 0; { size_t a = begin("moov"); mvhd1(44100, 88200); end(a); }
    CHECK(open_buf(buf, (Size)len, &m2, NULL) == noErr);
    CHECK(GetMovieTimeScale(m2) == 44100 && GetMovieDuration(m2) == 88200);
    DisposeMovie(m2);
    len = 0; { size_t a = begin("moov"); mvhd1(INT32_MAX, INT32_MAX); end(a); }
    CHECK(open_buf(buf, (Size)len, &m2, NULL) == noErr);
    CHECK(GetMovieTimeScale(m2) == INT32_MAX && GetMovieDuration(m2) == INT32_MAX);
    DisposeMovie(m2);
    simple0(1, 0);
    CHECK(open_buf(buf, (Size)len, &m2, NULL) == noErr);
    CHECK(GetMovieDuration(m2) == 0 && GetMovieTimeScale(m2) == 1);
    SetMovieTimeScale(m2, 30); /* zero duration: still rescalable */
    CHECK(GetMoviesError() == noErr && GetMovieTimeScale(m2) == 30);
    DisposeMovie(m2);

    /* Empty NewMovie unchanged: 600, duration 0. */
    m2 = NewMovie(0);
    CHECK(m2 != NULL && GetMovieTimeScale(m2) == 600 && GetMovieDuration(m2) == 0);
    SetMovieTimeScale(m2, 44100);
    CHECK(GetMoviesError() == noErr && GetMovieTimeScale(m2) == 44100);
    DisposeMovie(m2);
    CHECK(GetMovieDuration(NULL) == 0 && GetMoviesError() == -2010);

    /* Negative: parameters and data references. */
    simple0(600, 1500);
    CHECK(NewMovieFromDataRef(NULL, 0, NULL, ref, PointerDataHandlerSubType) == -50);
    CHECK(GetMoviesError() == -50);
    rec.data = buf; rec.dataLength = (Size)len;
    m = (Movie)1;
    CHECK(NewMovieFromDataRef(&m, 1, NULL, ref, PointerDataHandlerSubType) == -4 && m == NULL);
    m = (Movie)1;
    CHECK(NewMovieFromDataRef(&m, 0, NULL, ref, 0x686E646C) == -2003 && m == NULL); /* hndl */
    m = (Movie)1;
    CHECK(NewMovieFromDataRef(&m, 0, NULL, NULL, PointerDataHandlerSubType) == -2012 && m == NULL);
    { PointerDataRefPtr nul = NULL; Handle hn = (Handle)&nul; m = (Movie)1;
      CHECK(NewMovieFromDataRef(&m, 0, NULL, hn, PointerDataHandlerSubType) == -2012 && m == NULL); }
    m = (Movie)1;
    CHECK(open_buf(NULL, (Size)len, &m, NULL) == -2012 && m == NULL);
    CHECK(open_buf(buf, 0, &m, NULL) == -2012);
    CHECK(open_buf(buf, -1, &m, NULL) == -2012);
    CHECK(GetMoviesError() == -2012 && GetMoviesError() == noErr);

    /* Negative: malformed MOV data. */
    simple0(600, 1500); len -= 81; EXPECT_ERR(-2002);           /* truncated mvhd payload */
    simple0(600, 1500); len -= 1; EXPECT_ERR(-2002);            /* moov overruns buffer */
    simple0(600, 1500); be32(buf, 4); EXPECT_ERR(-2002);        /* atom size < 8 */
    simple0(600, 1500); be32(buf + 12, 0xFFFFFFF0u); EXPECT_ERR(-2002); /* offset out of bounds */
    len = 0; put32(1); put("mdat"); put32(0xFFFFFFFFu); put32(0xFFFFFFF0u); zero(8);
    EXPECT_ERR(-2002);                                           /* 64-bit length overflow */
    len = 0; put32(1); put("mdat"); put32(0); put32(8); zero(8);
    EXPECT_ERR(-2002);                                           /* 64-bit length < header */
    len = 0; { size_t a = begin("ftyp"); put("qt  "); end(a); a = begin("free"); zero(8); end(a); }
    EXPECT_ERR(-2048);                                           /* no moov */
    len = 0; { size_t a = begin("moov"); size_t t = begin("trak"); zero(8); end(t); end(a); }
    EXPECT_ERR(-2048);                                           /* moov without mvhd */
    simple0(600, 1500); buf[12 + 8 + 8] = 2; EXPECT_ERR(-2002);  /* mvhd version 2 */
    simple0(0, 1500); EXPECT_ERR(-2002);                         /* timescale 0 */
    simple0(0x80000000u, 1500); EXPECT_ERR(-2002);               /* timescale > INT32_MAX */
    simple0(600, 0x80000000u); EXPECT_ERR(-2014);                /* duration > INT32_MAX */
    simple0(600, 0xFFFFFFFFu); EXPECT_ERR(-2014);                /* unknown duration */
    len = 0; { size_t a = begin("moov"); mvhd1(600, (uint64_t)1 << 40); end(a); }
    EXPECT_ERR(-2014);                                           /* v1 long duration */
    len = 0; { size_t a = begin("moov"); mvhd1(600, UINT64_MAX); end(a); }
    EXPECT_ERR(-2014);

    /* Refusals allocate nothing (after warming the tiny cache). */
    { Movie w = NewMovie(0); DisposeMovie(w); }
    simple0(600, 0x80000000u);
    before = in_use();
    for (i = 0; i < 1000; ++i) { Movie x; open_buf(buf, (Size)len, &x, NULL); }
    CHECK(in_use() == before);
    GetMoviesError();

    /* Deterministic fuzz: truncations and byte flips of a realistic file. */
    for (i = 0; i < 5000; ++i) {
        OSErr e; Movie x = (Movie)1; size_t n, j;
        realistic(1000, 250);
        seed = seed * 1103515245u + 12345u;
        n = (seed >> 8) % (len + 1);
        if (i & 1) { len = n; }
        else for (j = 0; j < 3; ++j) { seed = seed * 1103515245u + 12345u; buf[(seed >> 8) % len] = (uint8_t)(seed >> 24); }
        e = open_buf(buf, (Size)len, &x, NULL);
        if (e == noErr) {
            ++accepted;
            CHECK(x != NULL && GetMovieTimeScale(x) > 0 && GetMovieDuration(x) >= 0);
            DisposeMovie(x);
        } else {
            CHECK((e == -2002 || e == -2048 || e == -2014 || e == -2012) && x == NULL);
        }
        GetMoviesError();
    }
    printf("fuzz accepted=%u/5000\n", accepted);

    /* Cleanup with a live parsed movie. */
    ExitMovies();
    CHECK(GetMovieDuration(m) == 0 && GetMoviesError() == -2020);

    printf("checks=%u failures=%u\n", checks, failures);
    if (failures == 0)
        printf("D4RLING-QTNEXT-I386-OK\n");
    return failures > 100 ? 100 : (int)failures;
}
