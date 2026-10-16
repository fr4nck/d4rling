/*
 * Minimal in-process CoreMIDI 1.0 virtual endpoint implementation.
 * This is deliberately not an ALSA backend, MIDI server or realtime scheduler.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <CoreMIDI/MIDIServices.h>
#include "MIDIAlsaBridge.h"
#include <pthread.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define VIRTUAL_OBJECT_LIMIT 128
#define VIRTUAL_CONNECTION_LIMIT 128

enum ObjectKind { OBJ_NONE, OBJ_CLIENT, OBJ_INPUT, OBJ_OUTPUT, OBJ_SOURCE, OBJ_DEST };

typedef struct {
    MIDIObjectRef id;
    MIDIClientRef owner;
    enum ObjectKind kind;
    MIDIReadProc readProc;
    void *refCon;
} VirtualObject;

typedef struct {
    MIDIPortRef input;
    MIDIEndpointRef source;
    void *refCon;
    uint64_t generation; /* distinguishes disconnect/reconnect in the same slot */
} VirtualConnection;

static pthread_mutex_t objectsMutex = PTHREAD_MUTEX_INITIALIZER;
static VirtualObject objects[VIRTUAL_OBJECT_LIMIT];
static VirtualConnection connections[VIRTUAL_CONNECTION_LIMIT];
static MIDIObjectRef nextObjectID = 1;
static uint64_t nextConnectionGeneration = 1;

/*
 * Coarse-grained callback lifetime gate. All callback entry and object/
 * connection teardown must acquire this gate before objectsMutex, so a
 * different thread cannot destroy callback refCons during invocation.
 *
 * C11 thread-local depth permits callbacks to dispose/reconnect themselves
 * without deadlocking a non-recursive mutex. The gate is intentionally held
 * across user callbacks; callbacks must not synchronously wait for another
 * thread that is trying to dispose/disconnect CoreMIDI objects. This is
 * a correctness gate, NOT realtime-safe dispatch.
 */
static pthread_mutex_t callbackLifetimeMutex = PTHREAD_MUTEX_INITIALIZER;
static _Thread_local unsigned callbackLifetimeDepth;

static void callbackLifetimeEnter(void)
{
    if (callbackLifetimeDepth == 0)
        pthread_mutex_lock(&callbackLifetimeMutex);
    ++callbackLifetimeDepth;
}

static void callbackLifetimeLeave(void)
{
    if (--callbackLifetimeDepth == 0)
        pthread_mutex_unlock(&callbackLifetimeMutex);
}


static VirtualObject *lookup(MIDIObjectRef id, enum ObjectKind kind)
{
    size_t i;
    for (i = 0; i < VIRTUAL_OBJECT_LIMIT; ++i)
        if (objects[i].id == id && id && (!kind || objects[i].kind == kind))
            return &objects[i];
    return NULL;
}

static VirtualObject *allocate(enum ObjectKind kind, MIDIClientRef owner)
{
    size_t i;
    for (i = 0; i < VIRTUAL_OBJECT_LIMIT; ++i) {
        if (objects[i].kind == OBJ_NONE) {
            if (!nextObjectID)
                return NULL; /* never recycle a potentially stale object ID */
            objects[i].id = nextObjectID++;
            objects[i].owner = owner;
            objects[i].kind = kind;
            return &objects[i];
        }
    }
    return NULL;
}


/* Internal bridge query; the caller may hold the ALSA binding mutex.
 * Never acquire the binding mutex while objectsMutex is held.
 */
int D4MIDIVirtualSourceIsLive(MIDIEndpointRef source)
{
    int live;
    pthread_mutex_lock(&objectsMutex);
    live = lookup(source, OBJ_SOURCE) != NULL;
    pthread_mutex_unlock(&objectsMutex);
    return live;
}

static void pruneConnections(void)
{
    size_t i;
    for (i = 0; i < VIRTUAL_CONNECTION_LIMIT; ++i)
        if (connections[i].input &&
            (!lookup(connections[i].input, OBJ_INPUT) ||
             !lookup(connections[i].source, OBJ_SOURCE)))
            memset(&connections[i], 0, sizeof(connections[i]));
}

OSStatus MIDIClientCreate(CFStringRef name, MIDINotifyProc notify, void *refCon, MIDIClientRef *outClient)
{
    VirtualObject *object;
    (void)name; (void)notify; (void)refCon; /* notifications not yet implemented */
    if (!outClient) return paramErr;
    *outClient = 0;
    pthread_mutex_lock(&objectsMutex);
    object = allocate(OBJ_CLIENT, 0);
    if (object) *outClient = object->id;
    pthread_mutex_unlock(&objectsMutex);
    return object ? noErr : kMIDIMessageSendErr;
}

