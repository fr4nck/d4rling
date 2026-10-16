/*
 * ALSA event translation checks with genuine ALSA types, no sequencer device.
 * This exercises the real production D4MIDIAlsaTranslate function.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <CoreMIDI/MIDIServices.h>
#include <alsa/asoundlib.h>
#include <assert.h>
#include <stdio.h>

/* Internal-only symbol; not an Apple CoreMIDI API. */
extern OSStatus D4MIDIAlsaTranslate(const MIDIPacket *, snd_seq_event_t *);

static void check(unsigned status, unsigned length, unsigned first, unsigned second,
                  int type, unsigned channel, unsigned primary, int secondary)
{
    union { long double align; Byte bytes[128]; } storage;
    MIDIPacketList *list = (MIDIPacketList *)storage.bytes;
    MIDIPacket *packet;
    snd_seq_event_t event;
    Byte data[3] = {(Byte)status, (Byte)first, (Byte)second};

    packet = MIDIPacketListInit(list);
    assert(packet != NULL);
    packet = MIDIPacketListAdd(list, sizeof(storage.bytes), packet, 0,
                              length, data);
    assert(packet != NULL);
    assert(D4MIDIAlsaTranslate(packet, &event) == noErr);
    assert(event.type == type);
    if (type == SND_SEQ_EVENT_NOTEON || type == SND_SEQ_EVENT_NOTEOFF ||
        type == SND_SEQ_EVENT_KEYPRESS) {
        assert(event.data.note.channel == channel);
        assert(event.data.note.note == primary);
        assert(event.data.note.velocity == secondary);
    } else {
        assert(event.data.control.channel == channel);
        assert(event.data.control.value == secondary);
        if (type == SND_SEQ_EVENT_CONTROLLER)
            assert(event.data.control.param == primary);
    }
}

static void reject(unsigned status, unsigned length, unsigned first, unsigned second)
{
    union { long double align; Byte bytes[128]; } storage;
    MIDIPacketList *list = (MIDIPacketList *)storage.bytes;
    MIDIPacket *packet;
    snd_seq_event_t event;
    Byte data[4] = {(Byte)status, (Byte)first, (Byte)second, 0};

    packet = MIDIPacketListInit(list);
    assert(packet != NULL);
    packet = MIDIPacketListAdd(list, sizeof(storage.bytes), packet, 0,
                              length, data);
    assert(packet != NULL);
    assert(D4MIDIAlsaTranslate(packet, &event) == kMIDIMessageSendErr);
}

int main(void)
{
    unsigned channel;
    snd_seq_event_t unused;
    assert(D4MIDIAlsaTranslate(NULL, &unused) == paramErr);

    for (channel = 0; channel < 16; ++channel) {
        check(0x80 | channel, 3, 60, 42,
              SND_SEQ_EVENT_NOTEOFF, channel, 60, 42);
        check(0x90 | channel, 3, 60, 100,
              SND_SEQ_EVENT_NOTEON, channel, 60, 100);
        check(0x90 | channel, 3, 60, 0,
              SND_SEQ_EVENT_NOTEOFF, channel, 60, 0);
        check(0xa0 | channel, 3, 60, 55,
              SND_SEQ_EVENT_KEYPRESS, channel, 60, 55);
        check(0xb0 | channel, 3, 7, 127,
              SND_SEQ_EVENT_CONTROLLER, channel, 7, 127);
        check(0xc0 | channel, 2, 127, 0,
              SND_SEQ_EVENT_PGMCHANGE, channel, 0, 127);
        check(0xd0 | channel, 2, 127, 0,
              SND_SEQ_EVENT_CHANPRESS, channel, 0, 127);
        check(0xe0 | channel, 3, 0, 0,
              SND_SEQ_EVENT_PITCHBEND, channel, 0, -8192);
        check(0xe0 | channel, 3, 0, 64,
              SND_SEQ_EVENT_PITCHBEND, channel, 0, 0);
        check(0xe0 | channel, 3, 127, 127,
              SND_SEQ_EVENT_PITCHBEND, channel, 0, 8191);
    }

    reject(0x70, 3, 60, 100);  /* running status / missing status */
    reject(0xf0, 3, 1, 2);     /* SysEx: unsupported */
    reject(0xf8, 3, 1, 2);     /* realtime: unsupported */
    reject(0x90, 2, 60, 0);    /* short note */
    reject(0xc0, 3, 60, 0);    /* long program change */
    reject(0xd0, 3, 60, 0);    /* long channel pressure */
    reject(0xb0, 3, 128, 1);  /* controller out of range */
    reject(0x90, 3, 60, 128); /* velocity out of range */
    reject(0xe0, 3, 0, 128);  /* pitch high byte out of range */
    reject(0x90, 4, 60, 100); /* multiple messages not yet supported */

    puts("ALSA_TRANSLATION_PASS: seven channel-message classes and 16 channels");
    return 0;
}
