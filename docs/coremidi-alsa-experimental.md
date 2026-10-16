# Experimental CoreMIDI -> ALSA sequencer output (lot B, incomplete)

This is an incremental, opt-in bridge on `work/core-audio`, **not** proof of
Darling MIDI interoperability or a real MIDI device test.

## Scope

- Virtual endpoints continue working when ALSA support is disabled (default).
- When built with `-DDARLING_COREMIDI_ENABLE_ALSA=ON`, native sequencer
  destinations are enumerated and exposed through `MIDIGetDestination`.
- `MIDISend` can send immediate Note On and Note Off events to ALSA
  destinations. It returns an error for other MIDI event types. No input support.
- ALSA client/port identification is provisional and must be qualified against
  target CoreMIDI object semantics and restart scenarios.
- The Linux ALSA libraries and headers are needed for the opt-in build.
  A Darling runtime build and the Mach-O/ELF linkage have **not been qualified**.

## Limitations

- No ALSA input, subscriptions, hotplug events, property names or UID mapping.
- No timestamp scheduling or audio/MIDI synchronization.
- A native ALSA client is opened lazily and currently held for process lifetime.
- MIDI messages are limited to single 3-byte Note On/Off packets.
- Destination handles can become invalid after ALSA server/device restart.
- No device or cross-process traffic has been verified.
- Virtual callbacks can race with disposal; fix before realtime use.

## Tests / reproduction

The portable virtual test remains:
```sh
sh tests/regressions/coremidi-virtual/run.sh
CC=gcc sh tests/regressions/coremidi-virtual/run.sh
```

In the available Debian 13 runner, the disabled bridge compiled with Clang
and GCC, and its fallback assertions passed. The ALSA-enabled C translation
unit passed syntax checks against a lightweight *test double* of ALSA headers.
These are **not** substitutes for a build with genuine libasound development
headers, Darling linkage or Linux sequencer I/O.

Next: run the isolated regression from the checked-out GitHub tree; build with
actual ALSA headers; inspect link symbols; exercise ALSA loopback destinations
in a Linux environment exposing `/dev/snd/seq`; implement input and callback
lifetime safety. Do not mark the bridge "qualified" before these checks pass.
