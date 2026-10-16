/*
 * CoreMIDI ALSA input pump test with genuine ALSA types and an intercepted
 * snd_seq_event_input. No kernel sequencer, MIDI hardware or input thread.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <CoreMIDI/MIDIServices.h>
#include <alsa/asoundlib.h>
#include "MIDIAlsaBridge.h"
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>

extern OSStatus D4MIDIAlsaBindSourceAddress(int, int, MIDIEndpointRef);

typedef struct {
    unsigned callbacks;
    unsigned status;
    unsigned first;
    unsigned second;
    unsigned length;
    void *connection;
} Received;

static snd_seq_event_t script[8];
static unsigned script_count, script_cursor, input_calls;
static int terminal_status = -EAGAIN;
static int yield_null_event;

int __wrap_snd_seq_event_input(snd_seq_t *sequencer, snd_seq_event_t **event)
{
    assert(sequencer == (snd_seq_t *)(uintptr_t)1);
    assert(event != NULL);
    ++input_calls;
    *event = NULL;
    if (yield_null_event) return 0;
    if (script_cursor == script_count) return terminal_status;
    *event = &script[script_cursor++];
    /* A successful ALSA read returns the remaining queued byte count,
     * which may be zero; it does NOT report success as a boolean.
     */
    return 0;
}

static void receive(const MIDIPacketList *list, void *context, void *connection)
{
    Received *state = (Received *)context;
    const MIDIPacket *packet;
    assert(list != NULL && list->numPackets == 1);
    packet = &list->packet[0];
    assert(packet->length == 2 || packet->length == 3);
    ++state->callbacks;
    state->status = packet->data[0];
    state->first = packet->data[1];
    state->second = packet->length == 3 ? packet->data[2] : 0;
    state->length = packet->length;
    state->connection = connection;
}

static void set_sender(snd_seq_event_t *event, unsigned client, unsigned port)
{
    event->source.client = (unsigned char)client;
    event->source.port = (unsigned char)port;
}

static void reset_script(unsigned count, int end_status)
{
    assert(count <= sizeof(script) / sizeof(script[0]));
    script_count = count;
    script_cursor = 0;
    input_calls = 0;
    terminal_status = end_status;
    yield_null_event = 0;
}

int main(void)
{
    MIDIClientRef client = 0;
    MIDIEndpointRef sourceA = 0, sourceB = 0;
    MIDIPortRef portA = 0, portB = 0;
    Received a = {0}, b = {0};
    snd_seq_t *fake = (snd_seq_t *)(uintptr_t)1;
    ItemCount delivered = 99;
    unsigned i;

    assert(D4MIDIAlsaPumpNonblocking(NULL, 1, &delivered) == paramErr);
    assert(delivered == 0);
    assert(D4MIDIAlsaPumpNonblocking(fake, 0, &delivered) == paramErr);
    assert(D4MIDIAlsaPumpNonblocking(fake, 4097, &delivered) == paramErr);
    assert(D4MIDIAlsaPumpNonblocking(fake, 1, NULL) == paramErr);
    assert(input_calls == 0);

    assert(MIDIClientCreate(NULL, NULL, NULL, &client) == noErr);
    assert(MIDISourceCreate(client, NULL, &sourceA) == noErr);
    assert(MIDISourceCreate(client, NULL, &sourceB) == noErr);
    assert(MIDIInputPortCreate(client, NULL, receive, &a, &portA) == noErr);
    assert(MIDIInputPortCreate(client, NULL, receive, &b, &portB) == noErr);
    assert(MIDIPortConnectSource(portA, sourceA, (void *)(uintptr_t)0x1111) == noErr);
    assert(MIDIPortConnectSource(portB, sourceB, (void *)(uintptr_t)0x2222) == noErr);
    assert(D4MIDIAlsaBindSourceAddress(42, 1, sourceA) == noErr);
    assert(D4MIDIAlsaBindSourceAddress(43, 2, sourceB) == noErr);

    reset_script(5, -EAGAIN);
    snd_seq_ev_set_noteon(&script[0], 0, 60, 100);
    set_sender(&script[0], 42, 1);
    snd_seq_ev_set_pgmchange(&script[1], 15, 127);
    set_sender(&script[1], 43, 2);
    snd_seq_ev_set_noteon(&script[2], 1, 61, 100);
    set_sender(&script[2], 44, 3); /* Unbound sender is ignored. */
    snd_seq_ev_clear(&script[3]);
    script[3].type = SND_SEQ_EVENT_SYSEX; /* unsupported */
    set_sender(&script[3], 42, 1);
    snd_seq_ev_set_controller(&script[4], 7, 10, 99);
    set_sender(&script[4], 42, 1);
    assert(D4MIDIAlsaPumpNonblocking(fake, 8, &delivered) == noErr);
    assert(delivered == 3 && script_cursor == 5 && input_calls == 6);
    assert(a.callbacks == 2 && b.callbacks == 1);
    assert(a.status == 0xb7 && a.first == 10 && a.second == 99);
    assert(a.connection == (void *)(uintptr_t)0x1111);
    assert(b.status == 0xcf && b.first == 127 && b.length == 2);
    assert(b.connection == (void *)(uintptr_t)0x2222);

    reset_script(3, -EAGAIN);
    for (i = 0; i < 3; ++i) {
        snd_seq_ev_set_noteon(&script[i], i, 60, 100);
        set_sender(&script[i], 42, 1);
    }
    assert(D4MIDIAlsaPumpNonblocking(fake, 2, &delivered) == noErr);
    assert(delivered == 2 && script_cursor == 2 && input_calls == 2);
    assert(a.callbacks == 4);
    assert(D4MIDIAlsaPumpNonblocking(fake, 2, &delivered) == noErr);
    assert(delivered == 1 && script_cursor == 3 && input_calls == 4);
    assert(a.callbacks == 5);

    reset_script(0, -EIO);
    assert(D4MIDIAlsaPumpNonblocking(fake, 3, &delivered)
           == kMIDIMessageSendErr);
    assert(delivered == 0 && input_calls == 1);
    reset_script(0, -ENOSPC); /* Lost kernel events are not silently ignored. */
    assert(D4MIDIAlsaPumpNonblocking(fake, 3, &delivered)
           == kMIDIMessageSendErr);
    assert(delivered == 0 && input_calls == 1);
    reset_script(0, -EAGAIN);
    yield_null_event = 1;
    assert(D4MIDIAlsaPumpNonblocking(fake, 3, &delivered)
           == kMIDIMessageSendErr);
    assert(delivered == 0 && input_calls == 1);

    assert(MIDIClientDispose(client) == noErr);
    puts("ALSA_INPUT_PUMP_PASS: bounded nonblocking events delivered and errors handled");
    return 0;
}
