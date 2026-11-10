/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "qt_mov_pcm.h"
#include "qt_mov_probe.h"

#include <string.h>

struct span {
    const uint8_t *p;
    size_t n;
};

static uint16_t rd16(const uint8_t *p)
{
    return (uint16_t)((unsigned)p[0] << 8 | p[1]);
}

static uint32_t rd32(const uint8_t *p)
{
    return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 |
           (uint32_t)p[2] << 8 | (uint32_t)p[3];
}

static uint64_t rd64(const uint8_t *p)
{
    return (uint64_t)rd32(p) << 32 | rd32(p + 4);
}

/* Atom at s.p + off: type, payload and total length, all inside s. */
static int read_atom(struct span s, size_t off, const uint8_t **type,
                     struct span *body, size_t *total)
{
    size_t remaining = s.n - off, header = 8;
    uint64_t length;

    if (remaining < 8)
        return D4RL_QT_PCM_BAD_MOVIE;
    length = rd32(s.p + off);
    if (length == 1) {
        if (remaining < 16)
            return D4RL_QT_PCM_BAD_MOVIE;
        length = rd64(s.p + off + 8);
        header = 16;
    } else if (length == 0) {
        length = remaining;
    }
    if (length < header || length > remaining)
        return D4RL_QT_PCM_BAD_MOVIE;
    *type = s.p + off + 4;
    body->p = s.p + off + header;
    body->n = (size_t)length - header;
    *total = (size_t)length;
    return D4RL_QT_PCM_OK;
}

/* Count children of a type; *out receives the last one. Validates all. */
static int find_children(struct span s, const char *type, struct span *out,
                         unsigned *count)
{
    size_t off = 0;
    *count = 0;
    while (off < s.n) {
        const uint8_t *t;
        struct span body;
        size_t total;
        int status = read_atom(s, off, &t, &body, &total);
        if (status != D4RL_QT_PCM_OK)
            return status;
        if (memcmp(t, type, 4) == 0) {
            if (out)
                *out = body;
            ++*count;
        }
        off += total;
    }
    return D4RL_QT_PCM_OK;
}

/* Exactly one child: missing is a bad movie, duplicates are unsupported. */
static int one_child(struct span s, const char *type, struct span *out)
{
    unsigned count;
    int status = find_children(s, type, out, &count);
    if (status != D4RL_QT_PCM_OK)
        return status;
    if (count == 0)
        return D4RL_QT_PCM_BAD_MOVIE;
    return count == 1 ? D4RL_QT_PCM_OK : D4RL_QT_PCM_UNSUPPORTED;
}

/* Full atom with version 0 and a 32-bit entry count after flags. */
static int table(struct span s, size_t entry_size, uint32_t *entries)
{
    if (s.n < 8)
        return D4RL_QT_PCM_BAD_MOVIE;
    if (rd32(s.p) != 0)
        return D4RL_QT_PCM_UNSUPPORTED;
    *entries = rd32(s.p + 4);
    if (entry_size && *entries != 1)
        return D4RL_QT_PCM_UNSUPPORTED;
    if (entry_size && s.n - 8 < entry_size)
        return D4RL_QT_PCM_BAD_MOVIE;
    return D4RL_QT_PCM_OK;
}

#define TRY(expr) do { int s_ = (expr); if (s_ != D4RL_QT_PCM_OK) return s_; } while (0)

/* The 1-based stsd data reference index must select a self-contained entry
 * of minf/dinf/dref (QTFF, Data Reference Atoms: self reference flag 0x0001,
 * media data in the same file as the movie atom). External aliases, URLs and
 * resources are never followed; their samples are not copied. */
