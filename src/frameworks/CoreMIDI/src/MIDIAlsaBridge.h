#ifndef D4R_COREMIDI_ALSA_BRIDGE_H
#define D4R_COREMIDI_ALSA_BRIDGE_H
#include <CoreMIDI/MIDIServices.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Internal bridge: direct destination enumeration and immediate Note On/Off. */
ItemCount D4MIDIAlsaDestinationCount(void);
MIDIEndpointRef D4MIDIAlsaDestinationAt(ItemCount index);
OSStatus D4MIDIAlsaSend(MIDIEndpointRef destination, const MIDIPacketList *packets);
#ifdef __cplusplus
}
#endif
#endif
