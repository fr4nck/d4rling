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
/* Called after virtual source/client disposal, outside objectsMutex. */
void D4MIDIAlsaForgetVirtualSource(MIDIEndpointRef source);
/* Takes the virtual object registry mutex; safe while ALSA binding mutex held. */
int D4MIDIVirtualSourceIsLive(MIDIEndpointRef source);
#ifdef __cplusplus
}
#endif
#endif