OSStatus MIDIClientDispose(MIDIClientRef client)
{
    size_t i, sourceCount = 0;
    MIDIEndpointRef discardedSources[VIRTUAL_OBJECT_LIMIT];
    callbackLifetimeEnter();
    pthread_mutex_lock(&objectsMutex);
    if (!lookup(client, OBJ_CLIENT)) {
        pthread_mutex_unlock(&objectsMutex);
        callbackLifetimeLeave();
        return kMIDIInvalidClient;
    }
    for (i = 0; i < VIRTUAL_OBJECT_LIMIT; ++i) {
        if (objects[i].id == client || objects[i].owner == client) {
            if (objects[i].kind == OBJ_SOURCE)
                discardedSources[sourceCount++] = objects[i].id;
            memset(&objects[i], 0, sizeof(objects[i]));
        }
    }
    pruneConnections();
    pthread_mutex_unlock(&objectsMutex);
    /* The ALSA binding mutex is never acquired while objectsMutex is held.
     * The callback lifetime gate remains held across the whole disposal.
     */
    for (i = 0; i < sourceCount; ++i)
        D4MIDIAlsaForgetVirtualSource(discardedSources[i]);
    callbackLifetimeLeave();
    return noErr;
}
static OSStatus createOwned(MIDIClientRef client, enum ObjectKind kind,
                            MIDIReadProc proc, void *refCon, MIDIObjectRef *out)
{
    VirtualObject *object;
    if (!out) return paramErr;
    *out = 0;
    pthread_mutex_lock(&objectsMutex);
    if (!lookup(client, OBJ_CLIENT)) {
        pthread_mutex_unlock(&objectsMutex);
        return kMIDIInvalidClient;
    }
    object = allocate(kind, client);
    if (object) {
        object->readProc = proc;
        object->refCon = refCon;
        *out = object->id;
    }
    pthread_mutex_unlock(&objectsMutex);
    return object ? noErr : kMIDIMessageSendErr;
}

OSStatus MIDIInputPortCreate(MIDIClientRef client, CFStringRef name, MIDIReadProc proc,
                             void *refCon, MIDIPortRef *outPort)
{
    (void)name;
    if (!proc) return paramErr;
    return createOwned(client, OBJ_INPUT, proc, refCon, outPort);
}

OSStatus MIDIOutputPortCreate(MIDIClientRef client, CFStringRef name, MIDIPortRef *outPort)
{
    (void)name;
    return createOwned(client, OBJ_OUTPUT, NULL, NULL, outPort);
}

OSStatus MIDISourceCreate(MIDIClientRef client, CFStringRef name, MIDIEndpointRef *outSource)
{
    (void)name;
    return createOwned(client, OBJ_SOURCE, NULL, NULL, outSource);
}

OSStatus MIDIDestinationCreate(MIDIClientRef client, CFStringRef name,
                                MIDIReadProc proc, void *refCon, MIDIEndpointRef *outDest)
{
    (void)name;
    if (!proc) return paramErr;
    return createOwned(client, OBJ_DEST, proc, refCon, outDest);
}

OSStatus MIDIPortDispose(MIDIPortRef port)
{
    VirtualObject *object;
    int existed;
    callbackLifetimeEnter();
    pthread_mutex_lock(&objectsMutex);
    object = lookup(port, OBJ_INPUT);
    if (!object) object = lookup(port, OBJ_OUTPUT);
    existed = object != NULL;
    if (object) memset(object, 0, sizeof(*object));
    pruneConnections();
    pthread_mutex_unlock(&objectsMutex);
    callbackLifetimeLeave();
    return existed ? noErr : kMIDIInvalidPort;
}
OSStatus MIDIEndpointDispose(MIDIEndpointRef endpoint)
{
    VirtualObject *object;
    int existed, wasSource = 0;
    callbackLifetimeEnter();
    pthread_mutex_lock(&objectsMutex);
    object = lookup(endpoint, OBJ_SOURCE);
    if (object) wasSource = 1;
    if (!object) object = lookup(endpoint, OBJ_DEST);
    existed = object != NULL;
    if (object) memset(object, 0, sizeof(*object));
    pruneConnections();
    pthread_mutex_unlock(&objectsMutex);
    if (wasSource)
        D4MIDIAlsaForgetVirtualSource(endpoint);
    callbackLifetimeLeave();
    return existed ? noErr : kMIDIUnknownEndpoint;
}
static ItemCount countEndpoints(enum ObjectKind kind)
{
    ItemCount n = 0;
    size_t i;
    pthread_mutex_lock(&objectsMutex);
    for (i = 0; i < VIRTUAL_OBJECT_LIMIT; ++i)
        if (objects[i].kind == kind) ++n;
    pthread_mutex_unlock(&objectsMutex);
    return n;
}