static int check_local_reference(struct span minf, uint16_t index)
{
    struct span dinf, dref, entries, body;
    const uint8_t *type, *selected = NULL;
    uint32_t count, n = 0, version_flags = 0;
    size_t off = 0, total;

    if (index == 0)
        return D4RL_QT_PCM_BAD_MOVIE;
    TRY(one_child(minf, "dinf", &dinf));
    TRY(one_child(dinf, "dref", &dref));
    if (dref.n < 8)
        return D4RL_QT_PCM_BAD_MOVIE;
    if (rd32(dref.p) != 0)
        return D4RL_QT_PCM_UNSUPPORTED;
    count = rd32(dref.p + 4);
    entries.p = dref.p + 8;
    entries.n = dref.n - 8;
    while (off < entries.n) {
        TRY(read_atom(entries, off, &type, &body, &total));
        if (body.n < 4)
            return D4RL_QT_PCM_BAD_MOVIE;
        if (++n == index) {
            selected = type;
            version_flags = rd32(body.p);
        }
        off += total;
    }
    if (n != count || !selected)
        return D4RL_QT_PCM_BAD_MOVIE;
    if (version_flags != 0x000001)
        return D4RL_QT_PCM_UNSUPPORTED;
    if (memcmp(selected, "alis", 4) != 0 && memcmp(selected, "url ", 4) != 0)
        return D4RL_QT_PCM_UNSUPPORTED;
    return D4RL_QT_PCM_OK;
}

static int find_sound_media(struct span moov, struct span *mdia)
{
    size_t off = 0;
    unsigned sound = 0;
    while (off < moov.n) {
        const uint8_t *t;
        struct span body, media, hdlr;
        size_t total;
        TRY(read_atom(moov, off, &t, &body, &total));
        off += total;
        if (memcmp(t, "trak", 4) != 0)
            continue;
        TRY(one_child(body, "mdia", &media));
        TRY(one_child(media, "hdlr", &hdlr));
        if (hdlr.n < 12)
            return D4RL_QT_PCM_BAD_MOVIE;
        if (memcmp(hdlr.p + 8, "soun", 4) == 0) {
            *mdia = media;
            ++sound;
        }
    }
    if (sound == 0)
        return D4RL_QT_PCM_NO_SOUND_TRACK;
    return sound == 1 ? D4RL_QT_PCM_OK : D4RL_QT_PCM_UNSUPPORTED;
}

/* Is [offset, offset + bytes) inside the payload of one top-level mdat? */
static int inside_mdat(struct span file, uint64_t offset, uint64_t bytes)
{
    size_t off = 0;
    while (off < file.n) {
        const uint8_t *t;
        struct span body;
        size_t total;
        TRY(read_atom(file, off, &t, &body, &total));
        if (memcmp(t, "mdat", 4) == 0) {
            uint64_t start = (uint64_t)(body.p - file.p);
            if (offset >= start && offset - start <= body.n &&
                bytes <= body.n - (offset - start))
                return D4RL_QT_PCM_OK;
        }
        off += total;
    }
    return D4RL_QT_PCM_OUT_OF_BOUNDS;
}

static int locate(const void *data, size_t length,
                  struct d4rl_qt_mov_pcm_info *info, size_t *where)
{
    struct span file = { data, length }, moov, mdia, mdhd, minf, stbl;
    struct span stsd, entries, entry, stts, stsc, stsz, stco;
    struct d4rl_qt_mov_header header;
    struct d4rl_qt_mov_pcm_info found;
    const uint8_t *format;
    size_t total;
    unsigned co64;
    uint32_t count, timescale, duration, rate, frames, frame_bytes;
    uint64_t offset, bytes;

    if (d4rl_qt_mov_probe(data, length, &header) != D4RL_QT_MOV_OK)
        return D4RL_QT_PCM_BAD_MOVIE;
    TRY(one_child(file, "moov", &moov));
    TRY(find_sound_media(moov, &mdia));

    TRY(one_child(mdia, "mdhd", &mdhd));
    if (mdhd.n < 20)
        return D4RL_QT_PCM_BAD_MOVIE;
    if (rd32(mdhd.p) != 0)
        return D4RL_QT_PCM_UNSUPPORTED;
    timescale = rd32(mdhd.p + 12);
    duration = rd32(mdhd.p + 16);
    TRY(one_child(mdia, "minf", &minf));
    TRY(one_child(minf, "stbl", &stbl));
    TRY(find_children(stbl, "co64", NULL, &co64));
    if (co64)
        return D4RL_QT_PCM_UNSUPPORTED;

