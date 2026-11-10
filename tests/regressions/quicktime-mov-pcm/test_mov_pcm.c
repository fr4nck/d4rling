/* SPDX-License-Identifier: GPL-3.0-or-later
 * QT-MOV-02 / E1 native witness for d4rl_qt_mov_extract_pcm.
 */
#include "qt_mov_pcm.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks, failures;
#define CHECK(e) do { ++checks; if (!(e)) { ++failures; printf("FAIL %d: %s\n", __LINE__, #e); } } while (0)

static uint8_t buf[16384];
static size_t len, stco_field;
static uint8_t ref[8192];
static size_t ref_len;
static uint8_t out[4096];
static size_t cap = sizeof(out);
static struct d4rl_qt_mov_pcm_info info;

static void be32(uint8_t *p, uint32_t x) { p[0]=x>>24; p[1]=x>>16; p[2]=x>>8; p[3]=x; }
static void put8(uint8_t x) { buf[len++] = x; }
static void put16(uint16_t x) { put8(x >> 8); put8((uint8_t)x); }
static void put32(uint32_t x) { be32(buf + len, x); len += 4; }
static void put4(const char *s) { memcpy(buf + len, s, 4); len += 4; }
static void zero(size_t n) { memset(buf + len, 0, n); len += n; }
static size_t begin(const char *type) { size_t at = len; put32(0); put4(type); return at; }
static void end(size_t at) { be32(buf + at, (uint32_t)(len - at)); }

struct cfg {
    const char *fmt;
    uint16_t channels, bits, sound_version, compression_id;
    uint32_t rate, timescale, mdhd_duration, frames;
    uint32_t stts_entries, stts_delta, stsc_entries, stsc_spc, stsc_first;
    uint32_t stsz_size, stsz_count, stco_entries, stsd_entries;
    int32_t offset_delta;
    uint32_t data_frames; /* frames stored in mdat; 0 = frames */
    uint16_t dri;                /* stsd data reference index */
    uint8_t reserved_byte;       /* written into stsd reserved byte 2 */
    uint32_t dref_vf, dref_count, dref_n; /* dref header and entries */
    const char *ref_type[3];
    uint32_t ref_vf[3];
    int ref_short, no_dinf, no_dref;
    int moov_first, video_trak, sound_traks, co64;
    int mdhd_v1, mdhd_omit_tail; /* test fixture only: v1 layout and truncation */
};

static struct cfg base(uint16_t channels, uint32_t hz)
{
    struct cfg c = { .fmt = "twos", .channels = channels, .bits = 16, .rate = hz << 16,
        .timescale = hz, .mdhd_duration = 100, .frames = 100, .stts_entries = 1,
        .stts_delta = 1, .stsc_entries = 1, .stsc_spc = 100, .stsc_first = 1,
        .stsz_size = channels * 2u, .stsz_count = 100, .stco_entries = 1,
        .stsd_entries = 1, .sound_traks = 1, .dri = 1, .dref_n = 1,
        .ref_type = { "alis", "url ", "alis" }, .ref_vf = { 1, 1, 1 } };
    return c;
}

