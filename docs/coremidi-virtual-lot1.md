# CoreMIDI virtual — lot 1

Branch: work/core-audio. Isolated experiment toward Logic Studio 8, not a claim of application, hardware or audio-engine compatibility.

## Implemented

- Typed declarations for a CoreMIDI 1.0 subset in MIDIServices.h.
- In-process clients, input/output ports, virtual sources and destinations.
- Endpoint enumeration, connect/disconnect, routing and cleanup.
- Synchronous MIDI delivery with MIDISend and MIDIReceived.
- MIDIPacketListInit, MIDIPacketListAdd and MIDIPacketNext, with packet bounds and architecture-dependent alignment.
- Mutex-protected fixed-size registries (128 objects and 128 connections).

## Reproduce the test

Run from the repository root on Linux with Clang or GCC:

    sh tests/regressions/coremidi-virtual/run.sh
    CC=gcc sh tests/regressions/coremidi-virtual/run.sh

The runner builds the same MIDIVirtual.c used by the framework against a minimal test-only CoreFoundation type shim. It tests Note On (0x90, 60, 100) and Note Off (0x80, 60, 0), packet-list bounds, enumeration, disconnect and cleanup.

Local test: Clang and GCC passed. A separate local Clang AddressSanitizer/UndefinedBehaviorSanitizer test with -fno-sanitize-recover=all passed, as did a simulated ARM-alignment configuration. None of these are a Darling framework build. CI status and exported Mach-O symbols remain unverified.

## Explicit limitations

- No ALSA sequencer ports, cross-process discovery, server or physical devices.
- No scheduling or host-clock semantics; callbacks are synchronous on the sending thread. Timestamps are passed through unchanged.
- No client notifications, properties, setup, sysex service or CoreMIDI 2.0.
- Other legacy void* CoreMIDI stubs remain ABI-incomplete and are unchanged.
- The caller must protect callback/refCon lifetimes during concurrent disposal. Callbacks run outside the registry mutex. This is not a realtime-safe implementation.
- No Audio Units, playback or Logic Studio execution has been tested.

## Next

Build CoreMIDI within Darling and inspect exports, add an in-framework smoke test, then bridge virtual endpoints to ALSA sequencer before connecting physical controllers.