    /* Sound description version 0: 36-byte entry (QTFF, Sound Media). */
    TRY(one_child(stbl, "stsd", &stsd));
    TRY(table(stsd, 0, &count));
    if (count != 1)
        return D4RL_QT_PCM_UNSUPPORTED;
    entries.p = stsd.p + 8;
    entries.n = stsd.n - 8;
    TRY(read_atom(entries, 0, &format, &entry, &total));
    if (total != entries.n || entry.n < 28)
        return D4RL_QT_PCM_BAD_MOVIE;
    if (entry.p[0] | entry.p[1] | entry.p[2] | entry.p[3] | entry.p[4] | entry.p[5])
        return D4RL_QT_PCM_BAD_MOVIE; /* six reserved bytes must be 0 */
    if (memcmp(format, "twos", 4) != 0 && memcmp(format, "sowt", 4) != 0)
        return D4RL_QT_PCM_UNSUPPORTED;
    found.format = rd32(format);
    found.channels = rd16(entry.p + 16);
    found.bits_per_sample = rd16(entry.p + 18);
    rate = rd32(entry.p + 24);
    if (rd16(entry.p + 8) != 0 || rd16(entry.p + 20) != 0 ||
        found.bits_per_sample != 16 || found.channels < 1 ||
        found.channels > 2 || (rate & 0xFFFF) != 0 || rate == 0)
        return D4RL_QT_PCM_UNSUPPORTED;
    found.sample_rate = rate >> 16;
    frame_bytes = (uint32_t)found.channels * 2;
    TRY(check_local_reference(minf, rd16(entry.p + 6)));

    TRY(one_child(stbl, "stts", &stts));
    TRY(table(stts, 8, &count));
    frames = rd32(stts.p + 8);
    TRY(one_child(stbl, "stsc", &stsc));
    TRY(table(stsc, 12, &count));
    TRY(one_child(stbl, "stsz", &stsz));
    if (stsz.n < 12)
        return D4RL_QT_PCM_BAD_MOVIE;
    if (rd32(stsz.p) != 0 || rd32(stsz.p + 4) == 0 || rd32(stsz.p + 4) == 1)
        return D4RL_QT_PCM_UNSUPPORTED;
    TRY(one_child(stbl, "stco", &stco));
    TRY(table(stco, 4, &count));

    if (frames == 0 || rd32(stts.p + 12) != 1 ||
        timescale != found.sample_rate || duration != frames ||
        rd32(stsc.p + 8) != 1 || rd32(stsc.p + 12) != frames ||
        rd32(stsc.p + 16) != 1 ||
        rd32(stsz.p + 4) != frame_bytes || rd32(stsz.p + 8) != frames)
        return D4RL_QT_PCM_INCONSISTENT;

    offset = rd32(stco.p + 8);
    bytes = (uint64_t)frames * frame_bytes;
    TRY(inside_mdat(file, offset, bytes));
    found.frame_count = frames;
    found.byte_count = (size_t)bytes;
    *info = found;
    *where = (size_t)offset;
    return D4RL_QT_PCM_OK;
}

int d4rl_qt_mov_find_pcm(const void *data, size_t length,
                         struct d4rl_qt_mov_pcm_info *info, size_t *offset)
{
    struct d4rl_qt_mov_pcm_info found;
    size_t where;

    if (!data || !info || !offset)
        return D4RL_QT_PCM_INVALID_ARGUMENT;
    TRY(locate(data, length, &found, &where));
    *info = found;
    *offset = where;
    return D4RL_QT_PCM_OK;
}

int d4rl_qt_mov_extract_pcm(const void *data, size_t length,
                            void *pcm, size_t capacity,
                            struct d4rl_qt_mov_pcm_info *info)
{
    struct d4rl_qt_mov_pcm_info found;
    size_t where;

