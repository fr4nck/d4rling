#ifndef D4R_COREMIDI_ALSA_BRIDGE_H
#define D4R_COREMIDI_ALSA_BRIDGE_H
#include <CoreMIDI/MIDIServices.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Internal bridge: ALSA output and virtual source-lifetime integration. */
ItemCount D4MIDIAlsaDestinationCount(void);
MIDIEndpointRef D4MIDIAlsaDestinationAt(ItemCount index);
OSStatus D4MIDIAlsaSend(MIDIEndpointRef destination, const MIDIPacketList *packets);
/*
 * Internal-only ALSA source-address enumeration. Does not allocate virtual
 * endpoints, subscribe to a port or poll sequencer events. Addresses are
 * snapshots, not stable device identifiers.
 */
ItemCount D4MIDIAlsaSourceAddressCount(void);
OSStatus D4MIDIAlsaSourceAddressAt(ItemCount index, int *client, int *port);
/* Predicate is provided by the ALSA-enabled backend; no device is opened. */
int D4MIDIAlsaSourcePortIsConnectable(unsigned int capabilities);
/* Caller supplies an already-open NONBLOCKING ALSA input sequencer.
 * This consumes at most budget events, routing bound MIDI 1.0 events.
 * Compiled only when the experimental ALSA bridge is enabled.
 */
#ifdef DARLING_COREMIDI_WITH_ALSA
struct _snd_seq;
OSStatus D4MIDIAlsaPumpNonblocking(struct _snd_seq *sequencer,
                                  ItemCount budget, ItemCount *delivered);
/* Internal single-source session. Must be zero-initialized by caller.
 * Caller serializes its lifecycle and pump operations on one thread.
 * No worker thread, device hotplug or automatic endpoint creation.
 */
typedef struct {
    struct _snd_seq *sequencer;
    int input_port;
    int sender_client;
    int sender_port;
    int subscribed;
    int pumping; /* callback-initiated close/unsubscribe is rejected */
} D4MIDIAlsaInputSession;
OSStatus D4MIDIAlsaInputSessionOpen(D4MIDIAlsaInputSession *session);
OSStatus D4MIDIAlsaInputSessionSubscribe(D4MIDIAlsaInputSession *session,
                                        int client, int port,
                                        MIDIEndpointRef source);
OSStatus D4MIDIAlsaInputSessionUnsubscribe(D4MIDIAlsaInputSession *session);
OSStatus D4MIDIAlsaInputSessionPump(D4MIDIAlsaInputSession *session,
                                   ItemCount budget, ItemCount *delivered);
OSStatus D4MIDIAlsaInputSessionClose(D4MIDIAlsaInputSession *session);
#endif
/* Called after virtual source/client disposal, outside objectsMutex. */
void D4MIDIAlsaForgetVirtualSource(MIDIEndpointRef source);
/* Takes the virtual object registry mutex; safe while ALSA binding mutex held. */
int D4MIDIVirtualSourceIsLive(MIDIEndpointRef source);
#ifdef __cplusplus
}
#endif
#endif
