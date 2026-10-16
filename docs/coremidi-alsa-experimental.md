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

## MIDI 1.0 channel message expansion (pending 5700X qualification)

`D4MIDIAlsaTranslate` now centralizes packet validation and translation
into native `snd_seq_event_t` values for Note On/Off, polyphonic aftertouch,
Control Change, Program Change (2 bytes), Channel Pressure (2 bytes) and
Pitch Bend (signed -8192..8191), including all 16 MIDI channels.
Note On with velocity zero is emitted as ALSA Note Off. Both preflight
and send use the same translator, preventing late malformed messages from
causing partial output **before** the first ALSA event.

A channel `MIDIPacket` must contain exactly one whole channel message;
multiple MIDI messages per packet, running status, SysEx, real-time/system
messages, timestamps and scheduler behavior remain unsupported. CoreMIDI
provides no packet-list capacity to `MIDISend`; the sender cannot safely
dereference arbitrary corrupted or truncated caller pointers.

The native no-sequencer gate `host_translation.c` covers all seven
message classes, 16 channels and data/length boundary cases.
`host_preflight.c` also checks that two-byte Program Change passes
validation before attempting ALSA. These tests were **added but still require
running on the 5700X against real ALSA 1.2.14**. An independent translation
logic test, using a synthetic ALSA event representation, passed isolated
GCC and Clang with ASan/UBSan; this does not substitute for real ALSA.

## ALSA event to MIDI 1.0 codec — pending native qualification

An internal sequencer-independent `D4MIDIAlsaEncodeEvent` helper now maps
the same seven ALSA channel-event classes back to complete MIDI 1.0 messages,
including 16 channels, Program Change and Channel Pressure as two-byte
messages, and signed pitch bend represented as the two 7-bit MIDI bytes.
Unsupported types, out-of-range data, invalid channels and short output
buffers are rejected before writing any caller bytes; `*length` is reset
to zero on such rejections when arguments are valid.

`tests/regressions/coremidi-alsa/host_reverse.c` runs forward/reverse
round trips and negative tests with the production codec and genuine
libasound event types. It requires no `/dev/snd/seq`. It is not yet
qualified on the 5700X, and does **not** implement ALSA input polling,
CoreMIDI source enumeration, callback distribution or actual MIDI capture.
The test runner emits `ALSA_REVERSE_PASS` only upon success.

The previously observed 5700X run on commit `26be43b` gave
`ALSA_COMPILE_PASS`, `ALSA_TRANSLATION_PASS`,
`ALSA_PREFLIGHT_PASS` and `ALSA_RUNTIME_SKIP` (exit 77); these are
baseline results predating this new reverse codec.

## Reverse-event delivery to virtual CoreMIDI ports (pending native qualification)

The internal `D4MIDIAlsaDeliverToVirtualSource` accepts a supplied ALSA
channel event and an existing *CoreMIDI virtual source*, encodes MIDI 1.0
bytes via `D4MIDIAlsaEncodeEvent`, and synchronously routes a one-packet
`MIDIPacketList` via `MIDIReceived` to connected input callbacks.
It does not call `snd_seq_open`, create an ALSA input client, discover ALSA
sources, map ALSA client/port IDs, or install a receive thread.
The temporary packet list is valid only during that synchronous dispatch;
there is no timestamp scheduling. All valid events currently use timestamp 0.

`host_delivery.c` is the native no-sequencer regression gate. It exercises
the actual production router with two connections, all seven supported
channel-message classes across 16 channels, per-connection refCons,
unsupported events, disconnect and source disposal. Marker:
`ALSA_DELIVERY_PASS`. Added pending first native GCC + ALSA qualification
on the 5700X. It does not prove realtime safety, callback lifetime under
concurrent disposal, ALSA device input or application-level compatibility.

## ALSA sender address -> virtual CoreMIDI source routing (qualification pending)