    if (!data || !info || (!pcm && capacity))
        return D4RL_QT_PCM_INVALID_ARGUMENT;
    TRY(locate(data, length, &found, &where));
    if (found.byte_count > capacity)
        return D4RL_QT_PCM_BUFFER_TOO_SMALL;
    memcpy(pcm, (const uint8_t *)data + where, found.byte_count);
    *info = found;
    return D4RL_QT_PCM_OK;
}

static void describe_track(struct span trak, struct d4rl_qt_mov_track_info *info)
{
    struct span mdia, mdhd, hdlr, minf, stbl, stsz;
    uint32_t scale, size, samples;
    size_t table;

    memset(info, 0, sizeof(*info));
    if (one_child(trak, "mdia", &mdia) != D4RL_QT_PCM_OK ||
        one_child(mdia, "hdlr", &hdlr) != D4RL_QT_PCM_OK || hdlr.n < 12)
        return;
    info->handler = rd32(hdlr.p + 8);
    if (one_child(mdia, "mdhd", &mdhd) != D4RL_QT_PCM_OK)
        return;
    if (mdhd.n >= 20 && rd32(mdhd.p) == 0)
        scale = rd32(mdhd.p + 12);
    else if (mdhd.n >= 36 && rd32(mdhd.p) == 0x01000000U)
        scale = rd32(mdhd.p + 20);
    else
        return;
    if (scale == 0 || scale > INT32_MAX ||
        one_child(mdia, "minf", &minf) != D4RL_QT_PCM_OK ||
        one_child(minf, "stbl", &stbl) != D4RL_QT_PCM_OK ||
        one_child(stbl, "stsz", &stsz) != D4RL_QT_PCM_OK)
        return;
    /* stsz (QTFF, Sample Size Atoms): version and flags 0, sample size,
     * number of entries, then a 4-byte size per sample only when the sample
     * size is 0. Compared by division: no overflow, no table entry read. */
    if (stsz.n < 12 || rd32(stsz.p) != 0)
        return;
    size = rd32(stsz.p + 4);
    samples = rd32(stsz.p + 8);
    table = stsz.n - 12;
    if (size != 0 ? table != 0 : (table % 4 != 0 || table / 4 != samples))
        return;
    if (samples > INT32_MAX)
        return;
    info->media_time_scale = scale;
    info->sample_count = samples;
    info->has_media = 1;
}

/* Walk moov children; describe traks only when tracks is not NULL. */
static int walk_tracks(struct span moov, struct d4rl_qt_mov_track_info *tracks,
                       size_t *count)
{
    size_t off = 0, n = 0;
    while (off < moov.n) {
        const uint8_t *t;
        struct span body;
        size_t total;
        TRY(read_atom(moov, off, &t, &body, &total));
        off += total;
        if (memcmp(t, "trak", 4) != 0)
            continue;
        if (tracks)
            describe_track(body, &tracks[n]);
        ++n;
    }
    *count = n;
    return D4RL_QT_PCM_OK;
}

int d4rl_qt_mov_list_tracks(const void *data, size_t length,
                            struct d4rl_qt_mov_track_info *tracks,
                            size_t capacity, size_t *count)
{
    struct span file = { data, length }, moov;
    struct d4rl_qt_mov_header header;
    size_t n;

    if (!data || !count || (!tracks && capacity))
        return D4RL_QT_PCM_INVALID_ARGUMENT;
    if (d4rl_qt_mov_probe(data, length, &header) != D4RL_QT_MOV_OK)
        return D4RL_QT_PCM_BAD_MOVIE;
    TRY(one_child(file, "moov", &moov));
    TRY(walk_tracks(moov, NULL, &n));
    if (tracks) {
        if (capacity < n)
            return D4RL_QT_PCM_BUFFER_TOO_SMALL;
        TRY(walk_tracks(moov, tracks, &n));
    }
    *count = n;
    return D4RL_QT_PCM_OK;
}