static void trak(const struct cfg *c, const char *handler)
{
    size_t t = begin("trak"), a, m, s, st, e;
    uint32_t i;
    a = begin("tkhd"); put32(1); zero(80); end(a);
    m = begin("mdia");
    a = begin("mdhd");
    if (c->mdhd_v1) {
        put32(0x01000000u); /* version 1, zero flags */
        zero(16);          /* 64-bit creation and modification times */
        put32(c->timescale);
        put32(0); put32(c->mdhd_duration); /* 64-bit duration */
        if (c->mdhd_omit_tail)
            zero((size_t)(4 - c->mdhd_omit_tail)); /* omit 1..4 trailing bytes */
        else
            put32(0);     /* language and quality: required four bytes */
    } else {
        put32(0); put32(0); put32(0); put32(c->timescale);
        put32(c->mdhd_duration); put32(0);
    }
    end(a);
    a = begin("hdlr"); put32(0); put4("mhlr"); put4(handler); zero(12); put8(0); end(a);
    s = begin("minf");
    a = begin(handler[0] == 's' ? "smhd" : "vmhd"); put32(0); put32(0); end(a);
    if (!c->no_dinf) {
        a = begin("dinf");
        if (!c->no_dref) {
            e = begin("dref"); put32(c->dref_vf); put32(c->dref_count ? c->dref_count : c->dref_n);
            for (i = 0; i < c->dref_n; ++i) {
                size_t r = begin(c->ref_type[i]);
                if (c->ref_short && i == 0) { put16(0); end(r); continue; }
                put32(c->ref_vf[i]);
                if (!(c->ref_vf[i] & 1)) { memcpy(buf + len, "file:///ext.mov", 16); len += 16; }
                end(r);
            }
            end(e);
        }
        end(a);
    }
    st = begin("stbl");
    a = begin("stsd"); put32(0); put32(c->stsd_entries);
    for (i = 0; i < c->stsd_entries; ++i) {
        e = begin(c->fmt); zero(6); buf[len - 4] = c->reserved_byte; put16(c->dri);
        put16(c->sound_version); put16(0); put32(0);
        put16(c->channels); put16(c->bits); put16(c->compression_id); put16(0); put32(c->rate);
        end(e);
    }
    end(a);
    a = begin("stts"); put32(0); put32(c->stts_entries);
    for (i = 0; i < c->stts_entries; ++i) { put32(c->frames / c->stts_entries); put32(c->stts_delta); }
    end(a);
    a = begin("stsc"); put32(0); put32(c->stsc_entries);
    for (i = 0; i < c->stsc_entries; ++i) { put32(c->stsc_first + i); put32(c->stsc_spc); put32(1); }
    end(a);
    a = begin("stsz"); put32(0); put32(c->stsz_size); put32(c->stsz_count); end(a);
    a = begin(c->co64 ? "co64" : "stco"); put32(0); put32(c->stco_entries);
    for (i = 0; i < c->stco_entries; ++i) { if (c->co64) put32(0); if (i == 0) stco_field = len; put32(0); }
    end(a);
    end(st); end(s); end(m); end(t);
}

static size_t mdat(void)
{
    size_t a = begin("mdat"), off;
    zero(16);
    off = len;
    memcpy(buf + len, ref, ref_len);
    len += ref_len;
    zero(16);
    end(a);
    return off;
}

static void build(const struct cfg *c)
{
    size_t a, i, data_off = 0;
    int k;
    ref_len = (size_t)(c->data_frames ? c->data_frames : c->frames) * c->channels * 2;
    for (i = 0; i < ref_len; ++i)
        ref[i] = (uint8_t)(i * 37u + 11u + (i >> 3));
    len = 0;
    a = begin("ftyp"); put4("qt  "); put32(0x20050300); put4("qt  "); end(a);
    if (!c->moov_first)
        data_off = mdat();
    a = begin("moov");
    { size_t h = begin("mvhd"); put32(0); put32(0); put32(0); put32(600); put32(75); zero(80); end(h); }
    if (c->video_trak)
        trak(c, "vide");
    for (k = 0; k < c->sound_traks; ++k)
        trak(c, "soun");
    end(a);
    if (c->moov_first)
        data_off = mdat();
    be32(buf + stco_field, (uint32_t)((int64_t)data_off + c->offset_delta));
}

/* Exact-size heap copy so that AddressSanitizer catches any overread. */
static int run(void)
{
    uint8_t *heap = malloc(len ? len : 1);
    int status;
    memcpy(heap, buf, len);
    status = d4rl_qt_mov_extract_pcm(heap, len, out, cap, &info);
    free(heap);
    return status;
}

static int untouched(void)
{
    const uint8_t *p = (const uint8_t *)&info;
    size_t i;
    for (i = 0; i < sizeof(out); ++i) if (out[i] != 0xCD) return 0;
    for (i = 0; i < sizeof(info); ++i) if (p[i] != 0xCD) return 0;
    return 1;
}

static void poison(void) { memset(out, 0xCD, sizeof(out)); memset(&info, 0xCD, sizeof(info)); }

/* Build() creates exactly one of each required table in this fixture.
 * Flip only the lowest flag byte in the version/flags full box header. */
