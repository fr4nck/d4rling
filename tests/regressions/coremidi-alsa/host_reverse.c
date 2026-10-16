/*
 * ALSA -> CoreMIDI MIDI 1.0 channel-event codec tests (no /dev/snd/seq).
 * Real ALSA types and production MIDIAlsaBridge.c are used.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <CoreMIDI/MIDIServices.h>
#include <alsa/asoundlib.h>
#include <assert.h>
#include <stdio.h>

extern OSStatus D4MIDIAlsaTranslate(const MIDIPacket *, snd_seq_event_t *);
extern OSStatus D4MIDIAlsaEncodeEvent(const snd_seq_event_t *, Byte *,
                                     ByteCount, ByteCount *);

static void roundtrip(unsigned status, unsigned length, unsigned first,
                      unsigned second)
{
    union { long double align; Byte bytes[128]; } buffer;
    MIDIPacketList *list = (MIDIPacketList *)buffer.bytes;
    MIDIPacket *packet = MIDIPacketListInit(list);
    snd_seq_event_t event;
    Byte original[3] = {(Byte)status, (Byte)first, (Byte)second};
    Byte output[3] = {0xff, 0xff, 0xff};
    ByteCount result_length = 0;
    unsigned expected_status = status;

    assert(packet != NULL);
    packet = MIDIPacketListAdd(list, sizeof(buffer.bytes), packet, 0,
                              length, original);
    assert(packet != NULL);
    assert(D4MIDIAlsaTranslate(packet, &event) == noErr);
    assert(D4MIDIAlsaEncodeEvent(&event, output, sizeof(output),
                                 &result_length) == noErr);
    if ((status & 0xf0u) == 0x90u && second == 0)
        expected_status = 0x80u | (status & 0x0fu);
    assert(result_length == length);
    assert((unsigned int)output[0] == expected_status);
    assert((unsigned int)output[1] == first);
    if (length == 3) assert((unsigned int)output[2] == second);
    else assert(output[2] == 0xff);
}

static void bad_event(const snd_seq_event_t *event)
{
    Byte output[3] = {0xaa, 0xbb, 0xcc};
    ByteCount length = 99;
    assert(D4MIDIAlsaEncodeEvent(event, output, sizeof(output), &length)
           == kMIDIMessageSendErr);
    assert(length == 0);
    assert(output[0] == 0xaa && output[1] == 0xbb && output[2] == 0xcc);
}

int main(void)
{
    unsigned ch;
    snd_seq_event_t event;
    Byte output[3] = {0xaa, 0xbb, 0xcc};
    ByteCount length = 17;

    for (ch = 0; ch < 16; ++ch) {
        roundtrip(0x80 | ch, 3, 60, 42);    /* Note Off */
        roundtrip(0x90 | ch, 3, 60, 100);   /* Note On */
        roundtrip(0x90 | ch, 3, 60, 0);     /* Note On 0 -> Note Off */
        roundtrip(0xa0 | ch, 3, 60, 55);    /* Polyphonic pressure */
        roundtrip(0xb0 | ch, 3, 7, 127);    /* Control Change */
        roundtrip(0xc0 | ch, 2, 127, 0);    /* Program Change */
        roundtrip(0xd0 | ch, 2, 127, 0);    /* Channel Pressure */
        roundtrip(0xe0 | ch, 3, 0, 0);      /* Pitch bend min */
        roundtrip(0xe0 | ch, 3, 0, 64);     /* Pitch bend centered */
        roundtrip(0xe0 | ch, 3, 127, 127);  /* Pitch bend max */
    }

    /* Check rejection without altering output bytes. */
    snd_seq_ev_set_noteon(&event, 0, 60, 100);
    event.data.note.channel = 16;
    bad_event(&event);
    snd_seq_ev_set_noteon(&event, 0, 128, 100);
    bad_event(&event);
    snd_seq_ev_set_noteon(&event, 0, 60, 128);
    bad_event(&event);

    snd_seq_ev_set_controller(&event, 0, 128, 1);
    bad_event(&event);
    snd_seq_ev_set_controller(&event, 0, 7, 128);
    bad_event(&event);
    snd_seq_ev_set_controller(&event, 0, 7, -1);
    bad_event(&event);

    snd_seq_ev_set_pgmchange(&event, 0, 128);
    bad_event(&event);
    snd_seq_ev_set_chanpress(&event, 0, -1);
    bad_event(&event);
    snd_seq_ev_set_pitchbend(&event, 0, 8192);
    bad_event(&event);
    snd_seq_ev_set_pitchbend(&event, 0, -8193);
    bad_event(&event);

    snd_seq_ev_clear(&event);
    event.type = 0xff;  /* no corresponding MIDI 1.0 channel message */
    bad_event(&event);

    snd_seq_ev_set_noteon(&event, 0, 60, 100);
    assert(D4MIDIAlsaEncodeEvent(NULL, output, sizeof(output), &length) == paramErr);
    assert(D4MIDIAlsaEncodeEvent(&event, NULL, sizeof(output), &length) == paramErr);
    assert(D4MIDIAlsaEncodeEvent(&event, output, sizeof(output), NULL) == paramErr);
    assert(D4MIDIAlsaEncodeEvent(&event, output, 2, &length) == paramErr);
    assert(length == 0);
    assert(output[0] == 0xaa && output[1] == 0xbb && output[2] == 0xcc);

    snd_seq_ev_set_pgmchange(&event, 15, 127);
    assert(D4MIDIAlsaEncodeEvent(&event, output, 2, &length) == noErr);
    assert(length == 2 && output[0] == 0xcf && output[1] == 127);
    assert(output[2] == 0xcc);

    puts("ALSA_REVERSE_PASS: seven MIDI classes, 16 channels and invalid events");
    return 0;
}
