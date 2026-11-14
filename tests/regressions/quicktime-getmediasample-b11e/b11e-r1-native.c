/* SPDX-License-Identifier: GPL-3.0-or-later
 * QT-B11E-R1: native witness of the real MOV PCM extractor (qt_mov_pcm.c +
 * qt_mov_probe.c) on the six B11E-R0 MOV vectors.
 *
 * Reuses the MOV builder of tests/regressions/quicktime-mov-pcm/test_mov_pcm.c
 * (included, its main renamed), replaces only the mdat samples located by
 * d4rl_qt_mov_find_pcm, writes each MOV and each extracted PCM to OUT for an
 * independent oracle (verify_r1.py), then runs bounded negative campaigns:
 * every single-bit flip, every truncation, named structural corruptions,
 * destination bounds and source lifetime. Every parser input is an exact-size
 * heap copy, so AddressSanitizer reports any read past the MOV.
 *
 * Usage: b11e-r1-native OUT_DIR      Exit status: number of failures (cap 100).
 */
#define main e1_main
#include "test_mov_pcm.c"
#undef main

#include <errno.h>

#define NVEC 6
#define FRAMES 100u
#define PCM_BYTES (FRAMES * 2u)

static const char *const vec_name[NVEC] = {
    "silence", "alternating_pm1", "impulse_32767", "alternating_limits", "ramp", "aperiodic"
};

static unsigned r1_checks, r1_failures;
static void verdict(int ok, const char *what, int v, const char *fmt, ...)
    __attribute__((format(printf, 4, 5)));
#include <stdarg.h>
static void verdict(int ok, const char *what, int v, const char *fmt, ...)
{
    va_list ap;
    ++r1_checks;
    if (!ok)
        ++r1_failures;
    printf("R1 %s v%d %s ", what, v, ok ? "PASS" : "FAIL");
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    putchar('\n');
}

/* B11E-R0 definition (same formulas as the B11C bench b11_fill), S16BE. */
static void fill_vector(uint8_t *dst, unsigned mode)
{
    unsigned i;
    for (i = 0; i < FRAMES; ++i) {
        int v = 0;
        switch (mode) {
        case 0: v = 0; break;
        case 1: v = (i & 1u) ? -1 : 1; break;
        case 2: v = (i == 0u) ? 32767 : 0; break;
        case 3: v = (i & 1u) ? -32768 : 32767; break;
        case 4: v = -32768 + (int)((i * 65535u) / 99u); break;
        case 5: v = (int)((i * 7919u + i * i * 17u + 12345u) & 65535u) - 32768; break;
        }
        dst[2 * i] = (uint8_t)((unsigned)(uint16_t)v >> 8);
        dst[2 * i + 1] = (uint8_t)(uint16_t)v;
    }
}

static uint8_t mov[NVEC][1024];
static size_t mov_len[NVEC], pcm_off[NVEC];
static uint8_t vec[NVEC][PCM_BYTES];

/* Exact-size heap copy of a MOV; extraction into an exact-size heap buffer. */
static int extract_exact(const uint8_t *src, size_t n, uint8_t *dst, size_t cap,
                         struct d4rl_qt_mov_pcm_info *pi)
{
    uint8_t *heap = malloc(n ? n : 1), *out_heap = malloc(cap ? cap : 1);
    int status;
    if (!heap || !out_heap) {
        free(heap); free(out_heap);
        return 1000;
    }
    memcpy(heap, src, n);
    memset(out_heap, 0xA5, cap);
    status = d4rl_qt_mov_extract_pcm(heap, n, cap ? out_heap : NULL, cap, pi);
    free(heap);
    memcpy(dst, out_heap, cap);
    free(out_heap);
    return status;
}

static int write_file(const char *dir, const char *name, const void *p, size_t n)
{
    char path[4096];
    FILE *f;
    snprintf(path, sizeof(path), "%s/%s", dir, name);
    f = fopen(path, "wb");
    if (!f)
        return 0;
    if (fwrite(p, 1, n, f) != n) { fclose(f); return 0; }
    return fclose(f) == 0;
}

static int all_bytes(const uint8_t *p, size_t n, uint8_t value)
{
    size_t i;
    for (i = 0; i < n; ++i)
        if (p[i] != value)
            return 0;
    return 1;
}

static int info_poisoned(const struct d4rl_qt_mov_pcm_info *pi)
{
    return all_bytes((const uint8_t *)pi, sizeof(*pi), 0xCD);
}

/* Offset of the first atom of this type (header at returned offset). */
static size_t atom_at(const uint8_t *p, size_t n, const char tag[4])
{
    size_t i;
    for (i = 4; i + 4 <= n; ++i)
        if (memcmp(p + i, tag, 4) == 0)
            return i - 4;
    return (size_t)-1;
}

