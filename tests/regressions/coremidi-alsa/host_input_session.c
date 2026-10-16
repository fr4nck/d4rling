/*
 * ALSA input session lifecycle regression. Only the ALSA open/subscribe/
 * input/close entry points are wrapped; real libasound port-info types
 * and the production CoreMIDI/ALSA bridge remain in use.
 * No /dev/snd/seq, device, background thread, or realtime claim.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <CoreMIDI/MIDIServices.h>
#include <alsa/asoundlib.h>
#include "MIDIAlsaBridge.h"
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

extern OSStatus D4MIDIAlsaRouteInputEvent(const snd_seq_event_t *);

static snd_seq_t *const fake = (snd_seq_t *)(uintptr_t)0x1234;
static int open_calls, name_calls, create_calls, info_calls;
static int connect_calls, disconnect_calls, close_calls, input_calls;
static int fail_open, fail_name, fail_create, fail_info, fail_connect;
static int fail_disconnect, fail_close, send_one_event;
static unsigned int sender_caps =
    SND_SEQ_PORT_CAP_READ | SND_SEQ_PORT_CAP_SUBS_READ;
static snd_seq_event_t incoming;

int __wrap_snd_seq_open(snd_seq_t **out, const char *name, int streams, int mode)
{
    ++open_calls;
    assert(out && strcmp(name, "default") == 0);
    assert(streams == SND_SEQ_OPEN_INPUT && mode == SND_SEQ_NONBLOCK);
    *out = fail_open ? NULL : fake;
    return fail_open ? -ENODEV : 0;
}

int __wrap_snd_seq_set_client_name(snd_seq_t *seq, const char *name)
{
    ++name_calls;
    assert(seq == fake);
    assert(strcmp(name, "d4rling CoreMIDI Input") == 0);
    return fail_name ? -EIO : 0;
}

int __wrap_snd_seq_create_simple_port(snd_seq_t *seq, const char *name,
                                       unsigned int caps, unsigned int type)
{
    ++create_calls;
    assert(seq == fake && strcmp(name, "CoreMIDI Input") == 0);
    assert(caps == (SND_SEQ_PORT_CAP_WRITE | SND_SEQ_PORT_CAP_SUBS_WRITE));
    assert((type & SND_SEQ_PORT_TYPE_MIDI_GENERIC) != 0);
    return fail_create ? -EIO : 6;
}

int __wrap_snd_seq_get_any_port_info(snd_seq_t *seq, int client, int port,
                                      snd_seq_port_info_t *info)
{
    ++info_calls;
    assert(seq == fake && client == 42 && port == 7);
    assert(info);
    if (fail_info) return -ENODEV;
    snd_seq_port_info_set_capability(info, sender_caps);
    return 0;
}

int __wrap_snd_seq_connect_from(snd_seq_t *seq, int local,
                                int source_client, int source_port)
{
    ++connect_calls;
    assert(seq == fake && local == 6);
    assert(source_client == 42 && source_port == 7);
    return fail_connect ? -EIO : 0;
}

int __wrap_snd_seq_disconnect_from(snd_seq_t *seq, int local,
                                   int source_client, int source_port)
{
    ++disconnect_calls;
    assert(seq == fake && local == 6);
    assert(source_client == 42 && source_port == 7);
    return fail_disconnect ? -EIO : 0;
}

int __wrap_snd_seq_event_input(snd_seq_t *seq, snd_seq_event_t **event)
{
    ++input_calls;
    assert(seq == fake && event);
    if (send_one_event) {
        send_one_event = 0;
        *event = &incoming;
        return 0;
    }
    *event = NULL;
    return -EAGAIN;
}

int __wrap_snd_seq_close(snd_seq_t *seq)
{
    ++close_calls;
    assert(seq == fake);
    return fail_close ? -EIO : 0;
}

typedef struct { unsigned calls; unsigned status; void *connection;
                 D4MIDIAlsaInputSession *during_pump; } Received;
static void receive(const MIDIPacketList *list, void *context, void *connection)
{
    Received *state = context;
    assert(list && list->numPackets == 1 && list->packet[0].length == 3);
    state->calls++;
    state->status = list->packet[0].data[0];
    state->connection = connection;
    if (state->during_pump) {
        assert(D4MIDIAlsaInputSessionClose(state->during_pump) == paramErr);
        assert(D4MIDIAlsaInputSessionUnsubscribe(state->during_pump) == paramErr);
    }
}

int main(void)
{
    MIDIClientRef client = 0;
    MIDIEndpointRef source = 0;
    MIDIPortRef port = 0;
    Received got = {0};
    D4MIDIAlsaInputSession session = {0}, other = {0};
    ItemCount delivered = 55;
    int previous;

    assert(D4MIDIAlsaInputSessionOpen(NULL) == paramErr);
    assert(D4MIDIAlsaInputSessionSubscribe(&session, 42, 7, 1) == paramErr);
    assert(D4MIDIAlsaInputSessionPump(&session, 1, &delivered) == paramErr);
    assert(delivered == 0);
    assert(D4MIDIAlsaInputSessionClose(&session) == paramErr);
    assert(open_calls == 0);

    fail_open = 1;
    assert(D4MIDIAlsaInputSessionOpen(&session) == kMIDIMessageSendErr);
    assert(session.sequencer == NULL && close_calls == 0);
    fail_open = 0;
    fail_name = 1;
    assert(D4MIDIAlsaInputSessionOpen(&session) == kMIDIMessageSendErr);
    assert(session.sequencer == NULL && close_calls == 1);
    fail_name = 0;
    fail_create = 1;
    assert(D4MIDIAlsaInputSessionOpen(&session) == kMIDIMessageSendErr);
    assert(session.sequencer == NULL && close_calls == 2);
    fail_create = 0;

    assert(MIDIClientCreate(NULL, NULL, NULL, &client) == noErr);
    assert(MIDISourceCreate(client, NULL, &source) == noErr);
    assert(MIDIInputPortCreate(client, NULL, receive, &got, &port) == noErr);
    assert(MIDIPortConnectSource(port, source,
                                (void *)(uintptr_t)0x4321) == noErr);

    assert(D4MIDIAlsaInputSessionOpen(&session) == noErr);
    assert(session.sequencer == fake && session.input_port == 6);
    assert(D4MIDIAlsaInputSessionOpen(&session) == paramErr);
    assert(D4MIDIAlsaInputSessionSubscribe(&session, -1, 7, source) == paramErr);
    assert(D4MIDIAlsaInputSessionSubscribe(&session, 42, 256, source) == paramErr);
    assert(D4MIDIAlsaInputSessionSubscribe(&session, 42, 7, 0) == paramErr);
    assert(D4MIDIAlsaInputSessionSubscribe(&session, 42, 7, 0xfffffff0u)
           == kMIDIUnknownEndpoint);
    assert(connect_calls == 0);

    fail_info = 1;
    assert(D4MIDIAlsaInputSessionSubscribe(&session, 42, 7, source)
           == kMIDIUnknownEndpoint);
    fail_info = 0;
    sender_caps = SND_SEQ_PORT_CAP_WRITE | SND_SEQ_PORT_CAP_SUBS_WRITE;
    assert(D4MIDIAlsaInputSessionSubscribe(&session, 42, 7, source)
           == kMIDIUnknownEndpoint);
    sender_caps = SND_SEQ_PORT_CAP_READ | SND_SEQ_PORT_CAP_SUBS_READ;

    fail_connect = 1;
    assert(D4MIDIAlsaInputSessionSubscribe(&session, 42, 7, source)
           == kMIDIMessageSendErr);
    assert(session.subscribed == 0 && connect_calls == 1);
    snd_seq_ev_set_noteon(&incoming, 0, 60, 100);
    incoming.source.client = 42;
    incoming.source.port = 7;
    assert(D4MIDIAlsaRouteInputEvent(&incoming) == kMIDIUnknownEndpoint);
    fail_connect = 0;

    assert(D4MIDIAlsaInputSessionSubscribe(&session, 42, 7, source) == noErr);
    assert(session.subscribed == 1 && connect_calls == 2);
    assert(D4MIDIAlsaInputSessionSubscribe(&session, 42, 7, source) == paramErr);
    assert(D4MIDIAlsaInputSessionPump(&session, 0, &delivered) == paramErr);
    assert(D4MIDIAlsaInputSessionPump(&session, 4097, &delivered) == paramErr);
    assert(D4MIDIAlsaInputSessionPump(&session, 1, NULL) == paramErr);
    assert(input_calls == 0);

    send_one_event = 1;
    got.during_pump = &session;
    assert(D4MIDIAlsaInputSessionPump(&session, 3, &delivered) == noErr);
    got.during_pump = NULL;
    assert(delivered == 1 && got.calls == 1 && got.status == 0x90);
    assert(got.connection == (void *)(uintptr_t)0x4321);
    assert(input_calls == 2);
    assert(D4MIDIAlsaInputSessionPump(&session, 1, &delivered) == noErr);
    assert(delivered == 0);

    /* A second session cannot claim a source address we already own. */
    assert(D4MIDIAlsaInputSessionOpen(&other) == noErr);
    previous = connect_calls;
    assert(D4MIDIAlsaInputSessionSubscribe(&other, 42, 7, source) == paramErr);
    assert(connect_calls == previous && other.subscribed == 0);
    assert(D4MIDIAlsaInputSessionClose(&other) == noErr);
    assert(D4MIDIAlsaRouteInputEvent(&incoming) == noErr && got.calls == 2);

    fail_disconnect = 1;
    assert(D4MIDIAlsaInputSessionUnsubscribe(&session) == kMIDIMessageSendErr);
    assert(session.subscribed == 1); /* The native link may still exist. */
    assert(D4MIDIAlsaRouteInputEvent(&incoming) == noErr && got.calls == 3);
    fail_disconnect = 0;
    assert(D4MIDIAlsaInputSessionUnsubscribe(&session) == noErr);
    assert(disconnect_calls == 2 && session.subscribed == 0);
    assert(D4MIDIAlsaRouteInputEvent(&incoming) == kMIDIUnknownEndpoint);
    assert(D4MIDIAlsaInputSessionUnsubscribe(&session) == paramErr);
    assert(D4MIDIAlsaInputSessionPump(&session, 1, &delivered) == paramErr);

    assert(D4MIDIAlsaInputSessionSubscribe(&session, 42, 7, source) == noErr);
    assert(D4MIDIAlsaInputSessionClose(&session) == noErr);
    assert(session.sequencer == NULL && session.subscribed == 0);
    assert(D4MIDIAlsaRouteInputEvent(&incoming) == kMIDIUnknownEndpoint);
    assert(D4MIDIAlsaInputSessionClose(&session) == paramErr);

    /* Even if ALSA disconnect fails, remove our binding and close. */
    assert(D4MIDIAlsaInputSessionOpen(&session) == noErr);
    assert(D4MIDIAlsaInputSessionSubscribe(&session, 42, 7, source) == noErr);
    fail_disconnect = 1;
    assert(D4MIDIAlsaInputSessionClose(&session) == kMIDIMessageSendErr);
    assert(session.sequencer == NULL);
    assert(D4MIDIAlsaRouteInputEvent(&incoming) == kMIDIUnknownEndpoint);
    fail_disconnect = 0;

    /* Closing a handle may fail; do not retain a dangling session pointer. */
    assert(D4MIDIAlsaInputSessionOpen(&session) == noErr);
    fail_close = 1;
    assert(D4MIDIAlsaInputSessionClose(&session) == kMIDIMessageSendErr);
    assert(session.sequencer == NULL);
    fail_close = 0;

    assert(MIDIClientDispose(client) == noErr);
    puts("ALSA_INPUT_SESSION_PASS: open, subscribe, receive, rollback and teardown");
    return 0;
}
