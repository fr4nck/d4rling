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
- Each supported packet must be a 3-byte Note On/Off event; multiple packets may be sent in a list.
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

## Native ALSA loopback gate (qualification pending)

`tests/regressions/coremidi-alsa/run.sh` builds against the host libasound
development files and links the real native bridge. It creates a receiver
through the ALSA sequencer and sends Note On/Off through public CoreMIDI
enumeration. It also checks that velocity 128 is rejected. The bridge now
validates an entire packet list before sending any ALSA events.

This gate is independent of Darling's Mach-O/ELF library wrapping. It cannot
qualify the framework's final build or Logic Studio.

On 2026-10-16, the test source passed Clang and GCC syntax checks with a
*synthetic ALSA header* on Debian 13, and `sh -n` passed for its runner.
Actual host libasound headers were unavailable in the isolated runner, and
`/dev/snd/seq` was absent. Therefore no genuine ALSA compile/link and no
sequencer events were verified. These results must be obtained on a Linux
environment with ALSA development files and an accessible sequencer.

## Debian 13 strict C11 header qualification

A native build on the 5700X with ALSA 1.2.14 exposed an implicit
`alloca` declaration in the ALSA sequencer allocation macros. The bridge
now explicitly includes `<alloca.h>` before `<alsa/asoundlib.h>` to support
`-std=c11 -Wall -Wextra -Werror`. An isolated strict-C11 include/use check
passed with GCC and Clang; the genuine ALSA bridge still requires a rerun
on the 5700X. `ALSA_COMPILE_PASS` and runtime transport must not be claimed
until the corresponding tests have actually completed.