static void put_be32(uint8_t *p, uint32_t x) { p[0] = x >> 24; p[1] = x >> 16; p[2] = x >> 8; p[3] = (uint8_t)x; }
static uint32_t get_be32(const uint8_t *p) { return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 | p[3]; }

static void build_vectors(const char *out)
{
    int v;
    for (v = 0; v < NVEC; ++v) {
        struct cfg c = base(1, 8000);
        struct d4rl_qt_mov_pcm_info pi;
        size_t off = 0;
        uint8_t *heap;
        int st;
        char name[64];

        build(&c);                 /* original fixture builder */
        heap = malloc(len);
        memcpy(heap, buf, len);
        st = d4rl_qt_mov_find_pcm(heap, len, &pi, &off);
        free(heap);
        verdict(st == D4RL_QT_PCM_OK && pi.byte_count == PCM_BYTES && pi.frame_count == FRAMES &&
                pi.channels == 1 && pi.bits_per_sample == 16 && pi.sample_rate == 8000 &&
                pi.format == 0x74776F73u && off == 44 && len == 761, /* B11E-R0 contract */
                "find_pcm_template", v, "status=%d offset=%zu bytes=%zu frames=%u rate=%u ch=%u len=%zu",
                st, off, st == 0 ? pi.byte_count : 0, st == 0 ? pi.frame_count : 0,
                st == 0 ? pi.sample_rate : 0, st == 0 ? pi.channels : 0, len);
        if (st != D4RL_QT_PCM_OK || off + PCM_BYTES > len || len > sizeof(mov[v]))
            continue;
        fill_vector(vec[v], (unsigned)v);
        memcpy(buf + off, vec[v], PCM_BYTES);   /* only the located samples change */
        memcpy(mov[v], buf, len);
        mov_len[v] = len;
        pcm_off[v] = off;
        snprintf(name, sizeof(name), "mov-%d.mov", v);
        verdict(write_file(out, name, mov[v], len), "write_mov", v, "%s", name);
    }
}

static void extract_vectors(const char *out)
{
    int v;
    for (v = 0; v < NVEC; ++v) {
        struct d4rl_qt_mov_pcm_info pi;
        uint8_t got[PCM_BYTES];
        size_t off = 0;
        uint8_t *heap = malloc(mov_len[v]);
        char name[64];
        int st, st2;

        memcpy(heap, mov[v], mov_len[v]);
        st2 = d4rl_qt_mov_find_pcm(heap, mov_len[v], &pi, &off);
        free(heap);
        verdict(st2 == 0 && off == pcm_off[v], "find_pcm_vector", v, "status=%d offset=%zu", st2, off);

        memset(&pi, 0xCD, sizeof(pi));
        st = extract_exact(mov[v], mov_len[v], got, PCM_BYTES, &pi);
        verdict(st == 0 && pi.byte_count == PCM_BYTES && pi.frame_count == FRAMES &&
                pi.sample_rate == 8000 && pi.channels == 1 && pi.bits_per_sample == 16 &&
                pi.format == 0x74776F73u && memcmp(got, vec[v], PCM_BYTES) == 0,
                "extract", v, "name=%s status=%d bytes=%zu frames=%u", vec_name[v], st,
                st == 0 ? pi.byte_count : 0, st == 0 ? pi.frame_count : 0);
        snprintf(name, sizeof(name), "pcm-%d.bin", v);
        if (st == 0)
            verdict(write_file(out, name, got, PCM_BYTES), "write_pcm", v, "%s", name);
    }
}

/* The destination must be an independent copy: freeing (and scribbling)
 * the source must not change it. */
static void lifetime(void)
{
    int v;
    for (v = 0; v < NVEC; ++v) {
        struct d4rl_qt_mov_pcm_info pi;
        uint8_t *src = malloc(mov_len[v]), *dst = malloc(PCM_BYTES);
        int st;
        memcpy(src, mov[v], mov_len[v]);
        st = d4rl_qt_mov_extract_pcm(src, mov_len[v], dst, PCM_BYTES, &pi);
        memset(src, 0x5A, mov_len[v]);
        free(src);
        verdict(st == 0 && memcmp(dst, vec[v], PCM_BYTES) == 0, "copy_outlives_source", v, "status=%d", st);
        free(dst);
    }
}

/* Destination bounds: one byte short refused untouched; exact; one more
 * byte keeps its canary. */
