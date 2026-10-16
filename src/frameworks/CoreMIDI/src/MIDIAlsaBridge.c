/*
 * Experimental CoreMIDI-to-ALSA sequencer output bridge.
 * GPL-3.0-or-later; no private Apple code.
 * Enumeration and send only; no input polling or realtime scheduling.
 */
#include <CoreMIDI/MIDIServices.h>
#include "MIDIAlsaBridge.h"
#include <stdint.h>

#define D4_ALSA_HANDLE_TAG UINT32_C(0xa0000000)
#define D4_ALSA_HANDLE_MASK UINT32_C(0xffff0000)

#ifdef DARLING_COREMIDI_WITH_ALSA
/* ALSA's *_alloca macros require the alloca declaration with strict C11. */
#include <alloca.h>
#include <alsa/asoundlib.h>
#include <errno.h>
#include <pthread.h>

static pthread_mutex_t g_alsa_lock = PTHREAD_MUTEX_INITIALIZER;
static snd_seq_t *g_seq;
static int g_output_port = -1;

/* Explicit ALSA client/port -> in-process CoreMIDI source bindings.
 * These are NOT native source discovery, hotplug or subscription support.
 * The table is independent of the output-only ALSA sequencer handle.
 */
#define D4_ALSA_INPUT_BINDING_LIMIT 128
typedef struct {
    int client;
    int port;
    MIDIEndpointRef source; /* 0 indicates an unused entry */
} D4MIDIAlsaInputBinding;

static pthread_mutex_t g_input_binding_lock = PTHREAD_MUTEX_INITIALIZER;
static D4MIDIAlsaInputBinding g_input_bindings[D4_ALSA_INPUT_BINDING_LIMIT];


static int open_sequencer(void)
{
    if (g_seq) return 0;
    if (snd_seq_open(&g_seq, "default", SND_SEQ_OPEN_OUTPUT, SND_SEQ_NONBLOCK) < 0) {
        g_seq = NULL;
        return -1;
    }
    snd_seq_set_client_name(g_seq, "d4rling CoreMIDI");
    g_output_port = snd_seq_create_simple_port(g_seq, "CoreMIDI Output",
        SND_SEQ_PORT_CAP_READ | SND_SEQ_PORT_CAP_SUBS_READ,
        SND_SEQ_PORT_TYPE_MIDI_GENERIC | SND_SEQ_PORT_TYPE_APPLICATION);
    if (g_output_port < 0) {
        snd_seq_close(g_seq);
        g_seq = NULL;
        return -1;
    }
    return 0;
}

/* Endpoint handles are not persistent across ALSA restarts. */
static MIDIEndpointRef make_handle(int client, int port)
{
    if (client < 0 || client > 255 || port < 0 || port > 255) return 0;
    return D4_ALSA_HANDLE_TAG | ((UInt32)client << 8) | (UInt32)port;
}

/* Caller holds g_alsa_lock. Returns count or the endpoint at index. */
static ItemCount scan_destinations(ItemCount wanted, MIDIEndpointRef *selected)
{
    snd_seq_client_info_t *ci;
    snd_seq_port_info_t *pi;
    ItemCount count = 0;
    snd_seq_client_info_alloca(&ci);
    snd_seq_port_info_alloca(&pi);
    snd_seq_client_info_set_client(ci, -1);
    while (snd_seq_query_next_client(g_seq, ci) >= 0) {
        int client = snd_seq_client_info_get_client(ci);
        if (client == snd_seq_client_id(g_seq)) continue;
        snd_seq_port_info_set_client(pi, client);
        snd_seq_port_info_set_port(pi, -1);
        while (snd_seq_query_next_port(g_seq, pi) >= 0) {
            int port = snd_seq_port_info_get_port(pi);
            unsigned int caps = snd_seq_port_info_get_capability(pi);
            MIDIEndpointRef h;
            if (!(caps & SND_SEQ_PORT_CAP_WRITE)) continue;
            h = make_handle(client, port);
            if (!h) continue;
            if (selected && wanted == count) *selected = h;
            ++count;
        }
    }
    return count;
}

