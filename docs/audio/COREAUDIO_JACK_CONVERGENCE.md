# CoreAudio / Ninja / JACK convergence

**Status (2026-10-26):** CA-10C PASS on the user's 5700X terminal: source contract, generated PulseAudio C, Mach-O wrapper object and 13/13 isolated-fixture regression tests. CoreAudio / libpulse linkage is NOT TESTED. Separate Darling runtime CA-12 launch test FAILED (RPC error and timeout), cause pending; do not infer Logic Studio 8 compatibility.

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

The test suite uses **synthetic fixtures** for optional headers and Mach-O headers. The user executed 13/13 cases on the 5700X in CA-10C; this proves the verifier's local control flow, not the real Darling loader or audio playback.

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
| P0 | N1 reproducible wrapper contract | Source rule + optional header + Mach-O object | PASS on 5700X CA-10C; 13/13 mock-fixture unit tests PASS on 5700X |
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

## 10. Field qualification update (2026-10-26, CA-10C / CA-12)

Evidence origin: terminal output pasted by the user from **Debian 13 / WSL2 on the 5700X**. GitHub does not have access to the live filesystem or runtime; the branch update here is documentation-only, not a new local execution.

### CA-10C — PASS, local verifier actually executed

- Retrieval integrity: `HASH_PASS: verify.py`, `HASH_PASS: test_verify.py`; expected pinned Git blob SHA values were checked by the user's script.
- `CA10_CONTRACT=PASS`: repository `wrap_elf.cmake` and `wrapgen.cpp` support an optional variable header.
- `CA10_PULSE_C=PASS`: generated `pulse.c` is **63,102 bytes**.
- `CA10_PULSE_VARS=SKIP_OPTIONAL`: no `pulse_vars.h`, which is valid for this build.
- `CA10_OBJECT_MACHO=PASS`: x86_64 MH_OBJECT file verified.
- `CA10_VERDICT=PASS`.
- `python3 -m unittest discover -s "$HOME/d4rling-ca10c-tests" -p "test_verify.py" -v`: **13 tests run, 0 failures, PASS** on the 5700X; fixture tests do not demonstrate linker success.
- `libpulse.dylib`, linked CoreAudio, exports, JACK audio and actual Logic 8: **SKIP**.

### CA-12 — FAIL, Darling runtime, distinct from the audio build

The user's `/usr/local/bin/darling exec` smoke for `echo` ended with `CA12_echo_RC=137`, `mach_msg_overwrite failed (internally): -111`, repeated `dserver_rpc_interrupt_enter failed with code -111`, and an explicit timeout/forced-termination marker. It is **not** evidence of CoreAudio or JACK malfunction. The root cause is **unknown** until server/prefix state, guest executable availability and shellspawn launch / exit-status behavior are inspected without destructive cleanup.

An earlier local `shellspawn.c` excerpt has `close(shellfd[0])` inside a loop over `i`, and uses `WEXITSTATUS` without a successful `waitpid` + `WIFEXITED` guard. These are separately actionable source concerns, but **not** yet proven to cause CA-12. Do not combine the shellspawn fix with the CoreAudio wrapper PR.

### Next gates

1. **Audio CA-11** (read-only initial gate): inspect wrapper dynamic link command and enumerate direct/implicit tool/library artifacts from Carbon and Audio, checking compatible Mach-O or ELF formats and exact target paths. Do not unconditionally trigger the 2,590-action Ninja graph or copy the 46 reusable files.
2. **Runtime CA-12R** (independent): capture Darling process list, `DPREFIX` effective path, guest binary existence and non-destructive logs. Do not run `killall`, `rm -rf`, reinstall or modify live prefixes while testing the audio link.
3. **JACK N3**: isolate backend design and mock RT callback/lifecycle tests. JACK remains HYPOTHESIS.


## 11. CA-11 exact wrapper link preflight (2026-10-26)

Evidence origin: another user's terminal report from Debian 13 / WSL2 on 5700X; **read-only inspection**, no dynamic link executed.

