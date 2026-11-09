/* SPDX-License-Identifier: GPL-3.0-or-later
 * D4rling QuickTime: private layout behind the opaque Movie handle.
 * Not public ABI; shared only with white-box test witnesses.
 */
#ifndef D4RL_QT_MOVIE_INTERNAL_H
#define D4RL_QT_MOVIE_INTERNAL_H

#include <MacTypes.h>
#include "qt_mov_pcm.h"

struct TrackType {
    OSType handler;          /* hdlr component subtype, 0 if unknown */
};

struct MediaType {
    TimeScale time_scale;
    SInt32 sample_count;
};

/* Track is &track_handle and Media is &media_handle: stable for the life of
 * the movie, located by address comparison, never dereferenced when unknown. */
struct D4RLTrackStorage {
    struct TrackType *track_handle;
    struct MediaType *media_handle; /* NULL when the track has no media */
    struct TrackType track;
    struct MediaType media;
};

struct MovieType {
    TimeScale time_scale;
    TimeValue duration;
    void *pcm;                            /* owned sound samples, or NULL */
    struct d4rl_qt_mov_pcm_info pcm_info; /* meaningful only when pcm != NULL */
    struct D4RLTrackStorage *tracks;      /* owned, container order */
    SInt32 track_count;
    Boolean tracks_unavailable;           /* moov children could not be walked */
};

#endif