/*
 * An ALSA MIDI input candidate must be readable and allow external
 * read-side subscriptions. Ports flagged NO_EXPORT cannot be subscribed to
 * from another ALSA client. This predicate requires no sequencer device.
 */
int D4MIDIAlsaSourcePortIsConnectable(unsigned int capabilities)
{
    const unsigned int required = SND_SEQ_PORT_CAP_READ |
                                  SND_SEQ_PORT_CAP_SUBS_READ;
    return (capabilities & required) == required &&
           !(capabilities & SND_SEQ_PORT_CAP_NO_EXPORT);
}

/*
 * Enumerate ALSA sender addresses separately from CoreMIDI virtual sources.
 * Caller holds g_alsa_lock. This does not subscribe, receive, or create a
 * CoreMIDI endpoint. Addresses may change after scan if clients disappear.
 */
static ItemCount scan_sources(ItemCount wanted, int *selectedClient,
                              int *selectedPort)
{
    snd_seq_client_info_t *ci;
    snd_seq_port_info_t *pi;
    ItemCount count = 0;
    snd_seq_client_info_alloca(&ci);
    snd_seq_port_info_alloca(&pi);
    snd_seq_client_info_set_client(ci, -1);
    while (snd_seq_query_next_client(g_seq, ci) >= 0) {
        int client = snd_seq_client_info_get_client(ci);
        if (client == snd_seq_client_id(g_seq)) continue;
        if (client < 0 || client > 255) continue;
        snd_seq_port_info_set_client(pi, client);
        snd_seq_port_info_set_port(pi, -1);
        while (snd_seq_query_next_port(g_seq, pi) >= 0) {
            int port = snd_seq_port_info_get_port(pi);
            unsigned int caps = snd_seq_port_info_get_capability(pi);
            if (port < 0 || port > 255 ||
                !D4MIDIAlsaSourcePortIsConnectable(caps))
                continue;
            if (selectedClient && selectedPort && wanted == count) {
                *selectedClient = client;
                *selectedPort = port;
            }
            ++count;
        }
    }
    return count;
}

ItemCount D4MIDIAlsaSourceAddressCount(void)
{
    ItemCount count = 0;
    pthread_mutex_lock(&g_alsa_lock);
    if (open_sequencer() == 0) count = scan_sources(0, NULL, NULL);
    pthread_mutex_unlock(&g_alsa_lock);
    return count;
}

OSStatus D4MIDIAlsaSourceAddressAt(ItemCount index, int *client, int *port)
{
    OSStatus result = kMIDIUnknownEndpoint;
    ItemCount count;
    if (!client || !port) return paramErr;
    *client = -1;
    *port = -1;
    pthread_mutex_lock(&g_alsa_lock);
    if (open_sequencer() == 0) {
        count = scan_sources(index, client, port);
        if (index < count && *client >= 0 && *port >= 0)
            result = noErr;
    }
    pthread_mutex_unlock(&g_alsa_lock);
    return result;
}

ItemCount D4MIDIAlsaDestinationCount(void)
{
    ItemCount result = 0;
    pthread_mutex_lock(&g_alsa_lock);
    if (open_sequencer() == 0) result = scan_destinations(0, NULL);
    pthread_mutex_unlock(&g_alsa_lock);
    return result;
}

MIDIEndpointRef D4MIDIAlsaDestinationAt(ItemCount index)
{
    MIDIEndpointRef result = 0;
    pthread_mutex_lock(&g_alsa_lock);
    if (open_sequencer() == 0) (void)scan_destinations(index, &result);
    pthread_mutex_unlock(&g_alsa_lock);
    return result;
}

/*
 * Convert one complete MIDI 1.0 channel message into an ALSA event.
 * A MIDIPacket holds exactly one supported message in this experimental
 * backend. Running status, SysEx and system messages are not implemented.
 * No /dev/snd/seq access: shared by the preflight gate and the sender.
 */