static int corrupt_table_flags(const char tag[4])
{
    size_t i;
    for (i = 4; i + 8 <= len; ++i) {
        uint32_t atom_size;
        if (memcmp(buf + i, tag, 4) != 0)
            continue;
        atom_size = ((uint32_t)buf[i - 4] << 24) |
                    ((uint32_t)buf[i - 3] << 16) |
                    ((uint32_t)buf[i - 2] << 8) | buf[i - 1];
        if (atom_size < 16 || atom_size > len - (i - 4))
            continue;
        buf[i + 7] = 1;
        return 1;
    }
    return 0;
}

static void refuse(int want, int line)
{
    int got;
    poison();
    got = run();
    ++checks; if (got != want) { ++failures; printf("FAIL %d: status %d want %d\n", line, got, want); }
    ++checks; if (!untouched()) { ++failures; printf("FAIL %d: outputs modified on error\n", line); }
}
#define REFUSE(c, w) do { build(&(c)); refuse((w), __LINE__); } while (0)

static void accept(const struct cfg *c, uint32_t fourcc, int line)
{
    int got;
    build(c);
    poison();
    got = run();
    ++checks; if (got != D4RL_QT_PCM_OK) { ++failures; printf("FAIL %d: status %d\n", line, got); return; }
    CHECK(info.format == fourcc);
    CHECK(info.sample_rate == c->timescale);
    CHECK(info.channels == c->channels && info.bits_per_sample == 16);
    CHECK(info.frame_count == c->frames);
    CHECK(info.byte_count == ref_len);
    ++checks; if (memcmp(out, ref, ref_len) != 0) { ++failures; printf("FAIL %d: PCM bytes differ\n", line); }
    CHECK(ref_len >= sizeof(out) || out[ref_len] == 0xCD);
}

