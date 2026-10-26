# CoreAudio / Ninja / JACK convergence

**Status (2026-10-26):** CA-10B wrapper generation and object compilation PASS **on the user's reported 5700X terminal log**; CoreAudio link and audio runtime NOT TESTED. GitHub source audit and a separate mocked verifier test suite are distinct evidence. Do not infer Logic Studio 8 compatibility.

## 1. Shared objective and architecture

Target: Logic Studio 8 (macOS guest) -> Darling CoreAudio HAL/API -> selected backend -> JACK2 or PipeWire-JACK -> ALSA / host audio hardware. The existing PulseAudio backend remains a supported path. CoreMIDI/ALSA sequencer work is separate from the PCM device transport.

One CoreAudio API contract, not two competing CoreAudio implementations. Keep AudioObject and AudioDevice semantics above a future backend abstraction. JACK is the preferred *candidate* for professional audio, not yet the verified default; neither PulseAudio nor ALSA is removed.

Candidate layers:
1. Apple-facing CoreAudio exports and object/property model (unchanged public ABI).
2. Backend-neutral device/stream lifetime, ASBD, buffer, callback, clock and error contracts (design under review).
3. PulseAudio backend (existing), JACK backend (proposed); retain optional ALSA route for future study.
4. Native JACK server or PipeWire JACK-compatible implementation; ALSA below as appropriate.

**No JACK backend implementation has yet been committed in this lot.** A direct port of the historical JackRouter CoreAudio HAL plugin is not assumed to work inside Darling.

## 2. Version and branch inventory

- Repository: https://github.com/fr4nck/d4rling
- Audio baseline: `work/core-audio` at `e05f18ab851fe676039903c66a26a4c3f137317e`, GitHub verified 2026-10-26.
- Repository default branch is `master`, **not** `main`; audio is **23 ahead / 9 behind** master at the time of this audit. No merge or rebase performed.
- Carbon PR #4 is still a draft; do not rewrite Carbon / CoreMIDI work to unblock audio.
- This convergence lot lives on `work/coreaudio-ninja-convergence`, branched from the audio baseline, and should target `work/core-audio` for review.
- Local checkout branch, cleanliness and uncommitted changes on the 5700X are **unknown to GitHub**; do not treat the remote HEAD as local `git status`.

## 3. CA-02 through CA-10B evidence ledger

These host entries come from interactive terminal output reported in the 2026-10-26 conversation. The present GitHub-side work did **not** rerun them on the 5700X.

| Gate | Status | Evidence / limitation |
| --- | --- | --- |
| CA-02 CMake GUI, Clang 19.1.7, x86_64, FFmpeg, PulseAudio | PASS, user log | CMake `COMPONENTS=gui`, Ninja generated |
| CA-03 full CoreAudio target dry-run | PASS, user log | 3,238 scheduled operations; 0 textual network matches is **not** proof of offline safety |
| CA-04 single `AudioHardware.cpp.o` | PASS, user log | Mach-O 64-bit x86_64 |
| CA-05 all CoreAudio objects | PASS, user log | 11/11 Mach-O relocatable objects |
| CA-06 full link preflight | BLOCKED | 11/11 objects, 0/4 direct library paths, 0/144 mapped library paths, missing ld64 in audio build |
| CA-07 Carbon reuse candidates | PARTIAL | 46/146 referenced paths exist in `d4rling-build-carbon`; no ABI/option compatibility proof |
| CA-08 Carbon `ninja -n CoreAudio` | EXPECTED FAIL | `UNKNOWN TARGET` with `COMPONENTS=core`; not a compiler defect |
| CA-09 wrapgen availability | PASS, user log | Carbon wrapgen executable exists; Linux `libpulse.so` available |
| Initial CA-10 check | FAIL, verifier only | `WRAPGEN_EXIT=0` yet script demanded BOTH generated files |
| CA-10B corrected verification | PASS, user log | `pulse.c` 63,102 bytes; optional `pulse_vars.h` absent; `pulse.c.o` Mach-O x86_64 |
| `libpulse.dylib` | SKIP | No successful link shown |
| Linked CoreAudio, exports, loader and actual playback | SKIP | No valid end-to-end evidence |
| JACK/JACK2/PipeWire-JACK runtime | SKIP | No real server/client/capture qualification |

### Root cause for CA-10

- `src/CoreAudio/CMakeLists.txt` calls `wrap_elf(pulse libpulse.so)`.
- `cmake/wrap_elf.cmake` registers **only** `pulse.c` as a required `add_custom_command(OUTPUT ...)` artifact; it passes `pulse_vars.h` as the third generator argument.
- `src/libelfloader/wrapgen/wrapgen.cpp` opens the optional header **only inside** `if (!vars.empty())`.
- CA-10's stop condition was therefore wrong when PulseAudio supplied no exported ELF data symbols requiring variable shims.
- CA-10B verifies the generated C and compiled Mach-O object successfully. **No generator source repair is justified.**