OSStatus D4MIDIAlsaTranslate(const MIDIPacket *packet, snd_seq_event_t *event)
{
    unsigned int opcode, channel, status;
    unsigned int expected_length;
    if (!packet || !event) return paramErr;
    if (packet->length < 2 || packet->length > 3) return kMIDIMessageSendErr;
    status = packet->data[0];
    if (status < 0x80 || status >= 0xf0) return kMIDIMessageSendErr;
    opcode = status & 0xf0u;
    expected_length = (opcode == 0xc0 || opcode == 0xd0) ? 2u : 3u;
    if (packet->length != expected_length ||
        (packet->data[1] & 0x80u) ||
        (expected_length == 3 && (packet->data[2] & 0x80u)))
        return kMIDIMessageSendErr;

    channel = status & 0x0fu;
    snd_seq_ev_clear(event);
    switch (opcode) {
    case 0x80:
        snd_seq_ev_set_noteoff(event, channel, packet->data[1], packet->data[2]);
        break;
    case 0x90:
        /* MIDI Note On with velocity zero is semantically a Note Off. */
        if (packet->data[2] == 0)
            snd_seq_ev_set_noteoff(event, channel, packet->data[1], 0);
        else
            snd_seq_ev_set_noteon(event, channel, packet->data[1], packet->data[2]);
        break;
    case 0xa0:
        snd_seq_ev_set_keypress(event, channel, packet->data[1], packet->data[2]);
        break;
    case 0xb0:
        snd_seq_ev_set_controller(event, channel, packet->data[1], packet->data[2]);
        break;
    case 0xc0:
        snd_seq_ev_set_pgmchange(event, channel, packet->data[1]);
        break;
    case 0xd0:
        snd_seq_ev_set_chanpress(event, channel, packet->data[1]);
        break;
    case 0xe0:
        snd_seq_ev_set_pitchbend(event, channel,
                                ((int)packet->data[1] |
                                 ((int)packet->data[2] << 7)) - 8192);
        break;
    default:
        return kMIDIMessageSendErr;
    }
    return noErr;
}

/*
 * Encode one ALSA sequencer channel event into a complete MIDI 1.0 message.
 * No sequencer access or callback dispatch; reserved for future input support.
 * An unsupported or out-of-range event leaves the caller's bytes untouched.
 */
OSStatus D4MIDIAlsaEncodeEvent(const snd_seq_event_t *event, Byte *data,
                              ByteCount capacity, ByteCount *length)
{
    unsigned int opcode, channel, first = 0, second = 0;
    ByteCount needed = 3;
    int value;
    if (!event || !data || !length) return paramErr;
    *length = 0;
    switch (event->type) {
    case SND_SEQ_EVENT_NOTEOFF:
        opcode = 0x80;
        channel = event->data.note.channel;
        first = event->data.note.note;
        second = event->data.note.velocity;
        break;
    case SND_SEQ_EVENT_NOTEON:
        opcode = 0x90;
        channel = event->data.note.channel;
        first = event->data.note.note;
        second = event->data.note.velocity;
        break;
    case SND_SEQ_EVENT_KEYPRESS:
        opcode = 0xa0;
        channel = event->data.note.channel;
        first = event->data.note.note;
        second = event->data.note.velocity;
        break;
    case SND_SEQ_EVENT_CONTROLLER:
        opcode = 0xb0;
        channel = event->data.control.channel;
        first = event->data.control.param;
        value = event->data.control.value;
        if (value < 0 || value > 127) return kMIDIMessageSendErr;
        second = (unsigned int)value;
        break;
    case SND_SEQ_EVENT_PGMCHANGE:
        opcode = 0xc0;
        channel = event->data.control.channel;
        value = event->data.control.value;
        if (value < 0 || value > 127) return kMIDIMessageSendErr;
        first = (unsigned int)value;
        needed = 2;
        break;
    case SND_SEQ_EVENT_CHANPRESS:
        opcode = 0xd0;
        channel = event->data.control.channel;
        value = event->data.control.value;
        if (value < 0 || value > 127) return kMIDIMessageSendErr;
        first = (unsigned int)value;
        needed = 2;
        break;
    case SND_SEQ_EVENT_PITCHBEND:
        opcode = 0xe0;
        channel = event->data.control.channel;
        value = event->data.control.value;
        if (value < -8192 || value > 8191) return kMIDIMessageSendErr;
        first = (unsigned int)(value + 8192) & 0x7fu;
        second = ((unsigned int)(value + 8192) >> 7) & 0x7fu;
        break;
    default:
        return kMIDIMessageSendErr;
    }
    if (channel > 15 || first > 127 || second > 127)
        return kMIDIMessageSendErr;
    if (capacity < needed) return paramErr;
    data[0] = (Byte)(opcode | channel);
    data[1] = (Byte)first;
    if (needed == 3) data[2] = (Byte)second;
    *length = needed;
    return noErr;
}

