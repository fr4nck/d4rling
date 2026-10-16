#include <CoreMIDI/MIDIServices.h>
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

typedef struct { int calls; unsigned noteOn; unsigned noteOff; void *lastConnection; } Received;
static void receive(const MIDIPacketList *list, void *opaque, void *conn)
{
    Received *r = (Received *)opaque;
    const MIDIPacket *p = &list->packet[0];
    unsigned i;
    r->calls++;
    r->lastConnection = conn;
    for (i = 0; i < list->numPackets; ++i) {
        assert(p->length == 3);
        if (p->data[0] == 0x90 && p->data[1] == 60 && p->data[2] == 100) r->noteOn++;
        if (p->data[0] == 0x80 && p->data[1] == 60 && p->data[2] == 0) r->noteOff++;
        p = MIDIPacketNext(p);
    }
}
int main(void)
{
    MIDIClientRef client = 0;
    MIDIPortRef input = 0, output = 0;
    MIDIEndpointRef source = 0, destination = 0;
    Received in = {0}, out = {0};
    const Byte on[] = {0x90, 60, 100}, off[] = {0x80, 60, 0};
    union { long double align; unsigned char bytes[128]; } storage;
    MIDIPacketList *list = (MIDIPacketList *)storage.bytes;
    MIDIPacket *packet;
    assert(MIDIClientCreate(NULL, NULL, NULL, NULL) == paramErr);
    assert(MIDIClientCreate(NULL, NULL, NULL, &client) == noErr && client);
    assert(MIDIInputPortCreate(client, NULL, receive, &in, &input) == noErr);
    assert(MIDIOutputPortCreate(client, NULL, &output) == noErr);
    assert(MIDISourceCreate(client, NULL, &source) == noErr);
    assert(MIDIDestinationCreate(client, NULL, receive, &out, &destination) == noErr);
    assert(MIDIGetNumberOfSources() == 1 && MIDIGetSource(0) == source);
    assert(MIDIGetNumberOfDestinations() == 1 && MIDIGetDestination(0) == destination);
    assert(MIDIGetSource(1) == 0 && MIDIGetDestination(1) == 0);
    assert(MIDIPortConnectSource(input, source, (void *)(uintptr_t)0x1234) == noErr);
    packet = MIDIPacketListInit(list);
    assert(packet != NULL && list->numPackets == 0);
    assert(MIDIPacketListAdd(list, 8, packet, 1, sizeof(on), on) == NULL);
    packet = MIDIPacketListAdd(list, sizeof(storage.bytes), packet, 1, sizeof(on), on);
    assert(packet != NULL);
    assert(MIDIPacketListAdd(list, sizeof(storage.bytes), packet, 2, sizeof(off), off) != NULL);
    assert(list->numPackets == 2);
    /* Without ALSA configured, foreign endpoint IDs never silently succeed. */
    assert(MIDISend(output, 0xa0000101u, list) == kMIDIUnknownEndpoint);
    assert(MIDIReceived(source, list) == noErr);
    assert(in.calls == 1 && in.noteOn == 1 && in.noteOff == 1);
    assert(in.lastConnection == (void *)(uintptr_t)0x1234);
    assert(MIDISend(output, destination, list) == noErr);
    assert(out.calls == 1 && out.noteOn == 1 && out.noteOff == 1 && !out.lastConnection);
    assert(MIDIPortDisconnectSource(input, source) == noErr);
    assert(MIDIReceived(source, list) == noErr && in.calls == 1);
    assert(MIDIEndpointDispose(source) == noErr);
    assert(MIDIReceived(source, list) == kMIDIUnknownEndpoint);
    assert(MIDIClientDispose(client) == noErr);
    assert(MIDIGetNumberOfSources() == 0 && MIDIGetNumberOfDestinations() == 0);
    assert(MIDIClientDispose(client) == kMIDIInvalidClient);

    /* ByteCount is not capped at 64 KiB; only each MIDI packet is UInt16-sized. */
    {
        Byte *largeStorage = (Byte *)malloc(70000);
        MIDIPacketList *largeList;
        MIDIPacket *largePacket;
        assert(largeStorage != NULL);
        largeList = (MIDIPacketList *)largeStorage;
        largePacket = MIDIPacketListInit(largeList);
        assert(largePacket != NULL);
        largePacket = MIDIPacketListAdd(largeList, 70000, largePacket,
                                       3, sizeof(on), on);
        assert(largePacket != NULL);
        assert(largeList->numPackets == 1);
        assert(memcmp(largePacket->data, on, sizeof(on)) == 0);
        free(largeStorage);
    }
    puts("CoreMIDI virtual: Note On/Off, routing, bounds and cleanup PASS");
    return 0;
}