int main(void)
{
    struct cfg c;
    unsigned i, accepted = 0;
    uint32_t seed = 2026;
    size_t full;

    /* Positive. */
    c = base(1, 8000); accept(&c, 0x74776F73, __LINE__);                       /* twos mono, mdat first */
    CHECK(ref[0] != 0 || ref[1] != 0);
    c = base(2, 44100); c.fmt = "sowt"; c.moov_first = 1; c.video_trak = 1;
    accept(&c, 0x736F7774, __LINE__);                                          /* sowt stereo, moov first */
    c = base(2, 48000); c.frames = c.mdhd_duration = c.stsc_spc = c.stsz_count = 1000;
    accept(&c, 0x74776F73, __LINE__);                                          /* 4000 bytes */
    c = base(1, 8000); cap = 200; accept(&c, 0x74776F73, __LINE__); cap = sizeof(out); /* exact capacity */

    /* Arguments. */
    c = base(1, 8000); build(&c); poison();
    CHECK(d4rl_qt_mov_extract_pcm(NULL, len, out, cap, &info) == D4RL_QT_PCM_INVALID_ARGUMENT && untouched());
    CHECK(d4rl_qt_mov_extract_pcm(buf, len, out, cap, NULL) == D4RL_QT_PCM_INVALID_ARGUMENT && untouched());
    CHECK(d4rl_qt_mov_extract_pcm(buf, len, NULL, 10, &info) == D4RL_QT_PCM_INVALID_ARGUMENT && untouched());

    /* 3. Offsets outside mdat. */
    c = base(1, 8000); c.offset_delta = 17; REFUSE(c, D4RL_QT_PCM_OUT_OF_BOUNDS);   /* runs past mdat end */
    c = base(1, 8000); c.offset_delta = 16; build(&c); poison(); CHECK(run() == D4RL_QT_PCM_OK); /* last valid */
    c = base(1, 8000); c.offset_delta = -17; REFUSE(c, D4RL_QT_PCM_OUT_OF_BOUNDS);  /* before payload */
    c = base(1, 8000); c.offset_delta = 100000; REFUSE(c, D4RL_QT_PCM_OUT_OF_BOUNDS);
    c = base(1, 8000); c.moov_first = 1; c.offset_delta = -300; REFUSE(c, D4RL_QT_PCM_OUT_OF_BOUNDS); /* into moov */

    /* 4. Truncated lengths. */
    c = base(1, 8000); build(&c); full = len; len = full - 1; refuse(D4RL_QT_PCM_BAD_MOVIE, __LINE__); /* file cut in mdat */
    c = base(1, 8000); c.moov_first = 1; build(&c); len = 300; refuse(D4RL_QT_PCM_BAD_MOVIE, __LINE__); /* cut in moov */
    c = base(1, 8000); c.frames = c.mdhd_duration = c.stsc_spc = c.stsz_count = 117; c.data_frames = 100;
    REFUSE(c, D4RL_QT_PCM_OUT_OF_BOUNDS);                    /* needs 234 bytes, 216 remain after offset */
    c = base(1, 8000); c.frames = c.mdhd_duration = c.stsc_spc = c.stsz_count = 108; c.data_frames = 100;
    build(&c); poison(); CHECK(run() == D4RL_QT_PCM_OK);     /* 216 bytes fit exactly */
    c = base(1, 8000); c.frames = c.mdhd_duration = c.stsc_spc = c.stsz_count = 0x80000001u; c.data_frames = 100;
    REFUSE(c, D4RL_QT_PCM_OUT_OF_BOUNDS);                    /* huge byte count */

    /* 5. Compressed or other descriptions. */
    c = base(1, 8000); c.fmt = "ima4"; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);
    c = base(1, 8000); c.compression_id = 0xFFFE; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);
    c = base(1, 8000); c.bits = 8; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);
    c = base(1, 8000); c.sound_version = 1; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);
    c = base(1, 8000); c.rate |= 0x8000; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);
    c = base(3, 8000); REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);
    c = base(1, 8000); c.stsd_entries = 2; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);
    c = base(1, 8000); c.co64 = 1; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);
    c = base(1, 8000); c.sound_traks = 2; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);
    c = base(1, 8000); c.sound_traks = 0; c.video_trak = 1; REFUSE(c, D4RL_QT_PCM_NO_SOUND_TRACK);

    /* 6. Inconsistent stsc / stsz / stts. */
    c = base(1, 8000); c.stsc_spc = 99; REFUSE(c, D4RL_QT_PCM_INCONSISTENT);
    c = base(1, 8000); c.stsc_first = 2; REFUSE(c, D4RL_QT_PCM_INCONSISTENT);
    c = base(1, 8000); c.stsz_count = 99; REFUSE(c, D4RL_QT_PCM_INCONSISTENT);
    c = base(1, 8000); c.stsz_size = 4; REFUSE(c, D4RL_QT_PCM_INCONSISTENT);
    c = base(1, 8000); c.stts_delta = 2; REFUSE(c, D4RL_QT_PCM_INCONSISTENT);
    c = base(1, 8000); c.timescale = 22050; REFUSE(c, D4RL_QT_PCM_INCONSISTENT);
    c = base(1, 8000); c.mdhd_duration = 99; REFUSE(c, D4RL_QT_PCM_INCONSISTENT);
    c = base(1, 8000); c.frames = 0; c.mdhd_duration = c.stsc_spc = c.stsz_count = 0; REFUSE(c, D4RL_QT_PCM_INCONSISTENT);
    c = base(1, 8000); c.stts_entries = 2; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);
    c = base(1, 8000); c.stsc_entries = 2; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);
    c = base(1, 8000); c.stco_entries = 2; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);
    c = base(1, 8000); c.stsz_size = 0; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);
    c = base(1, 8000); c.stsz_size = 1; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);

    /* R4: nonzero flags in the full-box header must never expose PCM.
     * Apple QTFF: stsd/stts/stsc/stco version (1 byte) + flags (3 bytes).
     * Mutation is applied after build(), before the caller-visible check. */
    c = base(1, 8000); build(&c); CHECK(corrupt_table_flags("stsd")); refuse(D4RL_QT_PCM_UNSUPPORTED, __LINE__);
    c = base(1, 8000); build(&c); CHECK(corrupt_table_flags("stts")); refuse(D4RL_QT_PCM_UNSUPPORTED, __LINE__);
    c = base(1, 8000); build(&c); CHECK(corrupt_table_flags("stsc")); refuse(D4RL_QT_PCM_UNSUPPORTED, __LINE__);
    c = base(1, 8000); build(&c); CHECK(corrupt_table_flags("stco")); refuse(D4RL_QT_PCM_UNSUPPORTED, __LINE__);

    /* R5: mdhd and stsz are FullBoxes; unsupported flags must not
     * expose PCM or advertise sample metadata in the track listing. */
    c = base(1, 8000); build(&c); CHECK(corrupt_table_flags("mdhd")); refuse(D4RL_QT_PCM_UNSUPPORTED, __LINE__);
    c = base(1, 8000); build(&c); CHECK(corrupt_table_flags("stsz")); refuse(D4RL_QT_PCM_UNSUPPORTED, __LINE__);
    {
        struct d4rl_qt_mov_track_info tracks[2];
        size_t track_count = 0;
        c = base(1, 8000); build(&c);
        CHECK(corrupt_table_flags("mdhd"));
        memset(tracks, 0xCD, sizeof(tracks));
        CHECK(d4rl_qt_mov_list_tracks(buf, len, tracks, 2, &track_count) == D4RL_QT_PCM_OK);
        CHECK(track_count == 1);
        CHECK(tracks[0].handler == 0x736F756Eu); /* 'soun' */
        CHECK(tracks[0].has_media == 0);
        CHECK(tracks[0].media_time_scale == 0 && tracks[0].sample_count == 0);

        c = base(1, 8000); build(&c);
        CHECK(corrupt_table_flags("stsz"));
        memset(tracks, 0xCD, sizeof(tracks));
        track_count = 0;
        CHECK(d4rl_qt_mov_list_tracks(buf, len, tracks, 2, &track_count) == D4RL_QT_PCM_OK);
        CHECK(track_count == 1);
        CHECK(tracks[0].handler == 0x736F756Eu);
        CHECK(tracks[0].has_media == 0);
        CHECK(tracks[0].media_time_scale == 0 && tracks[0].sample_count == 0);
    }

    /* R6: mdhd version 1 is supported for track *metadata* (not PCM).
     * Check the full 64-bit time layout and its required trailing fields. */
    {
        struct d4rl_qt_mov_track_info tracks[2];
        size_t n;
        c = base(1, 8000); c.mdhd_v1 = 1; c.moov_first = 1;
        build(&c);
        n = 99; memset(tracks, 0xCD, sizeof(tracks));
        CHECK(d4rl_qt_mov_list_tracks(buf, len, tracks, 2, &n) == D4RL_QT_PCM_OK);
        CHECK(n == 1);
        CHECK(tracks[0].handler == 0x736F756Eu);
        CHECK(tracks[0].has_media == 1);
        CHECK(tracks[0].media_time_scale == 8000);
        CHECK(tracks[0].sample_count == 100);
        refuse(D4RL_QT_PCM_UNSUPPORTED, __LINE__); /* extraction remains v0 */

        c = base(1, 8000); c.mdhd_v1 = 1; build(&c);
        CHECK(corrupt_table_flags("mdhd"));
        n = 99; memset(tracks, 0xCD, sizeof(tracks));
        CHECK(d4rl_qt_mov_list_tracks(buf, len, tracks, 2, &n) == D4RL_QT_PCM_OK);
        CHECK(n == 1);
        CHECK(tracks[0].handler == 0x736F756Eu);
        CHECK(tracks[0].has_media == 0);
        CHECK(tracks[0].media_time_scale == 0 && tracks[0].sample_count == 0);
        refuse(D4RL_QT_PCM_UNSUPPORTED, __LINE__);

        /* Missing 1, 2, 3 or 4 final language/quality bytes: all invalid. */
        for (unsigned missing = 1; missing <= 4; ++missing) {
            c = base(1, 8000); c.mdhd_v1 = 1; c.mdhd_omit_tail = (int)missing;
            build(&c); /* 35..32 bytes instead of the required 36 */
            n = 99; memset(tracks, 0xCD, sizeof(tracks));
            CHECK(d4rl_qt_mov_list_tracks(buf, len, tracks, 2, &n) == D4RL_QT_PCM_OK);
            CHECK(n == 1);
            CHECK(tracks[0].handler == 0x736F756Eu);
            CHECK(tracks[0].has_media == 0);
            CHECK(tracks[0].media_time_scale == 0 && tracks[0].sample_count == 0);
            refuse(D4RL_QT_PCM_UNSUPPORTED, __LINE__);
        }
    }

    /* R3. Data references: positive. */
    c = base(1, 8000); c.ref_type[0] = "url "; accept(&c, 0x74776F73, __LINE__);   /* url  self reference */
    c = base(1, 8000); c.dref_n = 2; c.ref_type[0] = "url "; c.ref_vf[0] = 0; c.dri = 2;
    accept(&c, 0x74776F73, __LINE__);                                            /* index 2 = alis self */
    /* R3. Malformed: reserved bytes, index, missing or incoherent dref. */
    c = base(1, 8000); c.reserved_byte = 1; REFUSE(c, D4RL_QT_PCM_BAD_MOVIE);
    c = base(1, 8000); c.dri = 0; REFUSE(c, D4RL_QT_PCM_BAD_MOVIE);
    c = base(1, 8000); c.dri = 2; REFUSE(c, D4RL_QT_PCM_BAD_MOVIE);              /* 1 entry */
    c = base(1, 8000); c.no_dinf = 1; REFUSE(c, D4RL_QT_PCM_BAD_MOVIE);
    c = base(1, 8000); c.no_dref = 1; REFUSE(c, D4RL_QT_PCM_BAD_MOVIE);
    c = base(1, 8000); c.dref_count = 2; REFUSE(c, D4RL_QT_PCM_BAD_MOVIE);       /* count > entries */
    c = base(1, 8000); c.dref_n = 2; c.dref_count = 1; REFUSE(c, D4RL_QT_PCM_BAD_MOVIE); /* count < entries */
    c = base(1, 8000); c.ref_short = 1; REFUSE(c, D4RL_QT_PCM_BAD_MOVIE);        /* entry without version/flags */
    /* R3. External or unsupported references; stco still points into the local mdat. */
    c = base(1, 8000); c.ref_vf[0] = 0; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);      /* alis external */
    c = base(1, 8000); c.ref_type[0] = "url "; c.ref_vf[0] = 0; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED); /* url external */
    c = base(1, 8000); c.dref_n = 2; c.ref_type[0] = "url "; c.ref_vf[0] = 0; c.dri = 1;
    REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);                                          /* selects external, self exists */
    c = base(1, 8000); c.ref_vf[0] = 0x01000001; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED); /* entry version 1 */
    c = base(1, 8000); c.ref_vf[0] = 0x000003; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);   /* unknown flag */
    c = base(1, 8000); c.ref_type[0] = "rsrc"; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);   /* resource self ref */
    c = base(1, 8000); c.dref_vf = 0x01000000; REFUSE(c, D4RL_QT_PCM_UNSUPPORTED);   /* dref version 1 */

    /* 7. Destination too small. */
    c = base(1, 8000); cap = 199; REFUSE(c, D4RL_QT_PCM_BUFFER_TOO_SMALL);
    build(&c); poison();
    CHECK(d4rl_qt_mov_extract_pcm(buf, len, NULL, 0, &info) == D4RL_QT_PCM_BUFFER_TOO_SMALL && untouched());
    cap = sizeof(out);

    /* Deterministic fuzz: byte flips and truncations under ASan. */
    for (i = 0; i < 20000; ++i) {
        int got; size_t j;
        c = base(2, 44100); c.moov_first = (int)(i & 2); c.video_trak = (int)(i & 4);
        build(&c);
        seed = seed * 1103515245u + 12345u;
        if (i & 1) len = (seed >> 8) % (len + 1);
        else for (j = 0; j < 1 + (i % 4); ++j) { seed = seed * 1103515245u + 12345u; buf[(seed >> 8) % len] = (uint8_t)(seed >> 24); }
        poison();
        got = run();
        if (got == D4RL_QT_PCM_OK) {
            ++accepted;
            CHECK(info.byte_count == (size_t)info.frame_count * info.channels * 2 && info.byte_count <= cap);
        } else {
            CHECK(got < 0 && got >= D4RL_QT_PCM_BUFFER_TOO_SMALL && untouched());
        }
    }
    printf("fuzz accepted=%u/20000\n", accepted);
    printf("checks=%u failures=%u\n", checks, failures);
    if (failures == 0)
        printf("D4RLING-QTMOV02-E1-NATIVE-OK\n");
    return failures > 100 ? 100 : (int)failures;
}