/*
 * Deliver a decoded ALSA channel event through an existing CoreMIDI virtual
 * source and its connected input ports. This does NOT open an ALSA input,
 * enumerate native sources or subscribe to an ALSA port.
 *
 * No persistent packet storage is used: MIDIReceived invokes callbacks
 * synchronously with this on-stack packet list.
 */
OSStatus D4MIDIAlsaDeliverToVirtualSource(MIDIEndpointRef source,
                                        const snd_seq_event_t *event)
{
    union { long double align; Byte bytes[64]; } storage;
    MIDIPacketList *list = (MIDIPacketList *)storage.bytes;
    MIDIPacket *packet;
    Byte data[3];
    ByteCount length = 0;
    OSStatus status;

    status = D4MIDIAlsaEncodeEvent(event, data, sizeof(data), &length);
    if (status != noErr) return status;
    packet = MIDIPacketListInit(list);
    if (!packet || !MIDIPacketListAdd(list, sizeof(storage.bytes), packet,
                                      0, length, data))
        return kMIDIMessageSendErr;
    return MIDIReceived(source, list);
}

/*
 * Bind one native ALSA sender address to an existing virtual CoreMIDI source.
 * This is a manual mapping until ALSA discovery and input subscriptions exist.
 * No ALSA sequencer device is opened here.
 */
static OSStatus bindSourceAddress(int client, int port,
                                  MIDIEndpointRef source, int idempotent)
{
    size_t slot, vacant = D4_ALSA_INPUT_BINDING_LIMIT;
    if (client < 0 || client > 255 || port < 0 || port > 255 || !source)
        return paramErr;

    pthread_mutex_lock(&g_input_binding_lock);
    /* Revalidate under binding mutex so source disposal cannot leave a
     * stale binding after a successful cleanup. Lock order:
     * binding mutex -> virtual objectsMutex. Disposal releases objectsMutex
     * before acquiring binding mutex to purge the source.
     */
    if (!D4MIDIVirtualSourceIsLive(source)) {
        pthread_mutex_unlock(&g_input_binding_lock);
        return kMIDIUnknownEndpoint;
    }
    for (slot = 0; slot < D4_ALSA_INPUT_BINDING_LIMIT; ++slot) {
        D4MIDIAlsaInputBinding *binding = &g_input_bindings[slot];
        if (binding->source && binding->client == client && binding->port == port) {
            OSStatus status = idempotent && binding->source == source
                                ? noErr : paramErr;
            pthread_mutex_unlock(&g_input_binding_lock);
            return status;
        }
        if (!binding->source && vacant == D4_ALSA_INPUT_BINDING_LIMIT)
            vacant = slot;
    }
    if (vacant == D4_ALSA_INPUT_BINDING_LIMIT) {
        pthread_mutex_unlock(&g_input_binding_lock);
        return kMIDIMessageSendErr;
    }
    g_input_bindings[vacant].client = client;
    g_input_bindings[vacant].port = port;
    g_input_bindings[vacant].source = source;
    pthread_mutex_unlock(&g_input_binding_lock);
    return noErr;
}

OSStatus D4MIDIAlsaBindSourceAddress(int client, int port, MIDIEndpointRef source)
{
    return bindSourceAddress(client, port, source, 1);
}



