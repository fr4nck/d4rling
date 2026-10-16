/*
 * Injected ALSA input source-address routing to CoreMIDI virtual sources.
 * No ALSA client, sequencer, polling, or physical MIDI input is created.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <CoreMIDI/MIDIServices.h>
#include <alsa/asoundlib.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

extern OSStatus D4MIDIAlsaBindSourceAddress(int, int, MIDIEndpointRef);
extern OSStatus D4MIDIAlsaUnbindSourceAddress(int, int);
extern OSStatus D4MIDIAlsaRouteInputEvent(const snd_seq_event_t *);

typedef struct {
    unsigned calls;
    unsigned status;
    unsigned first;
    unsigned second;
    unsigned length;
    unsigned channel;
    void *connection;
    int unbind;
    int alsaClient;
    int alsaPort;
} Receiver;

static void receive(const MIDIPacketList *list, void *opaque, void *connection)
{
    Receiver *receiver = (Receiver *)opaque;
    const MIDIPacket *packet;
    assert(list != NULL && list->numPackets == 1);
    assert(receiver != NULL);
    packet = &list->packet[0];
    assert(packet->length == 2 || packet->length == 3);
    ++receiver->calls;
    receiver->status = packet->data[0];
    receiver->channel = packet->data[0] & 0x0f;
    receiver->first = packet->data[1];
    receiver->second = packet->length == 3 ? packet->data[2] : 0;
    receiver->length = packet->length;
    receiver->connection = connection;
    if (receiver->unbind)
        assert(D4MIDIAlsaUnbindSourceAddress(receiver->alsaClient,
                                            receiver->alsaPort) == noErr);
}

static void inject_note(snd_seq_event_t *event, int client, int port, int channel)
{
    snd_seq_ev_set_noteon(event, channel, 60, 100);
    event->source.client = (unsigned char)client;
    event->source.port = (unsigned char)port;
}

int main(void)
{
    MIDIClientRef midiClient = 0;
    MIDIEndpointRef sourceA = 0, sourceB = 0;
    MIDIPortRef portA = 0, portB = 0;
    Receiver a = {0}, b = {0};
    snd_seq_event_t event;
    unsigned channel;

    assert(MIDIClientCreate(NULL, NULL, NULL, &midiClient) == noErr);
    assert(MIDISourceCreate(midiClient, NULL, &sourceA) == noErr);
    assert(MIDISourceCreate(midiClient, NULL, &sourceB) == noErr);
    assert(MIDIInputPortCreate(midiClient, NULL, receive, &a, &portA) == noErr);
    assert(MIDIInputPortCreate(midiClient, NULL, receive, &b, &portB) == noErr);
    assert(MIDIPortConnectSource(portA, sourceA,
           (void *)(uintptr_t)0x1111) == noErr);
    assert(MIDIPortConnectSource(portB, sourceB,
           (void *)(uintptr_t)0x2222) == noErr);

    assert(D4MIDIAlsaBindSourceAddress(-1, 1, sourceA) == paramErr);
    assert(D4MIDIAlsaBindSourceAddress(256, 1, sourceA) == paramErr);
    assert(D4MIDIAlsaBindSourceAddress(42, 256, sourceA) == paramErr);
    assert(D4MIDIAlsaBindSourceAddress(42, 1, 0) == paramErr);
    assert(D4MIDIAlsaBindSourceAddress(42, 1, 0xfffffff0u)
           == kMIDIUnknownEndpoint);
    assert(D4MIDIAlsaRouteInputEvent(NULL) == paramErr);

    assert(D4MIDIAlsaBindSourceAddress(42, 1, sourceA) == noErr);
    assert(D4MIDIAlsaBindSourceAddress(42, 1, sourceA) == noErr);
    assert(D4MIDIAlsaBindSourceAddress(42, 1, sourceB) == paramErr);
    assert(D4MIDIAlsaBindSourceAddress(43, 2, sourceB) == noErr);

    for (channel = 0; channel < 16; ++channel) {
        inject_note(&event, 42, 1, (int)channel);
        assert(D4MIDIAlsaRouteInputEvent(&event) == noErr);
        assert(a.calls == channel + 1 && b.calls == channel);
        assert(a.status == (0x90u | channel));
        assert(a.first == 60 && a.second == 100 && a.length == 3);
        assert(a.connection == (void *)(uintptr_t)0x1111);

        inject_note(&event, 43, 2, (int)channel);
        assert(D4MIDIAlsaRouteInputEvent(&event) == noErr);
        assert(a.calls == channel + 1 && b.calls == channel + 1);
        assert(b.status == (0x90u | channel));
        assert(b.first == 60 && b.second == 100 && b.length == 3);
        assert(b.connection == (void *)(uintptr_t)0x2222);
    }

    inject_note(&event, 44, 1, 0);
    assert(D4MIDIAlsaRouteInputEvent(&event) == kMIDIUnknownEndpoint);
    assert(a.calls == 16 && b.calls == 16);

    /* The callback is allowed to unbind its own address without deadlock. */
    a.unbind = 1;
    a.alsaClient = 42;
    a.alsaPort = 1;
    inject_note(&event, 42, 1, 9);
    assert(D4MIDIAlsaRouteInputEvent(&event) == noErr);
    assert(a.calls == 17 && b.calls == 16);
    assert(D4MIDIAlsaRouteInputEvent(&event) == kMIDIUnknownEndpoint);
    assert(D4MIDIAlsaUnbindSourceAddress(42, 1) == kMIDINoConnection);
    a.unbind = 0;

    /* Program Change is two bytes, and only the matching source receives. */
    snd_seq_ev_set_pgmchange(&event, 15, 127);
    event.source.client = 43;
    event.source.port = 2;
    assert(D4MIDIAlsaRouteInputEvent(&event) == noErr);
    assert(a.calls == 17 && b.calls == 17);
    assert(b.status == 0xcf && b.first == 127 && b.length == 2);

    snd_seq_ev_set_controller(&event, 0, 7, 128);
    event.source.client = 43;
    event.source.port = 2;
    assert(D4MIDIAlsaRouteInputEvent(&event) == kMIDIMessageSendErr);
    assert(b.calls == 17);

    /* Source lifetime is independent from the explicit address binding. */
    assert(MIDIEndpointDispose(sourceB) == noErr);
    inject_note(&event, 43, 2, 0);
    assert(D4MIDIAlsaRouteInputEvent(&event) == kMIDIUnknownEndpoint);
    assert(D4MIDIAlsaUnbindSourceAddress(43, 2) == noErr);
    assert(D4MIDIAlsaUnbindSourceAddress(-1, 2) == paramErr);
    assert(MIDIClientDispose(midiClient) == noErr);

    puts("ALSA_SOURCE_ROUTE_PASS: injected source addresses delivered to distinct callbacks");
    return 0;
}
