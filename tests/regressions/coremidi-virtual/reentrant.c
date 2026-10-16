/*
 * Reentrant CoreMIDI virtual delivery regression.
 * A callback may disconnect, reconnect, or destroy later recipients.
 * This does not test disposal concurrently from another thread.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <CoreMIDI/MIDIServices.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

typedef struct {
    MIDIPortRef second;
    MIDIEndpointRef source;
    unsigned calls;
    int operation;
} FirstState;

typedef struct {
    unsigned calls;
    void *lastConnection;
} SecondState;

static void first_callback(const MIDIPacketList *packets, void *context,
                           void *connection)
{
    FirstState *s = (FirstState *)context;
    assert(packets && packets->numPackets == 1);
    assert(connection == (void *)(uintptr_t)0x1111);
    ++s->calls;
    if (s->operation == 1) {
        assert(MIDIPortDisconnectSource(s->second, s->source) == noErr);
    } else if (s->operation == 2) {
        /* Reuses a freed slot: a stale snapshot must not call this anew. */
        assert(MIDIPortDisconnectSource(s->second, s->source) == noErr);
        assert(MIDIPortConnectSource(s->second, s->source,
                                     (void *)(uintptr_t)0x3333) == noErr);
    } else if (s->operation == 3) {
        assert(MIDIPortDispose(s->second) == noErr);
    } else if (s->operation == 4) {
        assert(MIDIEndpointDispose(s->source) == noErr);
    }
}

static void second_callback(const MIDIPacketList *packets, void *context,
                            void *connection)
{
    SecondState *s = (SecondState *)context;
    assert(packets && packets->numPackets == 1);
    ++s->calls;
    s->lastConnection = connection;
}

int main(void)
{
    MIDIClientRef client = 0;
    MIDIPortRef first = 0, second = 0;
    MIDIEndpointRef source = 0;
    FirstState a = {0};
    SecondState b = {0};
    const Byte note[3] = {0x90, 60, 100};
    union { long double align; Byte bytes[64]; } storage;
    MIDIPacketList *list = (MIDIPacketList *)storage.bytes;
    MIDIPacket *packet = MIDIPacketListInit(list);

    assert(packet != NULL);
    assert(MIDIPacketListAdd(list, sizeof(storage.bytes), packet,
                             0, sizeof(note), note) != NULL);
    assert(MIDIClientCreate(NULL, NULL, NULL, &client) == noErr);
    assert(MIDISourceCreate(client, NULL, &source) == noErr);
    a.source = source;
    assert(MIDIInputPortCreate(client, NULL, first_callback, &a, &first) == noErr);
    assert(MIDIInputPortCreate(client, NULL, second_callback, &b, &second) == noErr);
    a.second = second;
    assert(MIDIPortConnectSource(first, source,
           (void *)(uintptr_t)0x1111) == noErr);
    assert(MIDIPortConnectSource(second, source,
           (void *)(uintptr_t)0x2222) == noErr);

    /* First callback disconnects the second; no stale callback follows. */
    a.operation = 1;
    assert(MIDIReceived(source, list) == noErr);
    assert(a.calls == 1 && b.calls == 0);

    assert(MIDIPortConnectSource(second, source,
           (void *)(uintptr_t)0x2222) == noErr);
    /* Disconnect and reconnect to SAME slot from inside first callback.
       The new connection cannot be invoked by the old delivery snapshot. */
    a.operation = 2;
    assert(MIDIReceived(source, list) == noErr);
    assert(a.calls == 2 && b.calls == 0);

    a.operation = 0;
    assert(MIDIReceived(source, list) == noErr);
    assert(a.calls == 3 && b.calls == 1);
    assert(b.lastConnection == (void *)(uintptr_t)0x3333);

    /* Destruction of second port during first callback suppresses dispatch. */
    a.operation = 3;
    assert(MIDIReceived(source, list) == noErr);
    assert(a.calls == 4 && b.calls == 1);
    assert(MIDIPortDispose(second) == kMIDIInvalidPort);

    /* Disposal of source inside callback stops subsequent dispatch. */
    assert(MIDIInputPortCreate(client, NULL, second_callback, &b, &second) == noErr);
    assert(MIDIPortConnectSource(second, source,
           (void *)(uintptr_t)0x4444) == noErr);
    a.second = second;
    a.operation = 4;
    assert(MIDIReceived(source, list) == noErr);
    assert(a.calls == 5 && b.calls == 1);
    assert(MIDIReceived(source, list) == kMIDIUnknownEndpoint);

    assert(MIDIClientDispose(client) == noErr);
    puts("CoreMIDI reentrant: disconnect, reconnect and disposal PASS");
    return 0;
}