An internal bounded, mutex-protected map allows an ALSA sender
`client:port` address (0..255 each) to be bound manually to an existing
virtual CoreMIDI source, unbound, and resolved for a supplied
`snd_seq_event_t` using `event->source.client` and
`event->source.port`. Address collisions are rejected; identical
rebindings are idempotent. The source must appear in current virtual
source enumeration at bind time. An event from an unknown sender returns
`kMIDIUnknownEndpoint`; disposed bound sources are also rejected by
the existing CoreMIDI virtual delivery layer.

The mapping lock is released before invoking any CoreMIDI callback,
so callbacks may unbind their own source address. An already-routed event
may still be delivered while a concurrent unbind is taking place.
Bindings are now explicitly purged when a virtual source is disposed
or an owning client is disposed. Mapping/delivery still does not
perform native ALSA discovery or stable cross-process identity assignment.

The new `host_source_route.c` exercises source isolation across 16
channels, binding validation, reentrant unbind, short Program Change,
invalid messages and source disposal. It needs only libasound headers
and the real bridge source, **not** `/dev/snd/seq`. Marker:
`ALSA_SOURCE_ROUTE_PASS`. The gate is pending native execution on the
5700X.

The previous 5700X run of `978d0ac` passed the CoreMIDI virtual,
reentrant and concurrent callback regression gates, plus
`ALSA_COMPILE_PASS`, `ALSA_TRANSLATION_PASS`,
`ALSA_REVERSE_PASS`, `ALSA_DELIVERY_PASS`, and
`ALSA_PREFLIGHT_PASS`. Actual sequencer traffic was skipped (77),
and this source router had not yet been added.

## Virtual source binding lifetime (new gate; qualification pending)

To avoid exhausting the 128-entry ALSA source-address map with stale
entries, `MIDIEndpointDispose` and `MIDIClientDispose` explicitly
forget all mappings for destroyed virtual sources. The enabled ALSA
bridge implements `D4MIDIAlsaForgetVirtualSource`; a no-op stub preserves
the non-ALSA build. The CoreMIDI object registry is unlocked before
taking the ALSA binding mutex. The binding path now revalidates source
liveness while its mapping mutex is held, using an internal
`D4MIDIVirtualSourceIsLive` query that briefly locks the virtual registry.
This closes the bind-after-dispose race in the source mapping.

`host_source_lifetime.c` checks all 128 table entries can be reclaimed
after source destruction and after client destruction of multiple
sources, then reused without reaching the binding limit. The existing
`host_source_route.c` regression checks immediate address reuse and
automatic unbinding on client disposal. The new marker is
`ALSA_SOURCE_LIFETIME_PASS`, pending native GCC and ALSA validation
on the 5700X. This is an in-process ownership guarantee; it does not
qualify ALSA hotplug, cross-process sequencing or real device input.

## ALSA native sender discovery (new gate; not yet qualified)

The ALSA-enabled bridge adds internal `D4MIDIAlsaSourceAddressCount`
and `D4MIDIAlsaSourceAddressAt` APIs. They enumerate currently
available ALSA sender `client:port` addresses using the existing
native sequencer client, but **do not** expose them automatically as
CoreMIDI endpoints, subscribe to sources or poll for MIDI data.
Enumeration is an instantaneous snapshot; ALSA clients/ports may
disappear and numeric identifiers can be reused.

A sender candidate is readable (`SND_SEQ_PORT_CAP_READ`), allows read
subscriptions (`SND_SEQ_PORT_CAP_SUBS_READ`) and is not
`SND_SEQ_PORT_CAP_NO_EXPORT`. The bridge's own ALSA client is
excluded, as are addresses not representable by the sequencer's
8-bit `client`/`port` fields. The no-sequencer regression
`host_source_filter.c` checks these rules using genuine ALSA
port-info structs and verifies NULL output argument rejection before
any device access. Marker: `ALSA_SOURCE_FILTER_PASS`.

