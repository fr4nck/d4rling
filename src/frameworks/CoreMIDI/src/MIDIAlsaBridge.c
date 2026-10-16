/*
 * Experimental CoreMIDI-to-ALSA sequencer output bridge.
 * GPL-3.0-or-later; no private Apple code.
 * Enumeration and send only; no input polling or realtime scheduling.
 */
#include <CoreMIDI/MIDIServices.h>
#include <stdint.h>

#define D4_ALSA_HANDLE_TAG UINT32_C(0xa0000000)
#define D4_ALSA_HANDLE_MASK UINT32_C(0xffff0000)

#ifdef DARLING_COREMIDI_WITH_ALSA
/* ALSA's *_alloca macros require the alloca declaration with strict C11. */
#include <alloca.h>
#include <alsa/asoundlib.h>
#include <pthread.h>

static pthread_mutex_t g_alsa_lock = PTHREAD_MUTEX_INITIALIZER;
static snd_seq_t *g_seq;
static int g_output_port = -1;

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