/* Remove all bindings for a disposed virtual source, including aliases.
 * The dispatcher does not hold the binding mutex during user callbacks.
 */
void D4MIDIAlsaForgetVirtualSource(MIDIEndpointRef source)
{
    size_t slot;
    if (!source) return;
    pthread_mutex_lock(&g_input_binding_lock);
    for (slot = 0; slot < D4_ALSA_INPUT_BINDING_LIMIT; ++slot)
        if (g_input_bindings[slot].source == source)
            g_input_bindings[slot].source = 0;
    pthread_mutex_unlock(&g_input_binding_lock);
}

OSStatus D4MIDIAlsaUnbindSourceAddress(int client, int port)
{
    size_t slot;
    if (client < 0 || client > 255 || port < 0 || port > 255)
        return paramErr;
    pthread_mutex_lock(&g_input_binding_lock);
    for (slot = 0; slot < D4_ALSA_INPUT_BINDING_LIMIT; ++slot) {
        D4MIDIAlsaInputBinding *binding = &g_input_bindings[slot];
        if (binding->source && binding->client == client && binding->port == port) {
            binding->source = 0;
            pthread_mutex_unlock(&g_input_binding_lock);
            return noErr;
        }
    }
    pthread_mutex_unlock(&g_input_binding_lock);
    return kMIDINoConnection;
}

/*
 * The event must originate from a caller-supplied ALSA input event.
 * Only previously bound source addresses are accepted. The binding lock
 * is never held across CoreMIDI user callbacks (which may themselves unbind).
 * Concurrent unbinding does not cancel a delivery already in progress.
 */
OSStatus D4MIDIAlsaRouteInputEvent(const snd_seq_event_t *event)
{
    size_t slot;
    MIDIEndpointRef source = 0;
    if (!event) return paramErr;
    pthread_mutex_lock(&g_input_binding_lock);
    for (slot = 0; slot < D4_ALSA_INPUT_BINDING_LIMIT; ++slot) {
        const D4MIDIAlsaInputBinding *binding = &g_input_bindings[slot];
        if (binding->source &&
            binding->client == event->source.client &&
            binding->port == event->source.port) {
            source = binding->source;
            break;
        }
    }
    pthread_mutex_unlock(&g_input_binding_lock);
    if (!source) return kMIDIUnknownEndpoint;
    return D4MIDIAlsaDeliverToVirtualSource(source, event);
}


/*
 * Consume up to budget queued events from a caller-owned NONBLOCKING ALSA
 * input sequencer. No input handle, port, subscription or thread is created.
 * Unbound/unsupported MIDI channel events are discarded; unexpected errors
 * from ALSA or the CoreMIDI router are reported to the caller.
 *
 * ALSA 1.2.x owns the event storage returned by snd_seq_event_input:
 * consume it synchronously before requesting the next event. Calling the
 * deprecated snd_seq_free_event() is not required.
 */
OSStatus D4MIDIAlsaPumpNonblocking(struct _snd_seq *sequencer,
                                  ItemCount budget, ItemCount *delivered)
{
    ItemCount i;
    if (delivered) *delivered = 0;
    if (!sequencer || !delivered || !budget || budget > 4096)
        return paramErr;
    for (i = 0; i < budget; ++i) {
        snd_seq_event_t *event = NULL;
        OSStatus result;
        int status = snd_seq_event_input(sequencer, &event);
        if (status == -EAGAIN)
            return noErr;
        if (status < 0 || !event)
            return kMIDIMessageSendErr;

        result = D4MIDIAlsaRouteInputEvent(event);
        if (result == noErr) {
            ++*delivered;
        } else if (result != kMIDIUnknownEndpoint &&
                   result != kMIDIMessageSendErr) {
            return result;
        }
    }
    return noErr;
}


/*
 * Minimal explicit ALSA input session. The caller serializes Open/Subscribe/
 * Pump/Close (including callback-initiated teardown) and owns its storage.
 * No worker thread, hotplug tracking, or automatic CoreMIDI endpoint.
 */
