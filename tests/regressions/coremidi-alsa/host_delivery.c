/*
 * Deliver synthetic ALSA channel events to actual CoreMIDI virtual ports.
 * Uses the production ALSA codec and CoreMIDI callback router, but does not
 * open an ALSA sequencer or represent real kernel/physical MIDI reception.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <CoreMIDI/MIDIServices.h>
#include <alsa/asoundlib.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

extern OSStatus D4MIDIAlsaDeliverToVirtualSource(MIDIEndpointRef,
                                                const snd_seq_event_t *);

typedef struct {
    unsigned calls;
    unsigned status;
    unsigned first;
    unsigned second;
    unsigned length;
    void *lastConnection;
} Delivery;

static void receive(const MIDIPacketList *list, void *context, void *connection)
{
    Delivery *received = (Delivery *)context;
    const MIDIPacket *packet;
    assert(received != NULL);
    assert(list != NULL && list->numPackets == 1);
    packet = &list->packet[0];
    assert(packet->length == 2 || packet->length == 3);
    assert(packet->timeStamp == 0);
    ++received->calls;
    received->length = packet->length;
    received->status = packet->data[0];
    received->first = packet->data[1];
    received->second = packet->length == 3 ? packet->data[2] : 0;
    received->lastConnection = connection;
}

static void check(const Delivery *r, unsigned calls, unsigned status,
                  unsigned first, unsigned second, unsigned length,
                  void *connection)
{
    assert(r->calls == calls);
    assert(r->status == status);
    assert(r->first == first);
    assert(r->second == second);
    assert(r->length == length);
    assert(r->lastConnection == connection);
}

int main(void)
{
    MIDIClientRef client = 0;
    MIDIPortRef portA = 0, portB = 0;
    MIDIEndpointRef source = 0;
    Delivery a = {0}, b = {0};
    const void *connA = (void *)(uintptr_t)0x1234;
    const void *connB = (void *)(uintptr_t)0x5678;
    snd_seq_event_t event;
    unsigned ch, counter = 0;

    assert(MIDIClientCreate(NULL, NULL, NULL, &client) == noErr);
    assert(MIDISourceCreate(client, NULL, &source) == noErr);
    assert(MIDIInputPortCreate(client, NULL, receive, &a, &portA) == noErr);
    assert(MIDIInputPortCreate(client, NULL, receive, &b, &portB) == noErr);
    assert(MIDIPortConnectSource(portA, source, (void *)connA) == noErr);
    assert(MIDIPortConnectSource(portB, source, (void *)connB) == noErr);

    for (ch = 0; ch < 16; ++ch) {
        unsigned status, first, second, length;

        snd_seq_ev_set_noteon(&event, ch, 60, 100);
        status = 0x90u | ch; first = 60; second = 100; length = 3;
        assert(D4MIDIAlsaDeliverToVirtualSource(source, &event) == noErr);
        ++counter;
        check(&a, counter, status, first, second, length, (void *)connA);
        check(&b, counter, status, first, second, length, (void *)connB);

        snd_seq_ev_set_noteoff(&event, ch, 60, 0);
        status = 0x80u | ch; first = 60; second = 0;
        assert(D4MIDIAlsaDeliverToVirtualSource(source, &event) == noErr);
        ++counter;
        check(&a, counter, status, first, second, length, (void *)connA);
        check(&b, counter, status, first, second, length, (void *)connB);

        snd_seq_ev_set_keypress(&event, ch, 60, 12);
        status = 0xa0u | ch; first = 60; second = 12;
        assert(D4MIDIAlsaDeliverToVirtualSource(source, &event) == noErr);
        ++counter;
        check(&a, counter, status, first, second, length, (void *)connA);
        check(&b, counter, status, first, second, length, (void *)connB);

        snd_seq_ev_set_controller(&event, ch, 7, 127);
        status = 0xb0u | ch; first = 7; second = 127;
        assert(D4MIDIAlsaDeliverToVirtualSource(source, &event) == noErr);
        ++counter;
        check(&a, counter, status, first, second, length, (void *)connA);
        check(&b, counter, status, first, second, length, (void *)connB);

        snd_seq_ev_set_pgmchange(&event, ch, 12);
        status = 0xc0u | ch; first = 12; second = 0; length = 2;
        assert(D4MIDIAlsaDeliverToVirtualSource(source, &event) == noErr);
        ++counter;
        check(&a, counter, status, first, second, length, (void *)connA);
        check(&b, counter, status, first, second, length, (void *)connB);

        snd_seq_ev_set_chanpress(&event, ch, 33);
        status = 0xd0u | ch; first = 33; second = 0;
        assert(D4MIDIAlsaDeliverToVirtualSource(source, &event) == noErr);
        ++counter;
        check(&a, counter, status, first, second, length, (void *)connA);
        check(&b, counter, status, first, second, length, (void *)connB);

        snd_seq_ev_set_pitchbend(&event, ch, 8191);
        status = 0xe0u | ch; first = 127; second = 127; length = 3;
        assert(D4MIDIAlsaDeliverToVirtualSource(source, &event) == noErr);
        ++counter;
        check(&a, counter, status, first, second, length, (void *)connA);
        check(&b, counter, status, first, second, length, (void *)connB);
    }

    /* Reject unsupported and invalid native events without callbacks. */
    snd_seq_ev_set_controller(&event, 0, 7, 128);
    assert(D4MIDIAlsaDeliverToVirtualSource(source, &event) == kMIDIMessageSendErr);
    snd_seq_ev_clear(&event);
    event.type = 0xff;
    assert(D4MIDIAlsaDeliverToVirtualSource(source, &event) == kMIDIMessageSendErr);
    assert(D4MIDIAlsaDeliverToVirtualSource(source, NULL) == paramErr);
    assert(a.calls == counter && b.calls == counter);

    snd_seq_ev_set_noteon(&event, 0, 60, 100);
    assert(D4MIDIAlsaDeliverToVirtualSource(0, &event) == kMIDIUnknownEndpoint);
    assert(a.calls == counter && b.calls == counter);

    assert(MIDIPortDisconnectSource(portB, source) == noErr);
    assert(D4MIDIAlsaDeliverToVirtualSource(source, &event) == noErr);
    ++counter;
    check(&a, counter, 0x90, 60, 100, 3, (void *)connA);
    assert(b.calls == counter - 1);

    assert(MIDIEndpointDispose(source) == noErr);
    assert(D4MIDIAlsaDeliverToVirtualSource(source, &event) == kMIDIUnknownEndpoint);
    assert(a.calls == counter && b.calls == counter - 1);
    assert(MIDIClientDispose(client) == noErr);

    puts("ALSA_DELIVERY_PASS: synthetic events routed to CoreMIDI callbacks");
    return 0;
}
