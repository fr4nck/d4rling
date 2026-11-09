/* SPDX-License-Identifier: GPL-3.0-or-later
 * D4rling QuickTime: private, bounded extraction of one uncompressed 16-bit
 * PCM sound track from a complete in-memory MOV buffer (QT-MOV-02 / E1).
 * This is not the public Apple QuickTime ABI.
 */
#ifndef D4RL_QT_MOV_PCM_H
#define D4RL_QT_MOV_PCM_H

#include <stddef.h>
#include <stdint.h>

enum d4rl_qt_mov_pcm_status {
    D4RL_QT_PCM_OK = 0,
    D4RL_QT_PCM_INVALID_ARGUMENT = -1,
    D4RL_QT_PCM_BAD_MOVIE = -2,      /* invalid, truncated or missing atoms */
    D4RL_QT_PCM_NO_SOUND_TRACK = -3,
    D4RL_QT_PCM_UNSUPPORTED = -4,    /* valid but outside the supported subset */
    D4RL_QT_PCM_INCONSISTENT = -5,   /* description and sample tables disagree */
    D4RL_QT_PCM_OUT_OF_BOUNDS = -6,  /* samples not inside one mdat payload */
    D4RL_QT_PCM_BUFFER_TOO_SMALL = -7
};

struct d4rl_qt_mov_pcm_info {
    uint32_t format;          /* 'twos' (big-endian) or 'sowt' (little-endian) */
    uint32_t sample_rate;     /* Hz, integer part of the 16.16 description rate */
    uint16_t channels;        /* 1 or 2, interleaved */
    uint16_t bits_per_sample; /* 16 */
    uint32_t frame_count;     /* media samples, one sample frame each */
    size_t byte_count;        /* bytes copied to the destination */
};

/*
 * Locate the raw sample bytes of the only 'soun' track without copying them.
 * On success, *info describes them and *offset is their byte offset in data;
 * offset + info->byte_count never exceeds length. Outputs change only on
 * success. Same subset and refusals as d4rl_qt_mov_extract_pcm.
 */
__attribute__((visibility("hidden")))
int d4rl_qt_mov_find_pcm(const void *data, size_t length,
                         struct d4rl_qt_mov_pcm_info *info, size_t *offset);

/*
 * Copy the raw sample bytes of the only 'soun' track. Supported subset:
 * stsd version 0 with one 'twos'/'sowt' 16-bit entry (zero reserved bytes,
 * data reference index selecting a version 0 'alis' or 'url ' self reference
 * in minf/dinf/dref; external references are refused), sound version 0,
 * compression ID 0, 1-2 channels, integer rate equal to the mdhd time scale),
 * one stts entry of duration 1, one stsc entry covering every sample,
 * constant stsz size equal to channels * 2, one stco chunk inside one mdat.
 * Everything else is refused. pcm and info are changed only on success.
 */
__attribute__((visibility("hidden")))
int d4rl_qt_mov_extract_pcm(const void *data, size_t length,
                            void *pcm, size_t capacity,
                            struct d4rl_qt_mov_pcm_info *info);

#endif
