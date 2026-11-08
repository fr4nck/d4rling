/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "qt_mov_probe.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned tests, failures;
#define CHECK(expr) do { ++tests; if (!(expr)) { ++failures; \
    fprintf(stderr, "FAIL %d: %s\n", __LINE__, #expr); } } while (0)

static void be32(uint8_t *p, uint32_t x)
{
    p[0] = (uint8_t)(x >> 24); p[1] = (uint8_t)(x >> 16);
    p[2] = (uint8_t)(x >> 8); p[3] = (uint8_t)x;
}
static void be64(uint8_t *p, uint64_t x)
{
    be32(p, (uint32_t)(x >> 32)); be32(p + 4, (uint32_t)x);
}
static void atom(uint8_t *p, uint32_t len, const char type[4])
{
    be32(p, len); memcpy(p + 4, type, 4);
}
/* ftyp(12) + moov(36) containing mvhd(28), minimal v0 metadata. */
static size_t make_v0(uint8_t *p)
{
    memset(p, 0, 128);
    atom(p, 12, "ftyp"); memcpy(p + 8, "qt  ", 4);
    atom(p + 12, 36, "moov"); atom(p + 20, 28, "mvhd");
    be32(p + 40, 600); be32(p + 44, 1500); /* time 2.5 s */
    return 48;
}
/* moov extended-size(16) containing mvhd version 1 (8 + 32). */
static size_t make_v1(uint8_t *p)
{
    memset(p, 0, 128);
    atom(p, 1, "moov"); be64(p + 8, 56);
    atom(p + 16, 40, "mvhd"); p[24] = 1;
    be32(p + 44, 1000); be64(p + 48, UINT64_C(4294967297));
    return 56;
}
static void expect_status(const uint8_t *p, size_t n, int expected)
{
    struct d4rl_qt_mov_header info = {123, 456, 9};
    CHECK(d4rl_qt_mov_probe(p, n, &info) == expected);
    CHECK(info.timescale == 123 && info.duration == 456 && info.version == 9);
}

static void tests_synthetic(void)
{
    uint8_t p[128];
    size_t n;
    struct d4rl_qt_mov_header info;
    CHECK(d4rl_qt_mov_probe(NULL, 0, &info) == D4RL_QT_MOV_INVALID_ARGUMENT);
    CHECK(d4rl_qt_mov_probe(p, 0, NULL) == D4RL_QT_MOV_INVALID_ARGUMENT);
    expect_status(p, 0, D4RL_QT_MOV_NO_MOVIE_HEADER);
    n = make_v0(p);
    CHECK(d4rl_qt_mov_probe(p, n, &info) == D4RL_QT_MOV_OK);
    CHECK(info.timescale == 600 && info.duration == 1500 && info.version == 0);
    be32(p + 12, 0); /* moov size==0: until EOF */
    CHECK(d4rl_qt_mov_probe(p, n, &info) == D4RL_QT_MOV_OK);
    CHECK(info.duration == 1500);
    n = make_v1(p);
    CHECK(d4rl_qt_mov_probe(p, n, &info) == D4RL_QT_MOV_OK);
    CHECK(info.timescale == 1000 && info.duration == UINT64_C(4294967297) && info.version == 1);
    p[24] = 2; expect_status(p, n, D4RL_QT_MOV_UNSUPPORTED_VERSION);
    n = make_v0(p);
    be32(p + 40, 0); expect_status(p, n, D4RL_QT_MOV_BAD_TIMESCALE);
    be32(p + 40, UINT32_MAX); expect_status(p, n, D4RL_QT_MOV_BAD_TIMESCALE);
    n = make_v0(p);
    atom(p + 20, 12, "mvhd"); expect_status(p, n, D4RL_QT_MOV_TRUNCATED);
    n = make_v0(p);
    memcpy(p + 24, "none", 4); expect_status(p, n, D4RL_QT_MOV_NO_MOVIE_HEADER);
    n = make_v0(p);
    atom(p + 12, 7, "moov"); expect_status(p, n, D4RL_QT_MOV_BAD_ATOM);
    n = make_v0(p);
    atom(p + 12, 200, "moov"); expect_status(p, n, D4RL_QT_MOV_TRUNCATED);
    n = make_v0(p);
    atom(p + 12, 1, "moov"); be64(p + 20, 14); expect_status(p, n, D4RL_QT_MOV_BAD_ATOM);
    n = make_v0(p);
    atom(p + 12, 1, "moov"); be64(p + 20, 200); expect_status(p, n, D4RL_QT_MOV_TRUNCATED);
    n = make_v0(p);
    p[20] = 0; p[21] = 0; p[22] = 0; p[23] = 7; expect_status(p, n, D4RL_QT_MOV_BAD_ATOM);
    n = make_v0(p);
    be32(p + 44, UINT32_MAX);
    CHECK(d4rl_qt_mov_probe(p, n, &info) == D4RL_QT_MOV_OK);
    CHECK(info.duration == UINT32_MAX);
    n = make_v0(p);
    expect_status(p, 3, D4RL_QT_MOV_TRUNCATED);
    expect_status(p, n - 1, D4RL_QT_MOV_TRUNCATED);
    /* mvhd with an extended-size header, moov with a normal header. */
    memset(p, 0, sizeof(p));
    atom(p, 44, "moov"); atom(p + 8, 1, "mvhd"); be64(p + 16, 36);
    be32(p + 36, 48000); be32(p + 40, 96000);
    CHECK(d4rl_qt_mov_probe(p, 44, &info) == D4RL_QT_MOV_OK);
    CHECK(info.timescale == 48000 && info.duration == 96000);
    /* Fuzzer exercises all short/truncated/unknown atom shapes under sanitizers. */
    {
        uint32_t x = 0xC0FFEE;
        size_t j, k;
        for (j = 0; j < 5000; ++j) {
            for (k = 0; k < sizeof(p); ++k) {
                x = x * 1664525U + 1013904223U;
                p[k] = (uint8_t)(x >> 24);
            }
            (void)d4rl_qt_mov_probe(p, j % sizeof(p), &info);
            ++tests;
        }
    }
}

static void test_real_mov(const char *path)
{
    FILE *f = fopen(path, "rb");
    struct d4rl_qt_mov_header info;
    uint8_t *p;
    long size;
    CHECK(f != NULL);
    if (!f) return;
    CHECK(fseek(f, 0, SEEK_END) == 0);
    size = ftell(f);
    CHECK(size > 0 && size <= 16 * 1024 * 1024);
    if (size <= 0 || size > 16 * 1024 * 1024) { fclose(f); return; }
    CHECK(fseek(f, 0, SEEK_SET) == 0);
    p = malloc((size_t)size);
    CHECK(p != NULL);
    if (!p) { fclose(f); return; }
    CHECK(fread(p, 1, (size_t)size, f) == (size_t)size);
    CHECK(fclose(f) == 0);
    CHECK(d4rl_qt_mov_probe(p, (size_t)size, &info) == D4RL_QT_MOV_OK);
    CHECK(info.timescale > 0);
    CHECK(info.duration > 0);
    CHECK(info.duration * 4 == info.timescale); /* 0.25 s fixture */
    printf("MOV_TIMESCALE=%u MOV_DURATION=%llu\n", (unsigned)info.timescale,
           (unsigned long long)info.duration);
    free(p);
}

int main(int argc, char **argv)
{
    tests_synthetic();
    if (argc > 1) test_real_mov(argv[1]);
    printf("CHECKS=%u FAILURES=%u\n", tests, failures);
    return failures == 0 ? 0 : 1;
}