ItemCount MIDIGetNumberOfSources(void) { return countEndpoints(OBJ_SOURCE); }
ItemCount MIDIGetNumberOfDestinations(void)
{
    return countEndpoints(OBJ_DEST) + D4MIDIAlsaDestinationCount();
}

static MIDIEndpointRef getEndpoint(enum ObjectKind kind, ItemCount index)
{
    MIDIEndpointRef found = 0;
    size_t i;
    pthread_mutex_lock(&objectsMutex);
    for (i = 0; i < VIRTUAL_OBJECT_LIMIT; ++i) {
        if (objects[i].kind == kind) {
            if (!index--) { found = objects[i].id; break; }
        }
    }
    pthread_mutex_unlock(&objectsMutex);
    return found;
}

MIDIEndpointRef MIDIGetSource(ItemCount index) { return getEndpoint(OBJ_SOURCE, index); }
MIDIEndpointRef MIDIGetDestination(ItemCount index)
{
    ItemCount virtualCount = countEndpoints(OBJ_DEST);
    if (index < virtualCount)
        return getEndpoint(OBJ_DEST, index);
    return D4MIDIAlsaDestinationAt(index - virtualCount);
}

OSStatus MIDIPortConnectSource(MIDIPortRef port, MIDIEndpointRef source, void *refCon)
{
    size_t i;
    VirtualConnection *freeSlot = NULL;
    pthread_mutex_lock(&objectsMutex);
    if (!lookup(port, OBJ_INPUT)) {
        pthread_mutex_unlock(&objectsMutex);
        return kMIDIInvalidPort;
    }
    if (!lookup(source, OBJ_SOURCE)) {
        pthread_mutex_unlock(&objectsMutex);
        return kMIDIUnknownEndpoint;
    }
    for (i = 0; i < VIRTUAL_CONNECTION_LIMIT; ++i) {
        if (connections[i].input == port && connections[i].source == source) {
            pthread_mutex_unlock(&objectsMutex);
            return noErr;
        }
        if (!connections[i].input && !freeSlot) freeSlot = &connections[i];
    }
    if (freeSlot && nextConnectionGeneration) {
        freeSlot->input = port;
        freeSlot->source = source;
        freeSlot->refCon = refCon;
        freeSlot->generation = nextConnectionGeneration++;
    } else {
        freeSlot = NULL;
    }
    pthread_mutex_unlock(&objectsMutex);
    return freeSlot ? noErr : kMIDIMessageSendErr;
}