OSStatus D4MIDIAlsaInputSessionOpen(D4MIDIAlsaInputSession *session)
{
    snd_seq_t *sequencer = NULL;
    int port;
    if (!session || session->sequencer || session->pumping) return paramErr;
    if (snd_seq_open(&sequencer, "default", SND_SEQ_OPEN_INPUT,
                     SND_SEQ_NONBLOCK) < 0 || !sequencer)
        return kMIDIMessageSendErr;
    if (snd_seq_set_client_name(sequencer, "d4rling CoreMIDI Input") < 0) {
        snd_seq_close(sequencer);
        return kMIDIMessageSendErr;
    }
    port = snd_seq_create_simple_port(sequencer, "CoreMIDI Input",
        SND_SEQ_PORT_CAP_WRITE | SND_SEQ_PORT_CAP_SUBS_WRITE,
        SND_SEQ_PORT_TYPE_MIDI_GENERIC | SND_SEQ_PORT_TYPE_APPLICATION);
    if (port < 0) {
        snd_seq_close(sequencer);
        return kMIDIMessageSendErr;
    }
    session->sequencer = sequencer;
    session->input_port = port;
    session->subscribed = 0;
    session->pumping = 0;
    return noErr;
}

OSStatus D4MIDIAlsaInputSessionSubscribe(D4MIDIAlsaInputSession *session,
                                        int client, int port,
                                        MIDIEndpointRef source)
{
    snd_seq_port_info_t *info;
    OSStatus status;
    if (!session || !session->sequencer || session->subscribed ||
        session->pumping || client < 0 || client > 255 || port < 0 || port > 255 || !source)
        return paramErr;
    snd_seq_port_info_alloca(&info);
    if (snd_seq_get_any_port_info(session->sequencer, client, port, info) < 0 ||
        !D4MIDIAlsaSourcePortIsConnectable(
            snd_seq_port_info_get_capability(info)))
        return kMIDIUnknownEndpoint;

    /* Claim the address exclusively. Duplicate bindings must not be
     * unbound by a failed subscription or by this session's teardown.
     */
    status = bindSourceAddress(client, port, source, 0);
    if (status != noErr) return status;
    if (snd_seq_connect_from(session->sequencer, session->input_port,
                             client, port) < 0) {
        (void)D4MIDIAlsaUnbindSourceAddress(client, port);
        return kMIDIMessageSendErr;
    }
    session->sender_client = client;
    session->sender_port = port;
    session->subscribed = 1;
    return noErr;
}

OSStatus D4MIDIAlsaInputSessionUnsubscribe(D4MIDIAlsaInputSession *session)
{
    int result;
    if (!session || !session->sequencer || !session->subscribed ||
        session->pumping)
        return paramErr;
    result = snd_seq_disconnect_from(session->sequencer, session->input_port,
                                     session->sender_client, session->sender_port);
    if (result < 0)
        return kMIDIMessageSendErr; /* Still subscribed: safe to retry. */
    (void)D4MIDIAlsaUnbindSourceAddress(session->sender_client,
                                        session->sender_port);
    session->subscribed = 0;
    return noErr;
}

OSStatus D4MIDIAlsaInputSessionPump(D4MIDIAlsaInputSession *session,
                                   ItemCount budget, ItemCount *delivered)
{
    OSStatus status;
    if (delivered) *delivered = 0;
    if (!session || !session->sequencer || !session->subscribed ||
        session->pumping)
        return paramErr;
    session->pumping = 1;
    status = D4MIDIAlsaPumpNonblocking(session->sequencer, budget, delivered);
    session->pumping = 0;
    return status;
}

OSStatus D4MIDIAlsaInputSessionClose(D4MIDIAlsaInputSession *session)
{
    int result;
    OSStatus status = noErr;
    if (!session || !session->sequencer || session->pumping)
        return paramErr;
    if (session->subscribed) {
        status = D4MIDIAlsaInputSessionUnsubscribe(session);
        if (session->subscribed) {
            /* Disconnect failed: close still destroys the native link;
             * release the binding even though unsubscribe could not.
             */
            (void)D4MIDIAlsaUnbindSourceAddress(session->sender_client,
                                                 session->sender_port);
        }
    }
    result = snd_seq_close(session->sequencer);
    session->sequencer = NULL;
    session->input_port = 0;
    session->sender_client = 0;
    session->sender_port = 0;
    session->subscribed = 0;
    session->pumping = 0;
    if (result < 0) status = kMIDIMessageSendErr;
    return status;
}

