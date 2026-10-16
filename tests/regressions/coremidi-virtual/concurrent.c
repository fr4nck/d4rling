/*
 * CoreMIDI virtual callback lifetime gate regression.
 * Worker callback is deliberately blocked while a second thread attempts
 * teardown. No kernel ALSA support is needed. Not a realtime benchmark.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#define _POSIX_C_SOURCE 200809L
#include <CoreMIDI/MIDIServices.h>
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>

enum Teardown { DISCONNECT, DISPOSE_PORT, DISPOSE_SOURCE, DISPOSE_CLIENT,
                DISPOSE_DESTINATION };

typedef struct {
    pthread_mutex_t mutex;
    pthread_cond_t cond;
    int entered, release, callback_active, teardown_started, teardown_done;
    int teardown_while_active;
    unsigned callbacks;
    enum Teardown action;
    MIDIClientRef client;
    MIDIPortRef port;
    MIDIEndpointRef endpoint;
    int destination_mode;
    OSStatus dispatch_status, teardown_status;
} Scenario;

static void locked_callback(const MIDIPacketList *packets, void *refCon,
                            void *connectionRefCon)
{
    Scenario *s = (Scenario *)refCon;
    assert(packets && packets->numPackets == 1);
    assert(connectionRefCon ==
           (s->destination_mode ? NULL : (void *)(uintptr_t)0x1357));
    pthread_mutex_lock(&s->mutex);
    ++s->callbacks;
    s->callback_active = 1;
    s->entered = 1;
    pthread_cond_broadcast(&s->cond);
    while (!s->release)
        assert(pthread_cond_wait(&s->cond, &s->mutex) == 0);
    s->callback_active = 0;
    pthread_mutex_unlock(&s->mutex);
}

static void *dispatcher(void *opaque)
{
    Scenario *s = (Scenario *)opaque;
    const Byte note[] = {0x90, 60, 100};
    union { long double align; Byte bytes[64]; } storage;
    MIDIPacketList *list = (MIDIPacketList *)storage.bytes;
    MIDIPacket *packet = MIDIPacketListInit(list);
    assert(packet);
    assert(MIDIPacketListAdd(list, sizeof(storage.bytes), packet, 0,
                             sizeof(note), note));
    if (s->destination_mode)
        s->dispatch_status = MIDISend(s->port, s->endpoint, list);
    else
        s->dispatch_status = MIDIReceived(s->endpoint, list);
    return NULL;
}

static void *teardown(void *opaque)
{
    Scenario *s = (Scenario *)opaque;
    pthread_mutex_lock(&s->mutex);
    s->teardown_started = 1;
    pthread_cond_broadcast(&s->cond);
    pthread_mutex_unlock(&s->mutex);
    switch (s->action) {
    case DISCONNECT:
        s->teardown_status = MIDIPortDisconnectSource(s->port, s->endpoint);
        break;
    case DISPOSE_PORT:
        s->teardown_status = MIDIPortDispose(s->port);
        break;
    case DISPOSE_SOURCE:
    case DISPOSE_DESTINATION:
        s->teardown_status = MIDIEndpointDispose(s->endpoint);
        break;
    case DISPOSE_CLIENT:
        s->teardown_status = MIDIClientDispose(s->client);
        break;
    }
    pthread_mutex_lock(&s->mutex);
    s->teardown_while_active = s->callback_active;
    s->teardown_done = 1;
    pthread_cond_broadcast(&s->cond);
    pthread_mutex_unlock(&s->mutex);
    return NULL;
}

static void deadline(struct timespec *ts, unsigned milliseconds)
{
    assert(clock_gettime(CLOCK_REALTIME, ts) == 0);
    ts->tv_sec += milliseconds / 1000;
    ts->tv_nsec += (long)(milliseconds % 1000) * 1000000L;
    if (ts->tv_nsec >= 1000000000L) {
        ++ts->tv_sec;
        ts->tv_nsec -= 1000000000L;
    }
}

static void await(Scenario *s, const int *flag)
{
    struct timespec limit;
    deadline(&limit, 5000);
    while (!*flag) {
        int rc = pthread_cond_timedwait(&s->cond, &s->mutex, &limit);
        assert(rc == 0);
    }
}

static void run_case(enum Teardown action)
{
    Scenario s = {
        .mutex = PTHREAD_MUTEX_INITIALIZER,
        .cond = PTHREAD_COND_INITIALIZER,
        .action = action,
        .destination_mode = (action == DISPOSE_DESTINATION)
    };
    pthread_t sender, disposer;
    struct timespec limit;
    int ended_early;

    assert(MIDIClientCreate(NULL, NULL, NULL, &s.client) == noErr);
    if (s.destination_mode) {
        assert(MIDIOutputPortCreate(s.client, NULL, &s.port) == noErr);
        assert(MIDIDestinationCreate(s.client, NULL, locked_callback, &s,
                                     &s.endpoint) == noErr);
    } else {
        assert(MIDIInputPortCreate(s.client, NULL, locked_callback, &s,
                                   &s.port) == noErr);
        assert(MIDISourceCreate(s.client, NULL, &s.endpoint) == noErr);
        assert(MIDIPortConnectSource(s.port, s.endpoint,
                                     (void *)(uintptr_t)0x1357) == noErr);
    }

    assert(pthread_create(&sender, NULL, dispatcher, &s) == 0);
    pthread_mutex_lock(&s.mutex);
    await(&s, &s.entered);
    pthread_mutex_unlock(&s.mutex);

    assert(pthread_create(&disposer, NULL, teardown, &s) == 0);
    pthread_mutex_lock(&s.mutex);
    await(&s, &s.teardown_started);

    /* Teardown must not return until the blocked callback is released.
       The fixed wait makes the race reproducible on host schedulers, while
       the callback/teardown handshakes are otherwise deterministic. */
    deadline(&limit, 120);
    while (!s.teardown_done) {
        int rc = pthread_cond_timedwait(&s.cond, &s.mutex, &limit);
        if (rc == ETIMEDOUT) break;
        assert(rc == 0);
    }
    ended_early = s.teardown_done;
    s.release = 1;
    pthread_cond_broadcast(&s.cond);
    pthread_mutex_unlock(&s.mutex);

    assert(pthread_join(sender, NULL) == 0);
    assert(pthread_join(disposer, NULL) == 0);
    assert(!ended_early);
    assert(!s.teardown_while_active);
    assert(s.dispatch_status == noErr);
    assert(s.teardown_status == noErr);
    assert(s.callbacks == 1);

    if (action != DISPOSE_CLIENT)
        assert(MIDIClientDispose(s.client) == noErr);
    assert(pthread_cond_destroy(&s.cond) == 0);
    assert(pthread_mutex_destroy(&s.mutex) == 0);
}

int main(void)
{
    run_case(DISCONNECT);
    run_case(DISPOSE_PORT);
    run_case(DISPOSE_SOURCE);
    run_case(DISPOSE_CLIENT);
    run_case(DISPOSE_DESTINATION);
    puts("CoreMIDI concurrent: callback teardown serialization PASS");
    return 0;
}
