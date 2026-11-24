/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef D4RL_QT_TIMELINE_H
#define D4RL_QT_TIMELINE_H
#include <stdint.h>

struct qt_timeline {
    int32_t scale;
    int32_t duration;
    int32_t begin;
    int32_t end;
    int32_t position;
    uint64_t remainder;
    int running;
    int looping;
};

int qt_timeline_init(
    struct qt_timeline *,int32_t,int32_t);
int qt_timeline_segment(
    struct qt_timeline *,int32_t,int32_t);
int qt_timeline_start(struct qt_timeline *);
int qt_timeline_stop(struct qt_timeline *);
int qt_timeline_advance(
    struct qt_timeline *,uint64_t);
int qt_timeline_done(const struct qt_timeline *);

#endif
