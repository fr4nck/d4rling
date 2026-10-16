/*
 * Dynamic-link smoke regression for the CoreMIDI virtual + ALSA bridge.
 * Verifies public CoreMIDI symbols can be resolved and invoked through
 * a position-independent host shared object, without launching Darling.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <CoreMIDI/MIDIServices.h>
#include <assert.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static unsigned callbackCount;
static void onRead(const MIDIPacketList *packets, void *portCtx, void *connCtx)
{
    assert(portCtx == (void *)(uintptr_t)0x1234);
    assert(connCtx == (void *)(uintptr_t)0x5678);
    assert(packets && packets->numPackets == 1);
    assert(packets->packet[0].length == 3);
    assert(packets->packet[0].data[0] == 0x90);
    assert(packets->packet[0].data[1] == 60);
    assert(packets->packet[0].data[2] == 100);
    ++callbackCount;
}

#define RESOLVE(symbol) \
    __typeof__(&symbol) fp_##symbol = (__typeof__(&symbol))dlsym(lib, #symbol); \
    assert(fp_##symbol != NULL)

int main(int argc, char **argv)
{
    void *lib;
    MIDIClientRef client = 0;
    MIDIPortRef input = 0;
    MIDIEndpointRef source = 0;
    union { long double align; Byte bytes[128]; } buffer;
    MIDIPacketList *list = (MIDIPacketList *)buffer.bytes;
    MIDIPacket *packet;
    const Byte note[] = {0x90, 60, 100};

    assert(argc == 2);
    lib = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!lib) {
        fprintf(stderr, "CoreMIDI dlopen failed: %s\n", dlerror());
        return 1;
    }
    RESOLVE(MIDIClientCreate);
    RESOLVE(MIDIClientDispose);
    RESOLVE(MIDIInputPortCreate);
    RESOLVE(MIDIPortConnectSource);
    RESOLVE(MIDISourceCreate);
    RESOLVE(MIDIReceived);
    RESOLVE(MIDIPacketListInit);
    RESOLVE(MIDIPacketListAdd);
    RESOLVE(MIDIGetNumberOfSources);
    RESOLVE(MIDIGetSource);
    RESOLVE(MIDIPortDispose);

    assert(fp_MIDIClientCreate(NULL, NULL, NULL, &client) == noErr);
    assert(client);
    assert(fp_MIDISourceCreate(client, NULL, &source) == noErr);
    assert(source);
    assert(fp_MIDIInputPortCreate(client, NULL, onRead,
           (void *)(uintptr_t)0x1234, &input) == noErr);
    assert(input);
    assert(fp_MIDIPortConnectSource(input, source,
           (void *)(uintptr_t)0x5678) == noErr);
    assert(fp_MIDIGetNumberOfSources() == 1);
    assert(fp_MIDIGetSource(0) == source);

    packet = fp_MIDIPacketListInit(list);
    assert(packet);
    assert(fp_MIDIPacketListAdd(list, sizeof(buffer.bytes), packet,
             0, (UInt16)sizeof(note), note) != NULL);
    assert(fp_MIDIReceived(source, list) == noErr);
    assert(callbackCount == 1);
    assert(fp_MIDIPortDispose(input) == noErr);
    assert(fp_MIDIClientDispose(client) == noErr);
    assert(dlclose(lib) == 0);
    puts("CoreMIDI shared: ELF PIC/link/load/symbols/callback PASS");
    return 0;
}
