/*
 * Native ALSA bridge preflight test: real ALSA headers/link, no sequencer.
 * Wrap only snd_seq_open so packet validation can be checked independently
 * of /dev/snd/seq. This is NOT a sequencer transport test.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <CoreMIDI/MIDIServices.h>
#include <alsa/asoundlib.h>
#include <assert.h>
#include <errno.h>
#include <stdio.h>

static unsigned open_calls;

int __wrap_snd_seq_open(snd_seq_t **handle, const char *name, int streams, int mode)
{
    (void)handle;
    (void)name;
    (void)streams;
    (void)mode;
    ++open_calls;
    return -ENODEV;
}

static MIDIPacketList *make_list(unsigned char *bytes, size_t size,
                                 const Byte *first, const Byte *second)
{
    MIDIPacketList *list = (MIDIPacketList *)bytes;
    MIDIPacket *packet = MIDIPacketListInit(list);
    assert(packet != NULL);
    packet = MIDIPacketListAdd(list, (ByteCount)size, packet, 0, 3, first);
    assert(packet != NULL);
    if (second) {
        packet = MIDIPacketListAdd(list, (ByteCount)size, packet, 0, 3, second);
        assert(packet != NULL);
    }
    return list;
}

int main(void)
{
    MIDIClientRef client = 0;
    MIDIPortRef output = 0;
    /* This tag is intentionally synthetic: it must be validated before
       opening a real ALSA sequencer. */
    const MIDIEndpointRef fake_destination = 0xa0000101u;
    const Byte on[3] = {0x90, 60, 100};
    const Byte bad_note[3] = {0x90, 128, 100};
    const Byte bad_velocity[3] = {0x90, 60, 128};
    const Byte unsupported[3] = {0xb0, 60, 100};
    union { long double align; unsigned char bytes[128]; } storage;
    MIDIPacketList *list;

    assert(MIDIClientCreate(NULL, NULL, NULL, &client) == noErr);
    assert(MIDIOutputPortCreate(client, NULL, &output) == noErr);

    list = make_list(storage.bytes, sizeof(storage.bytes), bad_note, NULL);
    assert(MIDISend(output, fake_destination, list) == kMIDIMessageSendErr);
    assert(open_calls == 0);

    list = make_list(storage.bytes, sizeof(storage.bytes), bad_velocity, NULL);
    assert(MIDISend(output, fake_destination, list) == kMIDIMessageSendErr);
    assert(open_calls == 0);

    list = make_list(storage.bytes, sizeof(storage.bytes), unsupported, NULL);
    assert(MIDISend(output, fake_destination, list) == kMIDIMessageSendErr);
    assert(open_calls == 0);

    /* The second invalid packet must prevent even opening the sequencer. */
    list = make_list(storage.bytes, sizeof(storage.bytes), on, bad_velocity);
    assert(MIDISend(output, fake_destination, list) == kMIDIMessageSendErr);
    assert(open_calls == 0);

    list = make_list(storage.bytes, sizeof(storage.bytes), on, NULL);
    assert(MIDISend(output, 0xa0010101u, list) == kMIDIUnknownEndpoint);
    assert(open_calls == 0);

    /* A valid packet passes preflight and reaches the wrapped open call. */
    assert(MIDISend(output, fake_destination, list) == kMIDIMessageSendErr);
    assert(open_calls == 1);

    assert(MIDIPortDispose(output) == noErr);
    assert(MIDIClientDispose(client) == noErr);
    puts("ALSA_PREFLIGHT_PASS: packet validation before sequencer access");
    return 0;
}
