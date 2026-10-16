# CoreMIDI -> ALSA native sequencer loopback (experimental)

Run from the repository checkout on Linux:

```sh
sh tests/regressions/coremidi-alsa/run.sh
CC=gcc sh tests/regressions/coremidi-alsa/run.sh
```

Prerequisites: a C compiler, pkg-config, genuine ALSA development headers and
libasound. The runner uses the actual `MIDIVirtual.c` and `MIDIAlsaBridge.c`
sources, compiled **natively** outside the Darling framework. It creates an
ALSA input client, locates its endpoint via public CoreMIDI enumeration, sends
Note On/Off (channel 1, note 60), and checks their delivery and byte values.

Before checking for a sequencer, the runner also builds
`host_reverse.c` using the genuine ALSA event representation. It checks
the **internal, sequencer-independent** ALSA-to-MIDI 1.0 codec with 16-channel
round trips, correct 2-byte messages, Note On velocity-zero normalization,
rejection of out-of-range/unsupported events, and bounded output buffers.
The test prints `ALSA_REVERSE_PASS` when successful.

Before checking for a sequencer, the runner compiles and executes
`host_translation.c` against the actual bridge and ALSA headers. It verifies
Note On/Off, polyphonic aftertouch, Control Change, Program Change, Channel
Pressure and Pitch Bend on all 16 channels. Two-byte message lengths,
zero-velocity Note On, boundary values and unsupported/malformed messages
are checked. Success emits `ALSA_TRANSLATION_PASS`.

The runner also compiles and executes
`host_preflight.c`. It links to genuine libasound but uses GNU ld's
`--wrap=snd_seq_open` to count attempted sequencer opens without opening a
device. Invalid note/velocity values, unsupported opcodes and an invalid
second packet must all fail **before** `snd_seq_open`; a valid packet must
reach the wrapped call. This is a native packet-validation test, **not**
proof of real ALSA sequencer I/O.

Before attempting ALSA sequencer I/O, `host_delivery.c` creates a virtual
CoreMIDI source and two connected input ports, then delivers synthetic ALSA
events through the production reverse codec and `MIDIReceived`. It verifies
all seven channel-event classes across 16 channels, connection-specific
callback context, rejection of unsupported events, disconnect, and disposal.
It prints `ALSA_DELIVERY_PASS` on success. **This does not establish an ALSA
input port, poll a physical device, or qualify callback concurrency.**

The no-sequencer `host_source_route.c` gate checks explicit
`client:port` ALSA sender-address bindings to distinct virtual CoreMIDI
sources, across 16 channels. It verifies unmatched and invalid sender
addresses, no unintended cross-delivery, reentrant unbinding from a
callback, short Program Change events and disposed virtual sources.
It does not discover or subscribe to hardware ALSA sources.

The `host_source_lifetime.c` regression fills all 128 binding slots,
verifies source-endpoint disposal removes *every* old ALSA address,
refills them across two sources belonging to one CoreMIDI client,
and verifies client disposal releases both sets. It then reuses all
128 slots on a newly created source. `host_source_route.c` also
checks immediate address reuse following endpoint disposal.
Both tests run with genuine libasound but without `/dev/snd/seq`.

Output markers:
- `ALSA_SOURCE_LIFETIME_PASS`: disposed sources/clients automatically release source-address bindings.
- `ALSA_SOURCE_ROUTE_PASS`: synthetic ALSA source-address binding and delivery passed.
- `ALSA_DELIVERY_PASS`: synthetic ALSA events reached virtual CoreMIDI input callbacks.
- `ALSA_TRANSLATION_PASS`: channel-message translation tests passed.
- `ALSA_REVERSE_PASS`: ALSA event to MIDI 1.0 codec checks passed.
- `ALSA_PREFLIGHT_PASS`: native bridge validation works without a sequencer.
- `ALSA_COMPILE_PASS`: the native build and link completed.
- `ALSA_RUNTIME_PASS`: ALSA delivered Note On and Note Off.
- `ALSA_COMPILE_SKIP`: libasound development files or pkg-config missing.
- `ALSA_RUNTIME_SKIP`: /dev/snd/seq missing (exit 77).
- `ALSA_RUNTIME_FAIL`: receiver creation, discovery, delivery or validation failure.

An exit status of 77 means **not qualified**, not a passing ALSA runtime test.
This test does not prove ELF/Mach-O wrapping, physical USB MIDI, MIDI input
support, timing accuracy, concurrency safety, or Logic Studio compatibility.
