# CoreAudio CA-01 — source audit and qualification plan

Status: **source review completed, runtime qualification pending**.
Branch: `work/core-audio`. Reviewed baseline: `76b74ce0c8502daf7a7809cd194e7e5e3423f8df` (2026-10-26).
This document is an audit of repository source and CMake wiring. It does **not**
claim a successful build, Mach-O export check, sound playback, Logic 8 startup,
or tests on the 5700X. No host downloads, installs, or CI runs were performed.

## Goal and scope

Reuse Darling's existing CoreAudio/PulseAudio implementation. Establish the
shortest **verified** path to (1) a Mach-O CoreAudio framework loaded by Darling
and (2) a simple PCM output tone, before extending AudioToolbox/AudioUnit or
attempting Logic Studio 8. Keep the separate CoreMIDI/ALSA work intact.

### Existing components (source present, not qualified)

| Component | Source | Observed implementation |
| --- | --- | --- |
| CoreAudio framework | `src/CoreAudio/CoreAudio/CMakeLists.txt` | `add_framework(CoreAudio FAT ...)`, PulseAudio dependency |
| CoreAudio object API | `src/CoreAudio/CoreAudio/AudioHardware.cpp` | object/property, IOProc, start/stop entry points |
| PCM format/properties | `src/CoreAudio/CoreAudio/AudioHardwareImpl.cpp` | ASBD, device properties, stream creation |
| PulseAudio transport | `src/CoreAudio/CoreAudio/pulse/` | context, playback/capture streams, GCD event loop |
| AudioToolbox | `src/CoreAudio/AudioToolbox/CMakeLists.txt` | AudioQueue, AudioConverter, AudioFile, AudioComponent sources |
| AudioUnit | `src/CoreAudio/AudioToolbox/CMakeLists.txt` | AudioUnit framework reexports AudioToolbox |
| CoreAudio.component | `src/CoreAudio/CoreAudioComponent/CMakeLists.txt` | AUHAL, DefaultOutputAU, SystemOutputAU bundle |
| Native dependencies | `src/CoreAudio/CMakeLists.txt` | FFmpeg, PulseAudio; wraps libpulse and FFmpeg ELF libraries |
| CoreMIDI | `src/frameworks/CoreMIDI/` | separate virtual and experimental ALSA implementation |

Do not infer API completeness from the existence of source files. A complete
function-by-function export/behavior matrix requires a built Mach-O binary and
target SDK symbol inventory; those have **not** been produced by CA-01.

## Source findings — reproduce before fixing

### CA01-F01 — PCM ASBD bytes-per-frame calculation (P0, confirmed source defect)

`src/CoreAudio/CoreAudio/AudioHardwareImpl.cpp` sets both
`mBytesPerFrame` and `mBytesPerPacket` using
`mChannelsPerFrame * mSampleRate * mBitsPerChannel / 8`, in the constructor
and in the stream-format setter. Sample rate does not belong in bytes per
**frame**. At stereo/32-bit/44,100 Hz the expression yields 352,800 instead
of 8. Check interleaving/packing and frames-per-packet before implementing a
general formula; a minimal interleaved, packed, one-frame-per-packet test can
assert 8 bytes/frame and 8 bytes/packet.

Gate: regression on default and changed ASBD; do not patch without confirming
existing callers' expectations and format validity.

### CA01-F02 — host clock is a stub (P0 for timebase; confirmed)

`src/CoreAudio/CoreAudio/HostTime.mm` implements
`AudioGetCurrentHostTime()` as `STUB(); return 0;`.
`AudioHardwareImpl::getCurrentTime()` and `getNearestStartTime()` also
zero their output, and `start()` marks timing TODO.

Gate: monotonic, nonzero host-time progression; conversion/units and
AudioTimeStamp flags audited separately. Do not claim realtime accuracy.

### CA01-F03 — duplicate map key for system output (P1, confirmed)

`AudioHardware.cpp::initObjects()` inserts the regular output under
`kAudioObjectSystemObject + 1`, then attempts to insert the event/system
output with the **same map key**, while constructing the object with ID
`kAudioObjectSystemObject + 3`. `std::unordered_map::insert` does not
replace the existing key. The system-default-output property advertises +3,
but the object is not inserted at that key.

Gate: enumerate default output/input/system output; resolve each ID and check
its type/identity. Correct the key in a separate regression-backed patch.

### CA01-F04 — lifecycle, callback and error handling (P1, risk; unproven)

`AudioHardwareImpl::start()` constructs a stream and records it before the
asynchronous PulseAudio context/stream is necessarily ready.
`AudioHardwareStreamPA::stop()` calls `pa_stream_disconnect(m_stream)`
without an explicit null check; `m_stream` is initialized asynchronously.
`AudioHardwareImpl::stop()` mutates `m_streams` without the same
`m_procMutex` used by `start()`; callback code holds `m_stopMutex`.
Review callback reentrancy, lock ordering, failed connects and teardown
before interpreting any audio smoke as stable.

Gate: deterministic failure injection, repeated start/stop, concurrent
callback/dispose, sanitizers where available. This is a **risk assessment**,
not a demonstrated crash.

