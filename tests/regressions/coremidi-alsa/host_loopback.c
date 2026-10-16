/*
 * Native Linux ALSA Sequencer integration smoke test for the CoreMIDI bridge.
 * Does not require Logic or a physical MIDI controller.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <CoreMIDI/MIDIServices.h>
#include "MIDIAlsaBridge.h"
#include <alsa/asoundlib.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int receive_note(snd_seq_t *receiver, int expected_type, int expected_velocity)
{
    struct pollfd fds[8];
    int count = snd_seq_poll_descriptors_count(receiver, POLLIN);
    int tries;
    if (count <= 0 || count > (int)(sizeof(fds) / sizeof(fds[0])) ||
        snd_seq_poll_descriptors(receiver, fds, (unsigned int)count, POLLIN) < 0)
        return -1;
    for (tries = 0; tries < 10; ++tries) {
        snd_seq_event_t *event = NULL;
        int match;
        if (poll(fds, (nfds_t)count, 500) <= 0) return -1;
        if (snd_seq_event_input(receiver, &event) < 0 || !event) return -1;
        match = (event->type == expected_type &&
                 event->data.note.channel == 0 &&
                 event->data.note.note == 60 &&
                 event->data.note.velocity == expected_velocity);
        snd_seq_free_event(event);
        if (match) return 0;
    }
    return -1;
}

static int send_one(MIDIPortRef output, MIDIEndpointRef destination,
                    unsigned char status, unsigned char velocity)
{
    union { long double align; unsigned char bytes[128]; } storage;
    MIDIPacketList *list = (MIDIPacketList *)storage.bytes;
    unsigned char data[3] = {status, 60, velocity};
    MIDIPacket *packet = MIDIPacketListInit(list);
    if (!packet || !MIDIPacketListAdd(list, sizeof(storage.bytes), packet, 0, 3, data))
        return -1;
    return MIDISend(output, destination, list);
}


static int find_native_source(int wanted_client, int wanted_port)
{
    ItemCount count = D4MIDIAlsaSourceAddressCount();
    ItemCount i;
    for (i = 0; i < count; ++i) {
        int client = -1, port = -1;
        if (D4MIDIAlsaSourceAddressAt(i, &client, &port) != noErr)
            return -1; /* Device list changed or query failed. */
        if (client == wanted_client && port == wanted_port)
            return 1;
    }
    return 0;
}

int main(void)
{
    snd_seq_t *receiver = NULL;
    snd_seq_t *native_source = NULL;
    MIDIClientRef client = 0;
    MIDIPortRef output = 0;
    MIDIEndpointRef destination = 0;
    int receiving_port, receiver_client, source_port, source_client, rc = 1;
    ItemCount i;
    if (snd_seq_open(&receiver, "default", SND_SEQ_OPEN_INPUT, SND_SEQ_NONBLOCK) < 0) {
        fprintf(stderr, "ALSA_RUNTIME_FAIL: snd_seq_open receiver failed\n");
        return 1;
    }
    snd_seq_set_client_name(receiver, "d4rling MIDI self-test receiver");
    receiving_port = snd_seq_create_simple_port(receiver, "Test Note Receiver",
        SND_SEQ_PORT_CAP_WRITE | SND_SEQ_PORT_CAP_SUBS_WRITE,
        SND_SEQ_PORT_TYPE_MIDI_GENERIC | SND_SEQ_PORT_TYPE_APPLICATION);
    if (receiving_port < 0) {
        fprintf(stderr, "ALSA_RUNTIME_FAIL: cannot create input port\n");
        goto cleanup;
    }
    receiver_client = snd_seq_client_id(receiver);
    /* Real sequencer discovery gate: advertise a native ALSA sender and
     * ensure our source enumerator finds it but excludes the receiver.
     */
    if (snd_seq_open(&native_source, "default", SND_SEQ_OPEN_OUTPUT,
                     SND_SEQ_NONBLOCK) < 0) {
        fprintf(stderr, "ALSA_RUNTIME_FAIL: source client creation failed\n");
        goto cleanup;
    }
    snd_seq_set_client_name(native_source, "d4rling MIDI self-test source");
    source_port = snd_seq_create_simple_port(native_source, "Test MIDI Source",
        SND_SEQ_PORT_CAP_READ | SND_SEQ_PORT_CAP_SUBS_READ,
        SND_SEQ_PORT_TYPE_MIDI_GENERIC | SND_SEQ_PORT_TYPE_APPLICATION);
    if (source_port < 0) {
        fprintf(stderr, "ALSA_RUNTIME_FAIL: source port creation failed\n");
        goto cleanup;
    }
    source_client = snd_seq_client_id(native_source);
    if (find_native_source(source_client, source_port) != 1 ||
        find_native_source(receiver_client, receiving_port) != 0) {
        fprintf(stderr, "ALSA_RUNTIME_FAIL: source discovery/capability filtering\n");
        goto cleanup;
    }
    puts("ALSA_SOURCE_RUNTIME_PASS: native sequencer source port discovered");
    for (i = 0; i < MIDIGetNumberOfDestinations(); ++i) {
        MIDIEndpointRef candidate = MIDIGetDestination(i);
        if (((candidate >> 8) & 255) == (unsigned)receiver_client &&
            (candidate & 255) == (unsigned)receiving_port) {
            destination = candidate;
            break;
        }
    }
    if (!destination) {
        fprintf(stderr, "ALSA_RUNTIME_FAIL: receiver not discovered by CoreMIDI bridge\n");
        goto cleanup;
    }
    if (MIDIClientCreate(NULL, NULL, NULL, &client) != noErr ||
        MIDIOutputPortCreate(client, NULL, &output) != noErr) {
        fprintf(stderr, "ALSA_RUNTIME_FAIL: CoreMIDI client/output creation\n");
        goto cleanup;
    }
    if (send_one(output, destination, 0x90, 100) != noErr ||
        receive_note(receiver, SND_SEQ_EVENT_NOTEON, 100) != 0) {
        fprintf(stderr, "ALSA_RUNTIME_FAIL: Note On not received\n");
        goto cleanup;
    }
    if (send_one(output, destination, 0x80, 0) != noErr ||
        receive_note(receiver, SND_SEQ_EVENT_NOTEOFF, 0) != 0) {
        fprintf(stderr, "ALSA_RUNTIME_FAIL: Note Off not received\n");
        goto cleanup;
    }
    if (send_one(output, destination, 0x90, 128) != kMIDIMessageSendErr) {
        fprintf(stderr, "ALSA_RUNTIME_FAIL: invalid velocity not rejected\n");
        goto cleanup;
    }
    puts("ALSA_RUNTIME_PASS: native sequencer Note On/Off roundtrip");
    rc = 0;
cleanup:
    if (output) MIDIPortDispose(output);
    if (client) MIDIClientDispose(client);
    if (native_source) snd_seq_close(native_source);
    if (receiver) snd_seq_close(receiver);
    return rc;
}