static void write_bounds(void)
{
    int v;
    for (v = 0; v < NVEC; ++v) {
        struct d4rl_qt_mov_pcm_info pi;
        uint8_t got[PCM_BYTES + 1];
        int st;

        memset(&pi, 0xCD, sizeof(pi));
        st = extract_exact(mov[v], mov_len[v], got, PCM_BYTES - 1, &pi);
        verdict(st == D4RL_QT_PCM_BUFFER_TOO_SMALL && all_bytes(got, PCM_BYTES - 1, 0xA5) && info_poisoned(&pi),
                "capacity_199_refused", v, "status=%d", st);
        memset(&pi, 0xCD, sizeof(pi));
        st = extract_exact(mov[v], mov_len[v], got, 0, &pi);
        verdict(st == D4RL_QT_PCM_BUFFER_TOO_SMALL && info_poisoned(&pi), "capacity_0_null_refused", v, "status=%d", st);
        st = extract_exact(mov[v], mov_len[v], got, PCM_BYTES + 1, &pi);
        verdict(st == 0 && memcmp(got, vec[v], PCM_BYTES) == 0 && got[PCM_BYTES] == 0xA5,
                "capacity_201_canary", v, "status=%d canary=0x%02x", st, got[PCM_BYTES]);
    }
}

/* Every truncation of every vector MOV is refused, outputs untouched. */
static void truncations(void)
{
    int v;
    for (v = 0; v < NVEC; ++v) {
        size_t n, bad = 0, accepted = 0;
        for (n = 0; n < mov_len[v]; ++n) {
            struct d4rl_qt_mov_pcm_info pi;
            uint8_t got[PCM_BYTES];
            int st;
            memset(&pi, 0xCD, sizeof(pi));
            st = extract_exact(mov[v], n, got, PCM_BYTES, &pi);
            if (st == 0)
                ++accepted;
            else if (!(st < 0 && st >= D4RL_QT_PCM_BUFFER_TOO_SMALL && all_bytes(got, PCM_BYTES, 0xA5) && info_poisoned(&pi)))
                ++bad;
        }
        verdict(accepted == 0 && bad == 0, "all_truncations_refused", v, "lengths=%zu accepted=%zu bad=%zu",
                mov_len[v], accepted, bad);
    }
}

/* Every single-bit flip of every vector MOV.
 *  - a flip inside the 200 sample bytes is accepted and changes exactly that
 *    bit of the extracted PCM (a 1-bit mutation always reaches the output);
 *  - any refusal leaves the outputs untouched;
 *  - an accepted flip outside the samples either returns the original bytes
 *    or is counted (e.g. stco offset bits still inside mdat), never bytes
 *    from outside the file. */
static void bit_flips(const char *out)
{
    int v;
    for (v = 0; v < NVEC; ++v) {
        size_t byte, in_ok = 0, in_bad = 0, refused = 0, refused_bad = 0, same = 0, changed = 0;
        unsigned bit;
        uint8_t m[1024];
        for (byte = 0; byte < mov_len[v]; ++byte) {
            for (bit = 0; bit < 8; ++bit) {
                struct d4rl_qt_mov_pcm_info pi;
                uint8_t got[PCM_BYTES];
                int st, inside = byte >= pcm_off[v] && byte < pcm_off[v] + PCM_BYTES;
                memcpy(m, mov[v], mov_len[v]);
                m[byte] ^= (uint8_t)(1u << bit);
                memset(&pi, 0xCD, sizeof(pi));
                st = extract_exact(m, mov_len[v], got, PCM_BYTES, &pi);
                if (inside) {
                    uint8_t want[PCM_BYTES];
                    memcpy(want, vec[v], PCM_BYTES);
                    want[byte - pcm_off[v]] ^= (uint8_t)(1u << bit);
                    if (st == 0 && pi.byte_count == PCM_BYTES && memcmp(got, want, PCM_BYTES) == 0 &&
                        memcmp(got, vec[v], PCM_BYTES) != 0)
                        ++in_ok;
                    else
                        ++in_bad;
                    if (v == 5 && byte == pcm_off[v] + 37 && bit == 3 && st == 0)
                        write_file(out, "pcm-5-bitflip.bin", got, PCM_BYTES);
                } else if (st != 0) {
                    ++refused;
                    if (!(st < 0 && st >= D4RL_QT_PCM_BUFFER_TOO_SMALL && all_bytes(got, PCM_BYTES, 0xA5) && info_poisoned(&pi)))
                        ++refused_bad;
                } else if (pi.byte_count == PCM_BYTES && memcmp(got, vec[v], PCM_BYTES) == 0) {
                    ++same;
                } else {
                    ++changed;
                }
            }
        }
        verdict(in_ok == PCM_BYTES * 8 && in_bad == 0 && refused_bad == 0, "single_bit_flips", v,
                "flips=%zu sample_flips_detected=%zu sample_flips_bad=%zu outside_refused=%zu "
                "outside_refused_bad=%zu outside_same=%zu outside_changed=%zu",
                mov_len[v] * 8, in_ok, in_bad, refused, refused_bad, same, changed);
    }
}