OSStatus D4MIDIAlsaSend(MIDIEndpointRef destination, const MIDIPacketList *packets)
{
    OSStatus status = kMIDIUnknownEndpoint;
    ItemCount i;
    snd_seq_port_info_t *destination_info;
    const MIDIPacket *packet;
    if ((destination & D4_ALSA_HANDLE_MASK) != D4_ALSA_HANDLE_TAG)
        return kMIDIUnknownEndpoint;
    if (!packets || !packets->numPackets || packets->numPackets > 4096)
        return paramErr;

    /*
     * Validate all packets before sending any event. This prevents a late
     * unsupported MIDI message from causing a partial ALSA transmission.
     * Caller-supplied MIDIPacketList has no buffer-capacity argument; a
     * corrupted packet pointer cannot be made memory-safe here.
     */
    packet = &packets->packet[0];
    for (i = 0; i < packets->numPackets; ++i) {
        snd_seq_event_t probe;
        if (D4MIDIAlsaTranslate(packet, &probe) != noErr)
            return kMIDIMessageSendErr;
        if (i + 1 < packets->numPackets) packet = MIDIPacketNext(packet);
    }

    pthread_mutex_lock(&g_alsa_lock);
    if (open_sequencer() != 0) {
        status = kMIDIMessageSendErr;
        goto done;
    }
    snd_seq_port_info_alloca(&destination_info);
    if (snd_seq_get_any_port_info(g_seq, (destination >> 8) & 255,
                                  destination & 255, destination_info) < 0 ||
        !(snd_seq_port_info_get_capability(destination_info) & SND_SEQ_PORT_CAP_WRITE))
        goto done;
    status = noErr;
    packet = &packets->packet[0];
    for (i = 0; i < packets->numPackets; ++i) {
        snd_seq_event_t event;
        if (D4MIDIAlsaTranslate(packet, &event) != noErr) {
            status = kMIDIMessageSendErr;
            break;
        }
        snd_seq_ev_set_source(&event, g_output_port);
        snd_seq_ev_set_dest(&event, (destination >> 8) & 255, destination & 255);
        snd_seq_ev_set_direct(&event);
        if (snd_seq_event_output_direct(g_seq, &event) < 0) {
            status = kMIDIMessageSendErr;
            break;
        }
        if (i + 1 < packets->numPackets) packet = MIDIPacketNext(packet);
    }
done:
    pthread_mutex_unlock(&g_alsa_lock);
    return status;
}

#else
/* Explicit no-ALSA fallback: isolated builds never depend on host MIDI. */
/* No ALSA library: no native source address enumeration is available. */
int D4MIDIAlsaSourcePortIsConnectable(unsigned int capabilities)
{
    (void)capabilities;
    return 0;
}

ItemCount D4MIDIAlsaSourceAddressCount(void) { return 0; }
OSStatus D4MIDIAlsaSourceAddressAt(ItemCount index, int *client, int *port)
{
    (void)index;
    if (!client || !port) return paramErr;
    *client = -1;
    *port = -1;
    return kMIDIUnknownEndpoint;
}
void D4MIDIAlsaForgetVirtualSource(MIDIEndpointRef source)
{
    (void)source;
}
ItemCount D4MIDIAlsaDestinationCount(void) { return 0; }
MIDIEndpointRef D4MIDIAlsaDestinationAt(ItemCount index)
{
    (void)index;
    return 0;
}
OSStatus D4MIDIAlsaSend(MIDIEndpointRef endpoint, const MIDIPacketList *packets)
{
    (void)endpoint;
    (void)packets;
    return kMIDIUnknownEndpoint;
}
#endif
