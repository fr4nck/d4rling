#ifndef __MIDIServices_h__
#define __MIDIServices_h__

#include <CoreFoundation/CoreFoundation.h>
#include <stddef.h>

/* CoreMIDI 1.0-compatible declarations used by the virtual-only MVP. */
typedef UInt32 MIDIObjectRef;
typedef MIDIObjectRef MIDIClientRef;
typedef MIDIObjectRef MIDIPortRef;
typedef MIDIObjectRef MIDIEndpointRef;
typedef UInt64 MIDITimeStamp;

typedef struct MIDINotification {
    SInt32 messageID;
    UInt32 messageSize;
} MIDINotification;
typedef void (*MIDINotifyProc)(const MIDINotification *, void *);

#if defined(__arm__) || defined(__aarch64__)
#pragma pack(push, 4)
#else
#pragma pack(push, 1)
#endif
typedef struct MIDIPacket {
    MIDITimeStamp timeStamp;
    UInt16 length;
    Byte data[256];
} MIDIPacket;
typedef struct MIDIPacketList {
    UInt32 numPackets;
    MIDIPacket packet[1];
} MIDIPacketList;
#pragma pack(pop)

/* On Intel, CoreMIDI uses unaligned packed packet records; ARM pads to 4 bytes. */
static inline MIDIPacket *MIDIPacketNext(const MIDIPacket *packet)
{
    size_t stride = offsetof(MIDIPacket, data) + packet->length;
#if defined(__arm__) || defined(__aarch64__)
    stride = (stride + 3u) & ~(size_t)3u;
#endif
    return (MIDIPacket *)((const Byte *)packet + stride);
}

typedef void (*MIDIReadProc)(const MIDIPacketList *, void *, void *);

enum {
    kMIDIInvalidClient = -10830,
    kMIDIInvalidPort = -10831,
    kMIDIWrongEndpointType = -10832,
    kMIDINoConnection = -10833,
    kMIDIUnknownEndpoint = -10834,
    kMIDIMessageSendErr = -10838
};

#ifdef __cplusplus
extern "C" {
#endif
OSStatus MIDIClientCreate(CFStringRef, MIDINotifyProc, void *, MIDIClientRef *);
OSStatus MIDIClientDispose(MIDIClientRef);
OSStatus MIDIInputPortCreate(MIDIClientRef, CFStringRef, MIDIReadProc, void *, MIDIPortRef *);
OSStatus MIDIOutputPortCreate(MIDIClientRef, CFStringRef, MIDIPortRef *);
OSStatus MIDIPortDispose(MIDIPortRef);
OSStatus MIDISourceCreate(MIDIClientRef, CFStringRef, MIDIEndpointRef *);
OSStatus MIDIDestinationCreate(MIDIClientRef, CFStringRef, MIDIReadProc, void *, MIDIEndpointRef *);
OSStatus MIDIEndpointDispose(MIDIEndpointRef);
ItemCount MIDIGetNumberOfSources(void);
ItemCount MIDIGetNumberOfDestinations(void);
MIDIEndpointRef MIDIGetSource(ItemCount);
MIDIEndpointRef MIDIGetDestination(ItemCount);
OSStatus MIDIPortConnectSource(MIDIPortRef, MIDIEndpointRef, void *);
OSStatus MIDIPortDisconnectSource(MIDIPortRef, MIDIEndpointRef);
OSStatus MIDISend(MIDIPortRef, MIDIEndpointRef, const MIDIPacketList *);
OSStatus MIDIReceived(MIDIEndpointRef, const MIDIPacketList *);
MIDIPacket *MIDIPacketListInit(MIDIPacketList *);
MIDIPacket *MIDIPacketListAdd(MIDIPacketList *, ByteCount, MIDIPacket *, MIDITimeStamp, ByteCount, const Byte *);
#ifdef __cplusplus
}
#endif

/* Identification */
extern const CFStringRef kMIDIPropertyName API_AVAILABLE(macos(10.0));
extern const CFStringRef kMIDIPropertyManufacturer API_AVAILABLE(macos(10.0));
extern const CFStringRef kMIDIPropertyUniqueID API_AVAILABLE(macos(10.0));
/* Presentation */
extern const CFStringRef kMIDIPropertyDisplayName API_AVAILABLE(macos(10.4));
/* Timing */
extern const CFStringRef kMIDIPropertyAdvanceScheduleTimeMuSec API_AVAILABLE(macos(10.0));
/* Drivers */
extern const CFStringRef kMIDIPropertyDriverVersion API_AVAILABLE(macos(10.2));
/* Connections */
extern const CFStringRef kMIDIPropertyConnectionUniqueID API_AVAILABLE(macos(10.1));

#endif