The regression tool is `tests/regressions/coreaudio-wrapgen/verify.py`. It performs read-only source-contract and artifact inspection, without Ninja builds or network calls. Absence of the optional header yields `SKIP_OPTIONAL`, never a false failure. It parses Mach-O header magic, CPU type and object file type. It **does not** prove dynamic linking or wrapper runtime correctness.

To run on a checkout containing the verifier (with already-built 5700X artifacts):

```sh
python3 tests/regressions/coreaudio-wrapgen/verify.py \
  --source-tree "$HOME/d4rling-carbon-qualif" \
  --build-tree "$HOME/d4rling-build-audio"
python3 -m unittest discover \
  -s tests/regressions/coreaudio-wrapgen -p 'test_*.py' -v
```

The separately executed isolated-host suite uses **synthetic fixtures** for optional headers and Mach-O headers. It must never be reported as a real Darling build, load or playback test.

## 4. Source-level CoreAudio API matrix (N2)

Definitions and CMake wiring were read from `work/core-audio`. "Present" means a source-level entry point or implementation, **not** a confirmed Mach-O export nor correct runtime behavior. Actual Logic 8 imports have not been captured.

| Contract | Source state | Existing backend | JACK mapping hypothesis | Required gate |
| --- | --- | --- | --- | --- |
| AudioObject property get/set/size/has | Entry points in `AudioHardware.cpp`; delegated to `AudioHardwareImpl` | PulseAudio objects | Device and stream properties backed by JACK capabilities | Default device, sizes, qualifier and errors |
| AudioObject property listeners | Functions present; base methods return unknown-property error | Stub/partial | Event propagation on device/sample-rate changes | Add/remove callbacks, notification ordering |
| AudioDevice enumeration/default IDs | System/input/output IDs provided; **system output ID +3 not inserted** (CA01-F03) | PulseAudio | JACK port inventory and stable IDs | Resolve all advertised IDs |
| AudioDevice IOProc create/destroy, start/stop | Entry points and stream map present; lifecycle risks (CA01-F04) | PulseAudio | JACK process lifecycle via backend adapter | Repeated start/stop, cancellation, races |
| AudioStreamBasicDescription/PCM | Present, but bytes-per-frame formula incorrectly multiplies by sample rate (CA01-F01) | PulseAudio format negotiation | Convert interleaved/planar PCM to JACK float planar | 2ch 32-bit 44.1 kHz -> 8 bytes/frame |
| Device clocks and host time | `AudioGetCurrentHostTime` returns zero (CA01-F02); other time methods zero | Stub | Clock and timestamp translation with monotonic source | Nonzero monotonic time; drift and conversion |
| Output callback/data bounds | PA output code present; capacity/error handling not qualified (CA01-F05) | PulseAudio | JACK process buffer and bounded conversion | Guard bytes, underruns, callback status |
| Direct CoreAudio capture | PA input classes exist; no runtime qualification | PulseAudio | JACK capture ports | Loopback/capture byte comparison |
| AudioQueueNewOutput | Entry point present | AudioToolbox / PA path | Retain front-end behavior | AudioQueue smoke |
| AudioQueueNewInput | Returns `unimpErr` | Stub | Later | Explicit unsupported behavior |
| AudioUnit/AudioComponent | Build sources and CoreAudio.component present | Partial / not qualified | Must use same device backend | AudioUnit HAL discovery/instantiate |

Other known source risks from CA-01: `AudioHardwareImpl::stop` accesses the stream map without the start mutex; `pa_stream_begin_write` return/capacity requires bounds checks; `getPAContext` is asynchronous. No fixes were made in this documentation/regression lot.

## 5. JACK/JackRouter reference study (N3)

- Historical code: https://github.com/jackaudio/jack-router — original JackRouter sources, marked **unmaintained**; inspect architectural patterns but do not transplant its macOS coreaudiod plugin into Darling.
- JackRouter AudioServerPlugin design note: https://github.com/jackaudio/jack-router/blob/main/macOS/docs/JackRouter-AudioServerPlugin.md
- Official JACK callback and real-time restrictions: https://jackaudio.org/api/group__ClientCallbacks.html
- JACK client creation/activation: https://jackaudio.org/api/group__ClientFunctions.html
- JACK sample-rate / buffer-size behavior: https://jackaudio.org/api/group__ServerControl.html
- PipeWire's JACK compatibility: https://github.com/PipeWire/pipewire/blob/master/INSTALL.md

Potential adapter entry points: `jack_client_open`, `jack_port_register`, `jack_set_process_callback`, `jack_activate`, `jack_port_get_buffer`, `jack_get_sample_rate`, `jack_set_buffer_size_callback`, `jack_set_xrun_callback`.

