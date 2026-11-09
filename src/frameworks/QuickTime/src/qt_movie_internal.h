/* SPDX-License-Identifier: GPL-3.0-or-later
 * D4rling QuickTime: private layout behind the opaque Movie handle.
 * Not public ABI; shared only with white-box test witnesses.
 */
#ifndef D4RL_QT_MOVIE_INTERNAL_H
#define D4RL_QT_MOVIE_INTERNAL_H

#include <MacTypes.h>
#include "qt_mov_pcm.h"

struct MovieType {
    TimeScale time_scale;
    TimeValue duration;
    void *pcm;                            /* owned sound samples, or NULL */
    struct d4rl_qt_mov_pcm_info pcm_info; /* meaningful only when pcm != NULL */
};

#endif
