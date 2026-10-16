/*
 * Native ALSA source-port selection contract (no /dev/snd/seq).
 * Uses actual libasound port-info types and the production capability
 * predicate. Device enumeration is a separate runtime gate.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <CoreMIDI/MIDIServices.h>
#include <alsa/asoundlib.h>
#include "MIDIAlsaBridge.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    snd_seq_port_info_t *info = NULL;
    const unsigned int read = SND_SEQ_PORT_CAP_READ;
    const unsigned int subscribe_read = SND_SEQ_PORT_CAP_SUBS_READ;
    const unsigned int write = SND_SEQ_PORT_CAP_WRITE;
    const unsigned int subscribe_write = SND_SEQ_PORT_CAP_SUBS_WRITE;
    const unsigned int private_port = SND_SEQ_PORT_CAP_NO_EXPORT;
    const struct {
        unsigned int capabilities;
        int expected;
    } cases[] = {
        {0, 0},
        {read, 0},
        {subscribe_read, 0},
        {read | subscribe_read, 1},
        {write | subscribe_write, 0},
        {read | write, 0},
        {read | subscribe_read | write | subscribe_write, 1},
        {read | subscribe_read | private_port, 0},
        {read | subscribe_read | write | private_port, 0},
        {read | private_port, 0},
        {private_port, 0}
    };
    size_t index;
    int client = 123, port = 124;

    assert(snd_seq_port_info_malloc(&info) == 0);
    assert(info != NULL);
    for (index = 0; index < sizeof(cases) / sizeof(cases[0]); ++index) {
        snd_seq_port_info_set_capability(info, cases[index].capabilities);
        assert(D4MIDIAlsaSourcePortIsConnectable(
                   snd_seq_port_info_get_capability(info)) == cases[index].expected);
    }
    snd_seq_port_info_free(info);

    /* Null output pointers must be rejected before any sequencer open. */
    assert(D4MIDIAlsaSourceAddressAt(0, NULL, &port) == paramErr);
    assert(D4MIDIAlsaSourceAddressAt(0, &client, NULL) == paramErr);
    assert(client == 123 && port == 124);

    puts("ALSA_SOURCE_FILTER_PASS: readable subscription ports selected");
    return 0;
}
