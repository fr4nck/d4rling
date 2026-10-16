/*
 * ALSA source binding lifecycle and capacity regression.
 * Compiles against real ALSA types but performs no sequencer I/O.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <CoreMIDI/MIDIServices.h>
#include <alsa/asoundlib.h>
#include <assert.h>
#include <stdio.h>

extern OSStatus D4MIDIAlsaBindSourceAddress(int, int, MIDIEndpointRef);
extern OSStatus D4MIDIAlsaUnbindSourceAddress(int, int);
extern OSStatus D4MIDIAlsaRouteInputEvent(const snd_seq_event_t *);

int main(void)
{
    MIDIClientRef clientA = 0, clientB = 0, clientC = 0;
    MIDIEndpointRef sourceA = 0, sourceB = 0, sourceB2 = 0, sourceC = 0;
    snd_seq_event_t event;
    int client;

    assert(MIDIClientCreate(NULL, NULL, NULL, &clientA) == noErr);
    assert(MIDIClientCreate(NULL, NULL, NULL, &clientB) == noErr);
    assert(MIDISourceCreate(clientA, NULL, &sourceA) == noErr);
    assert(MIDISourceCreate(clientB, NULL, &sourceB) == noErr);
    assert(MIDISourceCreate(clientB, NULL, &sourceB2) == noErr);

    /* The binding table has 128 slots. Fill all of them with sourceA. */
    for (client = 0; client < 128; ++client)
        assert(D4MIDIAlsaBindSourceAddress(client, 3, sourceA) == noErr);
    assert(D4MIDIAlsaBindSourceAddress(128, 3, sourceB)
           == kMIDIMessageSendErr);

    /* Disposal must purge ALL aliases, allowing reuse of every slot. */
    assert(MIDIEndpointDispose(sourceA) == noErr);
    assert(D4MIDIAlsaUnbindSourceAddress(0, 3) == kMIDINoConnection);
    assert(D4MIDIAlsaUnbindSourceAddress(127, 3) == kMIDINoConnection);
    assert(D4MIDIAlsaBindSourceAddress(0, 3, sourceA)
           == kMIDIUnknownEndpoint);

    for (client = 0; client < 128; ++client)
        assert(D4MIDIAlsaBindSourceAddress(client, 4,
               client % 2 ? sourceB2 : sourceB) == noErr);
    assert(D4MIDIAlsaBindSourceAddress(128, 4, sourceB)
           == kMIDIMessageSendErr);

    /* Client disposal must purge bindings from all its owned sources. */
    assert(MIDIClientDispose(clientB) == noErr);
    assert(D4MIDIAlsaUnbindSourceAddress(0, 4) == kMIDINoConnection);
    assert(D4MIDIAlsaUnbindSourceAddress(127, 4) == kMIDINoConnection);
    assert(D4MIDIAlsaBindSourceAddress(2, 4, sourceB)
           == kMIDIUnknownEndpoint);
    assert(D4MIDIAlsaBindSourceAddress(3, 4, sourceB2)
           == kMIDIUnknownEndpoint);

    assert(MIDIClientCreate(NULL, NULL, NULL, &clientC) == noErr);
    assert(MIDISourceCreate(clientC, NULL, &sourceC) == noErr);
    for (client = 0; client < 128; ++client)
        assert(D4MIDIAlsaBindSourceAddress(client, 5, sourceC) == noErr);

    /* Delivery to a registered but disconnected source succeeds and is inert.
     * This tests address resolution rather than ALSA hardware traffic.
     */
    snd_seq_ev_set_noteon(&event, 0, 60, 100);
    event.source.client = 127;
    event.source.port = 5;
    assert(D4MIDIAlsaRouteInputEvent(&event) == noErr);

    assert(MIDIClientDispose(clientC) == noErr);
    for (client = 0; client < 128; ++client)
        assert(D4MIDIAlsaUnbindSourceAddress(client, 5) == kMIDINoConnection);
    assert(D4MIDIAlsaRouteInputEvent(&event) == kMIDIUnknownEndpoint);
    assert(MIDIClientDispose(clientA) == noErr);

    puts("ALSA_SOURCE_LIFETIME_PASS: bindings reclaimed on endpoint and client disposal");
    return 0;
}