| Check | Actual observation |
| --- | --- |
| \`ninja -t commands src/CoreAudio/libpulse.dylib\` | One shared-library link command identified |
| Command SHA-256 | \`c65d3d5e2df45afaa7d3bc2c31377d72e49bf3cd860efe0e623fc55fc8eea3a9\` |
| Wrapper Mach-O object | 1/1 exists in Audio tree |
| "Direct libs" from *heuristic token scanner* | 2 paths: 1 is a Carbon build candidate; **the other is the output \`src/CoreAudio/libpulse.dylib\` itself, which must not count as a missing input** |
| \`-Wl,-dylib_file\` target paths | 144 supplied; 45 exist in Carbon, 99 absent from both trees |
| Darling \`ld64\` | Missing in Audio tree; present in Carbon tree as **Linux x86_64 ELF host executable**, as expected |
| Actual \`libpulse.dylib\` | NOT LINKED; no PASS claim |

The huge \`-dylib_file\` map is *not* evidence that 99 dylibs are unconditional link-time inputs. First establish the exact direct Ninja target inputs (\`ninja -t query\`) and which mappings the link actually consumes. **Do not copy 45 Carbon artifacts, start a full Ninja dependency tree, or interpret \`-o\` output as an input.** Carbon configuration has \`COMPONENTS=core\` and Clang-19 explicit paths, whereas Audio has \`COMPONENTS=gui\` and generic Clang paths. Confirm tool compatibility before a single targeted link in a separate output path.

Separate CA-12 replay remains **FAIL**: echo command exit 137 after timeout, RPC \`-111\`; no new runtime root cause. Do not alter shellspawn or kill the live server as part of the audio link lot.

**Next CA-11B gate**: print the exact direct Ninja inputs, inspect \`-fuse-ld\` and auxiliary tool paths, check current existing \`libSystem.B.dylib\` candidate format, and identify any link command side effects. Only after this preflight consider a one-shot controlled Mach-O linker probe, with a non-production output name and no downloads.

## 12. CA-11B / CA-11C — First isolated Mach-O dynamic library (2026-10-26)

**Evidence:** exact stdout pasted by the user from the 5700X, Debian 13 / WSL2; GitHub tooling did **not** execute the local link.

### CA-11B — PASS, direct inputs audited
`ninja -t query src/CoreAudio/libpulse.dylib` identifies **one** object (`pulse.c.o` in Audio) and **one** directly linked Mach-O `libSystem.B.dylib` (already in Carbon); order-only prerequisites include ld64, lipo, libSystem and wrapgen. `ninja -t commands` reports 144 `-dylib_file` mappings. These are linker maps, not 144 proven direct dependencies. Tools: `ld64` from Carbon is an ELF x86_64 host executable (expected); `libSystem.B.dylib` is Mach-O x86_64.

### CA-11C — LINK_PASS, user-executed isolated link
A single command adapted from Ninja's link line, changing the output path to a distinct temporary directory, using Carbon ld64 and libSystem and redirecting 45 existing mapping paths, **exited 0**:

- Output: `/home/Deniel/d4rling-ca11c-ci_c19yl/libpulse.dylib`
- `LINK_EXIT=0`
- `OUTPUT_FORMAT=Mach-O 64-bit x86_64 dynamically linked shared library, flags:<NOUNDEFS|DYLDLINK|TWOLEVEL|NO_REEXPORTED_DYLIBS>`
- `OUTPUT_BYTES=83196`
- `SYMBOL__pa_context_new=PASS`, `SYMBOL__pa_stream_write=PASS`, tested with `llvm-nm-19 -g`
- `CARBON_MAPPINGS_REUSED=45` means 45 mapping arguments were redirected to Carbon candidates; it does **not** prove that ld64 consumed all 45.
- No file in the original Carbon or Audio build tree was overwritten. The isolated result is **not** installed into Darling.

**Gate outcome: CA-11C = PASS for Mach-O shared-library linking and named-symbol presence only.** Load commands, install name, runtime loader, PulseAudio PCM and JACK are still SKIP. Presence in `llvm-nm -g` alone does not formally establish defined-vs-undefined symbol status until a `--defined-only` check is run.

### Next: isolated CoreAudio framework link

The source audit already established 11 CoreAudio Mach-O objects and four direct library paths: `libc++.1.dylib`, `CoreFoundation`, the just-built `libpulse.dylib`, and `libSystem.B.dylib`. Use the actual unmodified Ninja link command with only these exact direct paths and the validated Carbon `ld64` redirected to existing locations. Keep output isolated outside all build trees and verify Mach-O x86_64 plus defined API exports. Any linker failure is a diagnostic **FAIL/BLOCKED**, never a reason to copy unknown binaries or rebuild thousands of targets automatically.

An entirely separate CA-12 Darling RPC smoke still fails (-111, timed-out exit 137). Do **not** mix runtime shellspawn fixes with CoreAudio linking.

## 13. CA-11D — Linked CoreAudio Mach-O image (2026-10-26)

**Evidence provenance:** output pasted by the user from their **5700X Debian 13 / WSL2** terminal. This GitHub documentation commit did not execute the linker locally. Earlier CA-11C PulseAudio wrapper is at `/home/Deniel/d4rling-ca11c-ci_c19yl/libpulse.dylib`.

### Observed local results — PASS for link and defined exports only

| Gate | Observed output |
| --- | --- |
| CoreAudio compilation inputs | `COREAUDIO_OBJECTS=11/11 PASS` |
| Direct library input candidates | `DIRECT_LIBRARIES=4/4 PASS` (Carbon libc++, CoreFoundation, libSystem; isolated CA-11C libpulse) |
| Reused linker | `LD64=PASS` |
| Redirected Carbon linker mappings | `CARBON_MAPPINGS=45` (**path mappings**, not evidence all were loaded) |
| Link exit | `LINK_EXIT=0` |
| Mach-O output | `Mach-O 64-bit x86_64 dynamically linked shared library`, flags `NOUNDEFS|DYLDLINK|TWOLEVEL|WEAK_DEFINES|BINDS_TO_WEAK|NO_REEXPORTED_DYLIBS` |
| File size | `OUTPUT_BYTES=268316` |
| Defined export check | `EXPORTS_PASS=6/6`, `llvm-nm-19 -g --defined-only` |
| Gate verdict | `CA11D_STATUS=LINK_AND_EXPORTS_PASS` |
| Output path | `/home/Deniel/d4rling-ca11d-kz4obkta/CoreAudio` |
| Log | `/home/Deniel/d4rling-ca11d-kz4obkta/link.log` |

**Six defined symbols verified:** `_AudioObjectGetPropertyData`, `_AudioObjectGetPropertyDataSize`, `_AudioDeviceCreateIOProcID`, `_AudioDeviceStart`, `_AudioDeviceStop`, `_AudioGetCurrentHostTime`.

This is a successfully linked **Mach-O image for the CoreAudio framework target**, not yet a complete installed `.framework` bundle. Link success and symbol definition **do not imply** API correctness; `AudioGetCurrentHostTime` remains a known zero-return stub (CA01-F02), despite being exported. No Darling load or PCM execution attempted (CA-12 runtime RPC failure remains independent).

### Next isolated CA-11E — inspect Mach-O load commands, not execute guest

Read-only inspect *both* actual images with `file`, `llvm-objdump-19 --macho --dylibs-used` (if tool supports this) or `llvm-otool-19 -L`, `llvm-objdump-19 --macho --private-headers`, `llvm-nm-19 --undefined-only`, `llvm-nm-19 -g --defined-only`. Verify installation IDs, logical dependency names, architecture, unresolved imports and absence of hardcoded paths to temporary build directories. Compare expected dependency paths against the runtime layout **without** copying/installing anything into the live Darling prefix. Limit verbose command output and store exact command/result logs. Only after this audit design loader/runtime tests; do not retry the failing `darling exec` loop until CA-12 RPC is diagnosed.

### Convergence decision

**Build track:** first CoreAudio Mach-O link + six exports PASS, a significant and reproducible linker milestone. **Runtime/JACK track:** SKIP pending loader and backend; do not claim Logic Studio 8 or JACK support. Preserve PulseAudio, ALSA and Carbon work unchanged. The PR remains a draft, targeting `work/core-audio` rather than default `master`.

## 14. CA-11E — Mach-O load-command and dependency audit (2026-10-26)

**Provenance:** stdout supplied by the user from the 5700X (Debian 13 / WSL2). GitHub tools did not inspect the binaries directly. Read-only command; **no guest runtime execution**.

| Binary | Size | Mach-O load cmds | LC_ID_DYLIB | LC_LOAD_DYLIB | LC_RPATH | Defined exports | nm undefined-symbol lines |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| `libpulse.dylib` | 83,196 | 15 | `/usr/lib/native/libpulse.dylib` | 1 (`/usr/lib/libSystem.B.dylib`) | 1 | 2/2 | 3 |
| CoreAudio | 268,316 | 19 | `/System/Library/Frameworks/CoreAudio.framework/Versions/A/CoreAudio` | 5 | 1 | 6/6 | 107 |

Five CoreAudio direct dependency IDs: `/usr/lib/libc++.1.dylib`, `/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation`, `/usr/lib/native/libpulse.dylib`, `/usr/lib/libSystem.B.dylib`, and `/usr/lib/libc++abi.dylib`.

**Portability concern:** both images embed a single `LC_RPATH` string containing absolute host build paths. The scanner reported `HOST_PATH_LEAKS=1` per file because it counted one command, **not** each colon-separated directory. PulseAudio lists two build directories, CoreAudio lists six. These paths are host-specific and need justification/removal before distribution; they are **not**, by themselves, proof that the linker or dyld failed. Mach-O `LC_RPATH` is a load-command path, not automatically identical to Linux's colon-separated `LD_LIBRARY_PATH` semantics.

`llvm-nm-19 --undefined-only` reported 3 and 107 *lines*, respectively, including expected dependencies (`__elfcalls` and CoreFoundation/Blocks/C++ helpers); unresolved-import existence is not equivalent to unresolved runtime failure. Real runtime dependency resolution remains **SKIP**, CA-12 RPC server still **FAIL**. No conclusion on Logic Studio 8 or JACK.

**Verdict:** `CA11E_STRUCTURE=PASS` (load-command structure and named symbol checks); **packaging portability = NEEDS_ACTION**, **runtime = SKIP**. Do not install either library into the active Darling prefix yet.

**Next CA-11F:** inspect the *exact* `-rpath` linker argument(s) from the saved CA-11D `command.txt` and extracted CA-11C Ninja command; count host path segments, check all install-name dependencies; then formulate a **separate, isolated** one-shot relink omitting host-only RPATH. Preserve original CA-11C/CA-11D artifacts and record both old/new signatures and symbols. No full Ninja graph, installs, runtime restart, or speculative source patches.