/* Named structural corruptions with their expected status. */
static void structures(void)
{
    struct corruption { const char *name; int want; };
    static const struct corruption cases[] = {
        { "stco_plus_17_past_mdat", D4RL_QT_PCM_OUT_OF_BOUNDS },
        { "stco_minus_17_before_payload", D4RL_QT_PCM_OUT_OF_BOUNDS },
        { "stco_points_into_moov", D4RL_QT_PCM_OUT_OF_BOUNDS },
        { "mdat_size_past_eof", D4RL_QT_PCM_BAD_MOVIE },
        { "mdat_size_7", D4RL_QT_PCM_BAD_MOVIE },
        { "moov_size_past_eof", D4RL_QT_PCM_BAD_MOVIE },
        { "stsz_count_99", D4RL_QT_PCM_INCONSISTENT },
        { "stts_count_101", D4RL_QT_PCM_INCONSISTENT },
        { "mdhd_scale_22050", D4RL_QT_PCM_INCONSISTENT },
        { "format_ima4", D4RL_QT_PCM_UNSUPPORTED },
        { "channels_3", D4RL_QT_PCM_UNSUPPORTED },
        { "hdlr_vide", D4RL_QT_PCM_NO_SOUND_TRACK },
        { "dref_external", D4RL_QT_PCM_UNSUPPORTED },
    };
    int v;
    size_t k;
    for (v = 0; v < NVEC; ++v) {
        for (k = 0; k < sizeof(cases) / sizeof(cases[0]); ++k) {
            uint8_t m[1024];
            size_t n = mov_len[v], a;
            struct d4rl_qt_mov_pcm_info pi;
            uint8_t got[PCM_BYTES];
            int st, applied = 1;
            memcpy(m, mov[v], n);
            switch (k) {
            case 0: a = atom_at(m, n, "stco"); put_be32(m + a + 16, get_be32(m + a + 16) + 17); break;
            case 1: a = atom_at(m, n, "stco"); put_be32(m + a + 16, get_be32(m + a + 16) - 17); break;
            case 2: a = atom_at(m, n, "stco"); put_be32(m + a + 16, (uint32_t)atom_at(m, n, "moov") + 8); break;
            case 3: a = atom_at(m, n, "mdat"); put_be32(m + a, (uint32_t)(n - a + 1)); break;
            case 4: a = atom_at(m, n, "mdat"); put_be32(m + a, 7); break;
            case 5: a = atom_at(m, n, "moov"); put_be32(m + a, (uint32_t)(n - a + 1)); break;
            case 6: a = atom_at(m, n, "stsz"); put_be32(m + a + 16, 99); break;
            case 7: a = atom_at(m, n, "stts"); put_be32(m + a + 16, 101); break;
            case 8: a = atom_at(m, n, "mdhd"); put_be32(m + a + 20, 22050); break;
            case 9: a = atom_at(m, n, "twos"); memcpy(m + a + 4, "ima4", 4); break;
            case 10: a = atom_at(m, n, "twos"); m[a + 8 + 16] = 0; m[a + 8 + 17] = 3; break;
            case 11: a = atom_at(m, n, "hdlr"); memcpy(m + a + 16, "vide", 4); break;
            case 12: a = atom_at(m, n, "alis"); put_be32(m + a + 8, 0); break;
            default: applied = 0; a = 0;
            }
            (void)a;
            memset(&pi, 0xCD, sizeof(pi));
            st = extract_exact(m, n, got, PCM_BYTES, &pi);
            verdict(applied && st == cases[k].want && all_bytes(got, PCM_BYTES, 0xA5) && info_poisoned(&pi),
                    cases[k].name, v, "status=%d want=%d", st, cases[k].want);
        }
    }
}

int main(int argc, char **argv)
{
    int e1;
    if (argc != 2) {
        fprintf(stderr, "usage: %s OUT_DIR\n", argv[0]);
        return 2;
    }
    printf("R1_ABI pointer_bits=%zu size_t_bits=%zu\n", sizeof(void *) * 8, sizeof(size_t) * 8);
    build_vectors(argv[1]);
    extract_vectors(argv[1]);
    lifetime();
    write_bounds();
    truncations();
    bit_flips(argv[1]);
    structures();
    printf("R1_SUMMARY checks=%u failures=%u\n", r1_checks, r1_failures);
    fflush(stdout);
    /* Existing extractor regression (QT-MOV-02 E1..R6, 20 000 fuzz cases). */
    e1 = e1_main();
    printf("E1_RC=%d\n", e1);
    if (r1_failures == 0 && e1 == 0)
        printf("B11E_R1_WITNESS_OK\n");
    return (int)(r1_failures + (unsigned)e1 > 100 ? 100 : r1_failures + (unsigned)e1);
}
