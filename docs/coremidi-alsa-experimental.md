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
Those were preliminary results. On 2026-10-16, the separate **Ryzen 7
5700X / Debian 13 WSL2** qualification used ALSA **1.2.14** and GCC with
real libasound headers. After the `<alloca.h>` fix in `8cb4953`, the
virtual suite reported **PASS**, and the actual enabled bridge plus
`host_loopback.c` compiled and linked: **ALSA_COMPILE_PASS**. The runner
then emitted **ALSA_RUNTIME_SKIP (77)** because `/dev/snd/seq` was absent.
The checkout was clean at that commit. None of this qualifies real ALSA
sequencer traffic, Darling Mach-O/ELF wrapping or Logic Studio.

## Debian 13 strict C11 header qualification

A native build on the 5700X with ALSA 1.2.14 exposed an implicit
`alloca` declaration in the ALSA sequencer allocation macros. The bridge
now explicitly includes `<alloca.h>` before `<alsa/asoundlib.h>` to support
`-std=c11 -Wall -Wextra -Werror`. An isolated strict-C11 include/use check
passed with GCC and Clang; the 5700X rerun on commit `8cb4953` subsequently produced
`ALSA_COMPILE_PASS`. A real sequencer transport test is still pending.

## Sequencer-independent ALSA preflight

The native test runner now additionally builds `host_preflight.c` using
real libasound headers and linkage, with only `snd_seq_open` intercepted
at link time. Invalid packet values and a valid-then-invalid packet list
must be rejected without trying to open the ALSA sequencer, and a valid
Note On must reach the intercepted open. Marker: `ALSA_PREFLIGHT_PASS`.

This test can run under WSL2 with no `/dev/snd/seq`; it is **not** a test
of real ALSA event delivery. On the 5700X at commit `7311124`, this gate
returned `ALSA_PREFLIGHT_PASS`.

## 5700X / Debian 13 WSL2 — verified 2026-10-16

User-run qualification in the native Linux checkout
`/home/Deniel/d4rling-midi-qualif` at commit `7311124`:

- `CC=gcc sh tests/regressions/coremidi-virtual/run.sh`:
  **PASS**, exit 0.
- `CC=gcc sh tests/regressions/coremidi-alsa/run.sh`:
  **ALSA_COMPILE_PASS** with system ALSA 1.2.14 and GCC.
- Same runner: **ALSA_PREFLIGHT_PASS**, verifying MIDI packet rejection
  happens before attempted ALSA sequencer access.
- **ALSA_RUNTIME_SKIP**, exit 77, because `/dev/snd/seq` was absent.
- The Git checkout remained clean. No actual MIDI event was delivered,
  and the Darling framework build and Logic were **not tested**.

## Read-only sequencer kernel diagnostic

Run on the target Linux system:

```sh
sh tests/regressions/coremidi-alsa/kernel-diagnostics.sh
```

It checks the sequencer device, kernel release, `CONFIG_SND_SEQUENCER` when
the kernel's configuration is available, and loaded modules. The diagnostic
**never invokes sudo, modprobe, mknod, package installation or kernel changes**.
Missing kernel config or module files must not be interpreted as definitive
proof that the option was disabled. `/dev/snd/seq` requires sequencer
support in the running kernel; libasound development headers alone cannot
provide the device.

## 5700X WSL2 kernel gate — confirmed 2026-10-16

At commit `8d3613`, the read-only kernel diagnostic ran on the 5700X.
It identified:

```text
ALSA_KERNEL_RELEASE: 6.18.33.2-microsoft-standard-WSL2
ALSA_SEQ_NODE: absent
ALSA_KERNEL_CONFIG_SOURCE: /proc/config.gz
CONFIG_SOUND=m
CONFIG_SND=m
# CONFIG_SND_SEQUENCER is not set
ALSA_PROC_SEQUENCER: unavailable
ALSA_LOADED_SEQ_MODULES: (none listed)
ALSA_MODULE_TREE: present
```

The checkout was clean at `8d3613`. The **running WSL2 kernel has
ALSA Sequencer support disabled at build time**, unlike merely having an
unloaded `snd_seq` module. Installing user-space ALSA packages, creating
the missing device node or using `modprobe` alone cannot enable that
functionality. Do not treat `ALSA_RUNTIME_SKIP (77)` as a product failure.

Keep the tested native compilation and preflight gates in Debian WSL2.
For future real sequencer loopback tests, use a Linux kernel built with
`CONFIG_SND_SEQUENCER=y` or `=m` (with matching modules installed).
One option is a Linux live system or suitable VM; alternatively, WSL2
supports a custom kernel via the global `%UserProfile%/.wslconfig`, but
that changes the kernel environment for **all WSL2 distributions** and
must be evaluated separately. Do not change kernels as part of an
ordinary CoreMIDI source qualification.
