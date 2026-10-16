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

## Packet-list buffer sizing

The earlier prototype rejected any `MIDIPacketListAdd` buffer exceeding
65,536 bytes, regardless of whether the packet fit. This arbitrary limit is
removed: each packet retains its UInt16 payload bound and every write remains
checked against the caller-provided buffer size. A large-buffer regression
was added. The isolated packet-builder implementation passed GCC and Clang
with AddressSanitizer and UndefinedBehaviorSanitizer on an independent
Debian 13 environment. The full repository regression must still be rerun.

## Reentrant callback invalidation (new test, qualification pending)

The virtual source dispatcher now snapshots **connection identities**
rather than callback function pointers/refCons, and revalidates each
identity immediately before invoking its callback without holding the
registry mutex during user code. A fresh monotonically increasing
connection generation distinguishes disconnect/reconnect in a reused slot.

`tests/regressions/coremidi-virtual/reentrant.c` checks synchronous
callback-triggered disconnect, same-slot reconnect, input-port disposal
and source disposal. It requires no ALSA kernel device.

**Scope of the reentrant fix:** this prevents stale callback snapshots
after mutations made *by a previously invoked callback on the same thread*.
The test passed on the 5700X with GCC at commit `65b6751`, together with
the virtual and native ALSA compile/translation gates. Full Darling
framework/real-device qualification is still pending.

## Callback teardown serialization (new test, qualification pending)

A dedicated `callbackLifetimeMutex` now serializes **virtual callback
invocation** against client disposal, port disposal, endpoint disposal
and source disconnection from other threads. The lock is acquired before
`objectsMutex` and held through the callback to protect its `refCon` until
it returns. A C11 thread-local recursion depth lets the current callback
thread call the same APIs reentrantly without deadlocking the nonrecursive
mutex. Cross-thread teardown blocks until the active callback returns.
The gate also serializes concurrent virtual deliveries.

`tests/regressions/coremidi-virtual/concurrent.c` uses pthread conditions
and two worker threads to test concurrent teardown of a virtual input
connection, port, source, client, and a virtual destination callback.
It checks that teardown does not complete during the callback, and that
all cleanup calls eventually return. Each case includes a short
scheduler window and a 5-second handshake timeout; this is a regression
gate, **not a formal proof** of all possible scheduling interleavings.

**Important limitations:** holding one global gate across user callbacks
can introduce priority inversion and deadlock if a callback waits for an
external thread currently attempting CoreMIDI teardown. It is not
realtime-safe and not a final per-object lifetime protocol. Callback-
initiated destruction can still invalidate pointers held by the
callback itself; callers must honor their own refCon lifetimes.
This test does not qualify Mach-O TLS support or Darling runtime behavior.

The new test still requires actual execution on the 5700X.