On a Linux kernel with `/dev/snd/seq`, `host_loopback.c` creates a
separate native ALSA source, checks its address appears in the new
enumerator, and checks a destination-only receiver port is not
misidentified as a source. Marker: `ALSA_SOURCE_RUNTIME_PASS`.
This runtime test is **not** executable on the current 5700X WSL2
kernel and has not passed yet. The new discovery methods cannot
be used as evidence of MIDI input reception, hotplug handling,
Mach-O/ELF linking or Logic Studio 8 operation.

The 5700X GCC/ALSA run at commit `5986708` passed CoreMIDI virtual,
reentrant, concurrent, and `ALSA_COMPILE_PASS`,
`ALSA_TRANSLATION_PASS`, `ALSA_REVERSE_PASS`,
`ALSA_DELIVERY_PASS`, `ALSA_SOURCE_ROUTE_PASS`,
`ALSA_SOURCE_LIFETIME_PASS`, and `ALSA_PREFLIGHT_PASS`.
The runtime test was skipped (77), as expected. The new source
discovery changes require another native requalification.

## Bounded nonblocking ALSA input-event pump (new gate; pending 5700X)

`D4MIDIAlsaPumpNonblocking` consumes at most 4096 events per call
from a **caller-owned, already-open, nonblocking ALSA sequencer
input handle**. It invokes the existing address-to-virtual-source
router synchronously, returning the count of *delivered* channel
messages. Unmapped senders and unsupported messages are consumed
without callbacks. `-EAGAIN` is a normal empty queue; other ALSA
errors such as FIFO overflow (`-ENOSPC`) fail the call.
This method does **not** create, own, configure or close a sequencer
handle; it also does not subscribe to any ALSA source, start a thread,
provide scheduling or map MIDI timestamps.

The buffer returned by `snd_seq_event_input` belongs to ALSA in
current libasound and is consumed before the next read. The deprecated
`snd_seq_free_event` is not necessary. This avoids accidentally
freeing ALSA-managed storage.

`host_input_pump.c` uses genuine ALSA types and production source
code, but intercepts only `snd_seq_event_input` via the linker.
It checks two correctly routed callback destinations, filtering,
budget exhaustion, `-EAGAIN`, `-EIO`, `-ENOSPC`, NULL returned
events and invalid arguments. Marker: `ALSA_INPUT_PUMP_PASS`.
This tests *injected input*, not actual kernel event reception,
real subscriptions, hotplug, runtime Darling or Logic Studio 8.
The new test has **not** been qualified on the 5700X yet.

The latest prior 5700X run at `8bf455f` passed the three virtual
regressions and eight ALSA compile/codec/routing/source/filter
checks, with `ALSA_RUNTIME_SKIP` (exit 77). The new input adapter
requires another native requalification.

## Explicit native ALSA input session (new gate; pending 5700X)

The internal single-source `D4MIDIAlsaInputSession` brings the
previously independent components together without starting any
worker thread:

1. Open an ALSA `SND_SEQ_OPEN_INPUT` handle with
   `SND_SEQ_NONBLOCK` and create a receiving
   `WRITE|SUBS_WRITE` sequencer port.
2. Validate the chosen sender through `snd_seq_get_any_port_info`,
   claim its `client:port` mapping **exclusively** to an existing
   virtual CoreMIDI source, and call `snd_seq_connect_from`.
3. Pump at most a caller-provided number of messages using
   `D4MIDIAlsaPumpNonblocking`, then disconnect, remove the mapping
   and close the owned ALSA handle.

The caller must zero-initialize the session, serialize all operations
(including callback-triggered teardown), and arrange a polling/event
loop if continuous reception is needed. Session operations are not
thread-safe or realtime-safe. Each session accepts only one sender;
native hotplug, reconnection after ALSA client-number changes,
timestamp scheduling, and automatic CoreMIDI source creation are
outside this lot. If subscription fails, the owned address binding
is rolled back. On native disconnection failure the subscription
remains marked active so unsubscription can be retried; definitive
close still removes the binding and closes the ALSA handle.