### CA01-F05 — PulseAudio callback output contract (P1, risk; unproven)

`pulse/AudioHardwareStreamPAOutput.cpp` calls `pa_stream_begin_write`
then passes the buffer to the client's `AudioDeviceIOProc`, and uses the
callback-updated `mDataByteSize` in `pa_stream_write`. Return values,
capacity and partial-write bounds need explicit qualification. The callback
currently uses zeroed placeholder timestamps.

Gate: callback produces known PCM frames, byte counts never exceed allocated
space, failed PA calls stop cleanly, stream output is captured and compared.
Audible sound is an additional gate, not a replacement for byte validation.

### CA01-F06 — incomplete AudioToolbox input (P2, confirmed)

`src/CoreAudio/AudioToolbox/AudioQueue.cpp::AudioQueueNewInput()` returns
`unimpErr`. This does not mean all CoreAudio capture is absent: the
PulseAudio CoreAudio input stream exists separately.

Gate: qualify direct CoreAudio input first; AudioQueue input and AudioUnit
are later lots, prioritized by actual Logic 8 imports.

## Proposed API/behavior matrix for CA-02

| Contract | Source path | Source-level state | Runtime status |
| --- | --- | --- | --- |
| `AudioObjectGetPropertyData[Size]` | `AudioHardware.cpp` | entry points present | NOT TESTED |
| `AudioHardwareGetProperty[Info]` | `AudioHardware.cpp` | entry points present | NOT TESTED |
| `AudioDeviceCreateIOProcID` | `AudioHardware.cpp` | entry point present | NOT TESTED |
| `AudioDeviceStart/Stop` | `AudioHardware.cpp` | entry points present | NOT TESTED |
| PCM ASBD property | `AudioHardwareImpl.cpp` | present; F01 defect | NOT TESTED |
| Default output IDs | `AudioHardwareImplPA.cpp` | present; F03 mismatch | NOT TESTED |
| PulseAudio output | `pulse/AudioHardwareStreamPAOutput.cpp` | code present | NOT TESTED |
| PulseAudio input | `pulse/AudioHardwareStreamPAInput.cpp` | code present | NOT TESTED |
| `AudioGetCurrentHostTime` | `HostTime.mm` | zero stub | NOT TESTED |
| `AudioQueueNewOutput` | `AudioToolbox/AudioQueue.cpp` | entry point present | NOT TESTED |
| `AudioQueueNewInput` | `AudioToolbox/AudioQueue.cpp` | unimplemented | NOT TESTED |
| AudioUnit/AudioComponent | `AudioToolbox/`, `CoreAudioComponent/` | build sources present | NOT TESTED |

## CA-02 gate: build and inspect actual Darling binaries

1. **Preflight**: on Debian 13/5700X, check `git status -sb`, source HEAD,
   CMake cache, toolchain, and whether an existing build tree already has
   CoreAudio enabled. Do not modify the Carbon build tree or MIDI sparse clone.
2. **Offline dependency gate**: inspect the existing CMake/Ninja commands for
   `curl`, `wget`, `git clone/fetch/pull` and URLs; STOP before executing
   any network-capable build step. No package installs or downloads without
   explicit permission.
3. **Compile** CoreAudio from a separate build tree using the repository's
   actual CMake target. Report exact command, exit code and first errors.
4. **Inspect** the produced file with `file` and Mach-O-aware `llvm-nm`;
   verify the exported entry points and dependent dylibs. A host ELF shared
   library is **not** sufficient.
5. **Load** the framework through Darling using a minimal Mach-O client that
   requests the default output device and PCM stream format. Report result
   separately from compile and export checks.
6. Preserve the test log, branch/HEAD, tool versions, and a PASS/FAIL/SKIP
   matrix. Do not start audio playback until the format and lifecycle defects
   are characterized.

### M1 and M2 acceptance criteria

- **M1 / PASS**: Mach-O CoreAudio builds, exports verified, and the real
  Darling loader successfully resolves a minimal CoreAudio client.
- **M2 / PASS**: after targeted fixes, the client produces a 440 Hz stereo
  PCM stream; captured sample bytes match expected amplitude/frequency,
  audio is heard through an actual Linux output, and stop/restart is clean.
- **SKIP**: required PulseAudio runtime, audio sink, or Darling loader is
  unavailable; report missing prerequisite precisely.
- **FAIL**: compiler, linker, loader, API, data, or runtime contract fails;
  attach logs and do not relabel as PASS.

## Implementation order

1. CA-01 source audit (this document): **review delivered; no runtime pass**.
2. CA-02 build preflight and genuine Mach-O export/loader qualification.
3. F01/F03 regression tests and minimal corrections, isolated from Carbon.
4. F02 host-time implementation only with clock/ABI tests.
5. F04/F05 callback and stream lifetime checks, then 440 Hz output smoke.
6. Later: input capture, format negotiation, AudioToolbox/AudioUnit, CoreMIDI
   synchronization and Logic Studio 8 integration.

No percentage completion is asserted by this audit. Existing Darling
infrastructure is substantial, but the number of lines present is not
a measure of runtime compatibility.
