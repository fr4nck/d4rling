/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "qt_timeline.h"
#include <string.h>

static int valid(const struct qt_timeline *t)
{
    return t && t->scale>0 && t->duration>=0 &&
        t->begin>=0 && t->end>=t->begin &&
        t->end<=t->duration &&
        t->position>=t->begin &&
        t->position<=t->end &&
        t->remainder<1000000000ULL;
}

int qt_timeline_init(
    struct qt_timeline *t,int32_t scale,int32_t duration)
{
    if(!t || scale<=0 || duration<0)return -1;
    memset(t,0,sizeof(*t));
    t->scale=scale;
    t->duration=duration;
    t->end=duration;
    return 0;
}

int qt_timeline_segment(
    struct qt_timeline *t,int32_t start,int32_t duration)
{
    if(!valid(t) || start<0 || duration<0 ||
       start>t->duration ||
       duration>t->duration-start)return -1;

    t->begin=start;
    t->end=start+duration;
    t->position=start;
    t->remainder=0;
    t->running=0;
    return 0;
}

int qt_timeline_start(struct qt_timeline *t)
{
    if(!valid(t))return -1;
    if(t->begin==t->end){
        t->running=0;
        return 0;
    }
    if(t->position==t->end){
        t->position=t->begin;
        t->remainder=0;
    }
    t->running=1;
    return 0;
}

int qt_timeline_stop(struct qt_timeline *t)
{
    if(!valid(t))return -1;
    t->running=0;
    return 0;
}

/* Elapsed nanoseconds supplied by caller.
 * This does not drive an audio device.
 * Split seconds and fractions to avoid overflow.
 */
int qt_timeline_advance(
    struct qt_timeline *t,uint64_t ns)
{
    if(!valid(t))return -1;
    if(!t->running)return 0;

    uint64_t span=(uint64_t)(t->end-t->begin);
    if(!span){t->running=0;return 0;}

    uint64_t sec=ns/1000000000ULL;
    uint64_t frac=ns%1000000000ULL;
    uint64_t scale=(uint64_t)t->scale;
    uint64_t part=frac*scale+t->remainder;
    uint64_t ticks=part/1000000000ULL;
    uint64_t remainder=part%1000000000ULL;

    if(t->looping){
        uint64_t pos=(uint64_t)(t->position-t->begin);
        uint64_t whole=((sec%span)*(scale%span))%span;
        uint64_t next=(pos+whole+(ticks%span))%span;
        t->position=t->begin+(int32_t)next;
        t->remainder=remainder;
        return 0;
    }

    uint64_t left=(uint64_t)(t->end-t->position);

    if(sec>left/scale){
        t->position=t->end;
        t->running=0;
        t->remainder=0;
        return 0;
    }

    ticks+=sec*scale;

    if(ticks>=left){
        t->position=t->end;
        t->running=0;
        t->remainder=0;
    }else{
        t->position+=(int32_t)ticks;
        t->remainder=remainder;
    }
    return 0;
}

int qt_timeline_done(const struct qt_timeline *t)
{
    if(!valid(t))return -1;
    return t->position==t->end;
}