`host_input_session.c` links the real bridge and libasound but
intercepts the sequencer-facing ALSA operations with `--wrap`.
It exercises open/create/connect/pump/disconnect/close, source
isolation, failure rollback, exclusive map ownership and cleanup.
Marker: `ALSA_INPUT_SESSION_PASS`, **not yet qualified on 5700X**.
No actual `/dev/snd/seq` transport, real device, or Logic Studio 8
execution is claimed.

The native `host_loopback.c` test also now exercises the complete
experimental input session: a real ALSA sender port is subscribed to
the new session receiver, a Note On is delivered via ALSA sequencer
subscriptions and the resulting CoreMIDI callback is checked.
Marker: `ALSA_INPUT_RUNTIME_PASS` **only** on a kernel with active
ALSA Sequencer. There is no native PASS for this path yet.

While a session pump is active, callback-initiated
`Unsubscribe` and `Close` return `paramErr` instead of invalidating
the sequencer handle before the pump finishes. This is an in-thread
reentrancy guard, not cross-thread synchronization. The caller must
still serialize use of a session across multiple threads.


## Event loop descriptor handoff (new gate; native check pending)

`D4MIDIAlsaInputSessionPollDescriptors` exports the input session's
`POLLIN` file descriptors into a caller-owned `struct pollfd`
array, without calling `poll()`, reading events, or starting
threads. The caller keeps control over blocking timeouts and invokes
`D4MIDIAlsaInputSessionPump` only when input is ready. The helper
requires an opened, subscribed session, rejects reentrant access
during pumping, caps the reported descriptor requirement at 64,
and on inadequate buffer capacity returns `paramErr` with the
required count while leaving the buffer unchanged.

`host_input_session.c` intercepts only the two ALSA descriptor
query functions in addition to its existing device-facing mocks,
verifying successful output, invalid arguments, short capacity,
ALSA failures, and callback-time rejection. The native
`host_loopback.c` integration test now obtains poll descriptors
through this interface. These changes do not qualify realtime
dispatch, cross-thread session access, kernel ALSA reception or
Darling runtime integration. The new tests are awaiting a 5700X
native GCC run.

The host regression emits a separate `ALSA_INPUT_POLL_PASS` marker
after the session descriptor handoff and bounds checks succeed;
`ALSA_INPUT_SESSION_PASS` remains as the existing lifecycle gate.

## Host shared-library build and dynamic CoreMIDI symbol regression

The CoreMIDI CMake target already includes `MIDIVirtual.c` and
`MIDIAlsaBridge.c` in its source list. It exposes the experimental
`DARLING_COREMIDI_ENABLE_ALSA` option (OFF by default), which finds
ALSA, uses Darling's `wrap_elf` machinery and enables
`DARLING_COREMIDI_WITH_ALSA=1`. Source inspection found no overlap
between the named CoreMIDI.m stub functions and virtual entry points.

`tests/regressions/coremidi-shared/run.sh` now builds the two C
sources as host ELF shared libraries with `-fPIC -shared -Wl,-z,defs`
in ALSA-off and ALSA-on configurations, then loads both using
`dlopen(RTLD_NOW)` and invokes representative exported CoreMIDI
functions using `dlsym`. It verifies a callback receives a packet
across the host shared-library boundary. Marker:
`COREMIDI_SHARED_PASS`. The ALSA regression runner invokes this
check before its kernel-dependent runtime gate.

**Scope:** this checks native host ELF linking, symbol visibility and
callback ABI with the isolated header set. It does not build the
actual Darling framework, load Mach-O binaries, validate Darling's
`wrap_elf` output, or prove compatibility with Logic Studio 8.
It requires native qualification on the 5700X. No kernel sequencer
is required for the test.