OSStatus MIDIPortDisconnectSource(MIDIPortRef port, MIDIEndpointRef source)
{
    size_t i;
    callbackLifetimeEnter();
    pthread_mutex_lock(&objectsMutex);
    if (!lookup(port, OBJ_INPUT)) {
        pthread_mutex_unlock(&objectsMutex);
        callbackLifetimeLeave();
        return kMIDIInvalidPort;
    }
    for (i = 0; i < VIRTUAL_CONNECTION_LIMIT; ++i) {
        if (connections[i].input == port && connections[i].source == source) {
            memset(&connections[i], 0, sizeof(connections[i]));
            pthread_mutex_unlock(&objectsMutex);
            callbackLifetimeLeave();
            return noErr;
        }
    }
    pthread_mutex_unlock(&objectsMutex);
    callbackLifetimeLeave();
    return kMIDINoConnection;
}
OSStatus MIDISend(MIDIPortRef port, MIDIEndpointRef dest, const MIDIPacketList *packets)
{
    MIDIReadProc callback;
    void *refCon;
    VirtualObject *object;
    if (!packets || !packets->numPackets) return paramErr;
    callbackLifetimeEnter();
    pthread_mutex_lock(&objectsMutex);
    if (!lookup(port, OBJ_OUTPUT)) {
        pthread_mutex_unlock(&objectsMutex);
        callbackLifetimeLeave();
        return kMIDIInvalidPort;
    }
    object = lookup(dest, OBJ_DEST);
    if (!object) {
        pthread_mutex_unlock(&objectsMutex);
        callbackLifetimeLeave();
        return D4MIDIAlsaSend(dest, packets);
    }
    callback = object->readProc;
    refCon = object->refCon;
    pthread_mutex_unlock(&objectsMutex);
    callback(packets, refCon, NULL); /* serialized synchronous virtual delivery */
    callbackLifetimeLeave();
    return noErr;
}
OSStatus MIDIReceived(MIDIEndpointRef source, const MIDIPacketList *packets)
{
    /*
     * Snapshot connection identities, not callback pointers. Callbacks may
     * synchronously disconnect or dispose other connections and their refCons.
     * Revalidate each slot just before invoking it, outside objectsMutex.
     *
     * This prevents stale callbacks on the SAME delivery thread. Inter-thread
     * disposal between unlock and invocation still needs a callback lifetime
     * protocol; this change must not be treated as full concurrency safety.
     */
    struct Receiver { size_t slot; uint64_t generation; } receivers[VIRTUAL_CONNECTION_LIMIT];
    size_t count = 0, i;
    if (!packets || !packets->numPackets) return paramErr;
    callbackLifetimeEnter();
    pthread_mutex_lock(&objectsMutex);
    if (!lookup(source, OBJ_SOURCE)) {
        pthread_mutex_unlock(&objectsMutex);
        callbackLifetimeLeave();
        return kMIDIUnknownEndpoint;
    }
    for (i = 0; i < VIRTUAL_CONNECTION_LIMIT; ++i) {
        if (connections[i].source == source &&
            lookup(connections[i].input, OBJ_INPUT)) {
            receivers[count].slot = i;
            receivers[count].generation = connections[i].generation;
            ++count;
        }
    }
    pthread_mutex_unlock(&objectsMutex);
    for (i = 0; i < count; ++i) {
        MIDIReadProc proc = NULL;
        void *portRefCon = NULL, *connRefCon = NULL;
        size_t slot = receivers[i].slot;
        pthread_mutex_lock(&objectsMutex);
        if (lookup(source, OBJ_SOURCE) &&
            connections[slot].source == source &&
            connections[slot].generation == receivers[i].generation) {
            VirtualObject *port = lookup(connections[slot].input, OBJ_INPUT);
            if (port) {
                proc = port->readProc;
                portRefCon = port->refCon;
                connRefCon = connections[slot].refCon;
            }
        }
        pthread_mutex_unlock(&objectsMutex);
        if (proc)
            proc(packets, portRefCon, connRefCon);
    }
    callbackLifetimeLeave();
    return noErr;
}

MIDIPacket *MIDIPacketListInit(MIDIPacketList *list)
{
    if (!list) return NULL;
    list->numPackets = 0;
    return &list->packet[0];
}

MIDIPacket *MIDIPacketListAdd(MIDIPacketList *list, ByteCount size, MIDIPacket *current,
                              MIDITimeStamp time, ByteCount nData, const Byte *data)
{
    uintptr_t base, first, end, target;
    MIDIPacket *packet;
    size_t needed, i;
    if (!list || !current || !data || !nData || nData > UINT16_MAX ||
        size < offsetof(MIDIPacketList, packet) + offsetof(MIDIPacket, data) + nData)
        return NULL;
    base = (uintptr_t)list;
    if (size > UINTPTR_MAX - base) return NULL;
    first = (uintptr_t)&list->packet[0];
    end = base + size;
    target = first;
    if (list->numPackets) {
        uintptr_t p = first;
        if (list->numPackets > 4096) return NULL;
        for (i = 0; i < list->numPackets; ++i) {
            MIDIPacket *candidate;
            size_t bytes;
            if (p > end || end - p < offsetof(MIDIPacket, data)) return NULL;
            candidate = (MIDIPacket *)p;
            bytes = offsetof(MIDIPacket, data) + candidate->length;
            if (bytes > end - p) return NULL;
            if (i == list->numPackets - 1) {
                if (candidate != current) return NULL;
                target = (uintptr_t)MIDIPacketNext(candidate);
                break;
            }
            p = (uintptr_t)MIDIPacketNext(candidate);
        }
    } else if ((uintptr_t)current != first) {
        return NULL;
    }
    needed = offsetof(MIDIPacket, data) + nData;
    if (target > end || needed > end - target) return NULL;
    packet = (MIDIPacket *)target;
    packet->timeStamp = time;
    packet->length = (UInt16)nData;
    memcpy(packet->data, data, nData);
    ++list->numPackets;
    return packet;
}