**Hard real-time constraint:** JACK `process` callback must not block, allocate, log, wait on a mutex or perform arbitrary I/O. Darling's current CoreAudio `AudioDeviceIOProc` callbacks are not yet audited for these restrictions. Direct invocation from JACK's process thread is **not** approved by this document; explore a preallocated bounded lock-free transport and an explicitly qualified callback scheduling contract, with measured added latency.

JACK buffers are generally per-channel float audio; the existing CoreAudio ASBD and PulseAudio interleaved formats require explicit channel layout, sample precision, stride and capacity checks. Changes in JACK sample rate and buffer size require notifications and deterministic stream transitions.

A JACK2 server and PipeWire-JACK client-library substitute must be treated as **separate test environments**, not interchangeable proof. WSL2 physical ALSA and realtime scheduling are unverified.

## 6. Shared contracts / ownership

**CoreAudio/Ninja conversation** owns wrapper generator qualification, compilation dependencies, Mach-O link/export checks and the verifier in `tests/regressions/coreaudio-wrapgen/`. It may correct demonstrated non-backend build defects. It must not introduce a parallel JACK HAL or replace PulseAudio.

**JACK conversation** owns a proposed adapter contract and JACK-specific tests in a separate path and branch. Before editing `AudioHardware.cpp`, `AudioHardwareImpl.*`, `AudioHardwareStream.*` or CoreAudio CMake files, coordinate in this document and review outstanding branch diffs.

**Both** preserve the public CoreAudio ABI and CoreMIDI/ALSA/Carbon work. Any mutually touched file gets a sequential reviewed change. In this document, labels mean:
- **PASS** = explicitly executed test with logged evidence and environment.
- **FAIL** = reproduced fault.
- **SKIP** = no execution / unavailable prerequisite.
- **HYPOTHESIS** = design not verified.

## 7. Decisions and rejected shortcuts

1. **Retain** existing PulseAudio backend; **do not** replace with JACK until tests qualify it.
2. **Reject** treating `pulse_vars.h` as always mandatory: contradicted by actual wrapgen source and CA-10B.
3. **Reject** "148 files missing" as "148 independent compilation units"; linker mappings can be transitive.
4. **Reject** copying 46 Carbon binaries into Audio build blindly; compiler settings and build configurations differ.
5. **Reject** "11 objects compile" as "framework links / runs".
6. **Defer** touching `wrapgen.cpp`, HAL, callback code and CMake in this lot, because no regression-backed repair to those sources has been established.
7. **Defer** direct JACK CoreAudio callback on JACK process thread pending RT suitability analysis.

## 8. Convergence test gates and priorities

| Priority | Gate | Required evidence | State |
| --- | --- | --- | --- |
| P0 | N1 reproducible wrapper contract | Source rule + optional header + Mach-O object | PASS user CA-10B; isolated verifier mocks PASS; verifier not run on 5700X |
| P0 | CA-11 wrapper link | `libpulse.dylib` Mach-O, dependent libs and symbols | SKIP |
| P0 | CA-12 CoreAudio link | Real Mach-O x86_64 framework and expected symbols, no broken dependencies | SKIP |
| P0 | Loader smoke | Darling loads CoreAudio and resolves system/default output ID | SKIP |
| P0 | PCM regressions CA01-F01/F03 | Format bytes and default device IDs | SKIP |
| P0 | HAL callback lifetime | Error injection, start/stop and concurrency | SKIP |
| P1 | JACK contract mock | Fake JACK process cycles, sample rate changes, bounded ring buffer, RT forbidden calls audit | HYPOTHESIS |
| P1 | Real JACK2 / PipeWire-JACK | Measured latency, xruns, routing, capture, format/clock validity | SKIP |
| P1 | AudioUnit and Logic 8 | Real plugin discovery, graph, audio and MIDI integration | SKIP |

Next: inspect `ninja -t commands src/CoreAudio/libpulse.dylib` and compare **first-pass library dependencies**, not 2,590 unconditional build actions; qualify compatible existing tools or produce only required artifacts in an explicitly offline build. Then repeat for CoreAudio and inspect exports via `llvm-nm-19`. No downloads, installations or expensive CI in this lot.

## 9. Coordination protocol

At the start of each audio or JACK lot, read the latest committed version of this document from GitHub, record current branch/HEAD, compare touched files and check other open PRs. Record observation, patch, tested environment, PASS/FAIL/SKIP, commit SHA and unresolved dependency. If updates race, re-read and integrate content; never overwrite or force-push. Merge into the active audio work branch only after review; default branch is `master` and must not be modified without explicit approval.

This file is a technical handoff, not an assertion that the second chat has already delivered a JACK implementation.
