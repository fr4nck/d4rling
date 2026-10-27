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

## 15. CA-11F — RPATH link-argument audit (2026-10-26)

**Evidence:** exact terminal stdout provided by user, Debian 13 / WSL2, 5700X; read-only and no link performed.

| Image | RPATH linker arguments | Unrecognized RPATH forms | Colon-delimited segments in single argument |
| --- | ---: | ---: | ---: |
| PulseAudio | 1 | 0 | 2 (`src/external/libsystem`, `src/external/libmalloc` in Audio build) |
| CoreAudio | 1 | 0 | 6 (`libcxx`, `corefoundation`, `CoreAudio`, `libcxxabi`, `libsystem`, `libmalloc` within Audio build) |

The `-Wl,-rpath,` flags are the demonstrable link-time source of absolute host paths in `LC_RPATH`. Mach-O carries one load command per image, whose value has a colon-delimited string: do not claim Darwin interprets each colon segment as a separate independent RPATH. Neither link command was executed in CA-11F. Existing prior images remain untouched.

**Next gate CA-11G:** re-link both images with the single host-specific `-Wl,-rpath,` argument removed, separate outputs outside build trees, re-use only previously verified object/library candidates from Carbon and CA-11C; compare `LC_RPATH` absence, identical `LC_ID_DYLIB` and `LC_LOAD_DYLIB` identities, and 2+6 defined exports. Do not install, change source/CMake, run the broad Ninja dependency graph or retry Darling runtime. Any link failures remain BLOCKED, not a runtime PASS.


## 16. CA-11G — Two isolated Mach-O dylibs linked without host RPATH (2026-10-26)

**Source of evidence:** user's actual Debian 13 / WSL2 terminal output on the 5700X. This GitHub documentation update did not rerun the compiler, linker or runtime.

| Gate | PulseAudio | CoreAudio |
| --- | --- | --- |
| New isolated linker execution | `PULSE_LINK_EXIT=0` | `CORE_LINK_EXIT=0` |
| RPATH load commands, old → new | `1 → 0` | `1 → 0` |
| Install ID unchanged | PASS | PASS |
| Direct Mach-O dependencies unchanged | PASS | PASS |
| Defined symbol probes | 2/2 | 6/6 |
| New file size | 83,196 bytes | 268,316 bytes |
| Overall local gate | `PULSE_STATUS=PASS` | `CORE_STATUS=PASS` |

- Work directory: `/home/Deniel/d4rling-ca11g-yw99dhbq`
- Newly generated binaries: `libpulse.dylib`, `CoreAudio`.
- The exact link commands and diagnostic logs were stored in that work directory. Existing CA-11C/CA-11D binaries and original Carbon/Audio build directories were not replaced.
- `CA11G_STATUS=PASS`, `DARLING_RUNTIME=NOT_EXECUTED`.
- File sizes remaining unchanged is not inherently suspicious, given Mach-O alignment/padding. This alone is not a bytewise equivalence check or evidence of runtime behavior.

**Interpretation:** two usable *link-stage candidates*, with no `LC_RPATH` commands and unchanged `LC_ID_DYLIB` / load-dependency names relative to the earlier outputs. **Not qualified:** full `.framework` bundle packaging, runtime dependency presence/resolution, correct CoreAudio HAL semantics, JACK backend, user PCM or Logic Studio 8. The known host-time zero-return stub is unchanged.

### Next CA-11H — runtime-layout inventory, read-only

Use each new image's `LC_ID_DYLIB` / `LC_LOAD_DYLIB` values to enumerate candidate files under the configured Darling installation root (often `/usr/local/libexec/darling`, verify locally), and **separately** under `DPREFIX=/home/Deniel/d4rling-prefix-runtime-01`. Both are candidate roots, not a promise that Darling dyld resolves names through both locations. Classify `PRESENT_MACHO`, `PRESENT_OTHER`, `BROKEN_SYMLINK`, `MISSING` per dependency. Do not install/copy files into either location, manipulate symlinks, run the loader or delete any prefix data. Keep CA-12 RPC fault separately blocked.

The documentation branch remains `work/coreaudio-ninja-convergence` targeting `work/core-audio` in draft PR #5; no merge/rebase to `master` is authorized.


## 17. CA-11H — Darling host image and prefix inventory (2026-10-26)

**Evidence source:** user-supplied stdout executed on the 5700X / Debian 13 WSL2. The check was read-only; no runtime execution, installation or file modification.

Both candidate roots exist: **host installation** `/usr/local/libexec/darling` and **runtime state prefix** `/home/Deniel/d4rling-prefix-runtime-01`. These locations are *not* proven to be interchangeable guest filesystem roots; absence of a file directly under DPREFIX is not automatically an error.

| Load install name / self path | Host-install candidate | Direct DPREFIX candidate |
| --- | --- | --- |
| PulseAudio self `/usr/lib/native/libpulse.dylib` | MISSING (new staged library not installed) | MISSING |
| PulseAudio dependency `/usr/lib/libSystem.B.dylib` | PRESENT_MACHO | MISSING |
| CoreAudio self `/System/Library/Frameworks/CoreAudio.framework/Versions/A/CoreAudio` | MISSING (new staged framework image not installed) | MISSING |
| CoreAudio dependency `/usr/lib/libc++.1.dylib` | PRESENT_MACHO | MISSING |
| CoreAudio dependency `/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation` | PRESENT_MACHO | MISSING |
| CoreAudio dependency `/usr/lib/native/libpulse.dylib` | MISSING (staged image available) | MISSING |
| CoreAudio dependency `/usr/lib/libSystem.B.dylib` | PRESENT_MACHO | MISSING |
| CoreAudio dependency `/usr/lib/libc++abi.dylib` | PRESENT_MACHO | MISSING |

**Exact assessment:** four of CoreAudio's five direct dependency install names already resolve to physical Mach-O files in the **host installation**; the fifth is newly linked PulseAudio in isolated staging. The PulseAudio image's one direct dependency, libSystem, is already physically installed. Both new binaries themselves remain isolated at `/home/Deniel/d4rling-ca11g-yw99dhbq`.

The local tool reported `PULSE_INVENTORY=PASS`, `CORE_INVENTORY=PASS`, `CA11H_STATUS=INVENTORY_COMPLETE`, `RUNTIME_EXECUTED=NO`, and `INSTALLATION_MODIFIED=NO`.

**Not yet validated:** whether host-installed libraries match the symbols/ABI referenced by isolated new binaries, the precise Darling runtime filesystem mount layering, dyld load behavior, and Logic Studio 8 / JACK. CA-12 still failed RPC -111.

**Next CA-11I:** perform **read-only** symbol-resolution preflight against the host-installed four direct libraries plus the staged new libpulse. Verify each installed candidate's Mach-O x86_64 architecture and its LC_ID_DYLIB against the requested name; enumerate defined global exports and unresolved imports, but do not equate unresolved imports with runtime failures (loader-level, weak or indirect symbol resolution can intervene). Do not copy/install or execute Darling until the independent CA-12 runtime problem is addressed.

## 18. CA-11I / CA-11I-B — CoreFoundation universal Mach-O preflight (2026-10-26)

**Evidence:** exact user terminal output on 5700X / Debian 13 WSL2. No local installed library, runtime prefix, or audio source changed.

### CA-11I stopped before finishing — parser false negative

- libSystem.B.dylib: install ID PASS, 46 defined global symbols.
- libc++.1.dylib: install ID PASS, 1,837 defined global symbols.
- libc++abi.dylib: install ID PASS, 365 defined global symbols.
- Check for installed CoreFoundation aborted with `Unexpected Mach-O format` because the verifier assumed a little-endian thin x86_64 MH_DYLIB header at byte zero. Actual FAT container was not supported by this verifier.
- CoreFoundation symbol count, staged libpulse symbol count, and the PulseAudio/CoreAudio import match comparison **were not executed** by CA-11I.

### CA-11I-B diagnostic result — PASS for universal Mach-O architecture

- Installed CoreFoundation: Mach-O universal binary; `FAT_MAGIC=cafebabe`, 1 architecture, entire file 3,511,980 bytes.
- x86_64 slice: `CPU_TYPE=0x01000007`, start offset 4,096, slice length 3,507,884 bytes; valid little-endian Mach-O 64-bit dylib `FILE_TYPE=6`, 20 load commands.
- User output: `CA11IB_STATUS=PASS_X86_64_DYLIB` and `FILES_MODIFIED=NO`.
- Root cause: a **thin-only verifier false negative**, not a demonstrated CoreFoundation error. The successful CA-11G PulseAudio/CoreAudio links remain valid as link-stage milestones.

### Next CA-11I-C (strict read-only, no installs)

Accept thin and FAT binaries with a bounds-checked x86_64 Mach-O dylib slice, inspect its ID_DYLIB and global symbols. For CoreFoundation FAT, use a temporary extracted thin slice for llvm-nm-19; ensure only the disposable file is created and cleaned up, never the installed library. Compare imports against directly declared library exports, but treat misses as unresolved **static preflight observations**, not proof of failure under Darling dyld. CA-12 RPC -111 remains independently blocked.

## 19. CA-11I-C — FAT-aware symbol inventory (2026-10-26)

**Evidence origin:** 5700X / Debian 13 WSL2 stdout supplied by the user. Read-only host audit; temporary x86_64 CoreFoundation slice automatically cleaned. No test of the Darling runtime or loader.

| Direct provider candidate | Format | ID match | Global defined symbols |
| --- | --- | --- | ---: |
| `/usr/lib/libSystem.B.dylib` | THIN | PASS | 46 |
| `/usr/lib/libc++.1.dylib` | THIN | PASS | 1,837 |
| `/usr/lib/libc++abi.dylib` | THIN | PASS | 365 |
| `/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation` | FAT x86_64 | PASS | 2,251 |
| staged `/usr/lib/native/libpulse.dylib` | THIN | PASS | 378 |

`ID_MISMATCHES=0`, `CA11IC_STATUS=PASS`, `TEMPORARY_SLICE=AUTO_CLEANUP`, `DARLING_RUNTIME=NOT_EXECUTED`.

**Preliminary name-only undefined-symbol comparison** (not a real Darwin two-level lookup or dyld runtime test):
- PulseAudio: 3 imports; 0 matched among *direct* libSystem global defined exports; pending `___cxa_atexit`, `__elfcalls`, `dyld_stub_binder`.
- CoreAudio: 107 imports; 74 matched among the union of four installed direct providers plus staged PulseAudio; 33 pending. Examples: Blocks (`__Block_copy`, `__Block_release`, `__NSConcrete*`), dispatch (`_dispatch_async`, `_dispatch_once`, `_dispatch_source_*`), runtime C/C++ (`__Unwind_Resume`, `___cxa_atexit`, `___stack_chk_*`, `___stderrp`).
- Missing from this *direct name-only* lookup does **not** establish unresolved dyld imports. `libSystem` may be an umbrella with dependencies/reexports, and special Mach-O ordinals can designate dyld or dynamic lookup. Do not report 33 broken ABI symbols.

### Source-grounded wrapper insight

The current `src/libelfloader/wrapgen/wrapgen.cpp` generates `extern struct elf_calls* _elfcalls;` and dynamically resolves ELF symbols through `_elfcalls->dlsym_fatal`, so the `__elfcalls` Mach-O import in `libpulse.dylib` is **expected from the wrapper architecture**. Its provider during actual Darling loading remains to be qualified; a standard dylib export census alone cannot validate the custom loader contract.

### Next gate CA-11J: import ordinals and reexport diagnosis

Inspect `LC_SYMTAB` nlist64 of staged PulseAudio and CoreAudio, including `n_desc` two-level-library ordinals, weak-import flags, and the `LC_LOAD_DYLIB` / `LC_REEXPORT_DYLIB` ordering. Report imports per **expected provider**, plus special dynamic_lookup / executable cases. This is more meaningful than merging all direct libraries' exports. Read-only, bounded output; no downloads, installs, full Ninja builds, or `darling exec`. Runtime CA-12 remains blocked by RPC -111.

## 20. Field sync JACK-01A: i386-13 and CA-11J (2026-10-26)

**Origin:** terminal stdout pasted by the user from the 5700X; neither the i386 build directory nor the isolated CoreAudio dylibs are accessible through GitHub. These are host-reported artifacts, not remote reproducibility claims.

### i386-13: actual built universal `libsystem_kernel.dylib`

- Build path: `~/d4rling-build-i386/src/external/xnu/darling/src/libsystem_kernel/libsystem_kernel.dylib`.
- `file` and `llvm-lipo-19 -info`: a **two-architecture FAT Mach-O dylib** with slices **x86_64 and i386**.
- `llvm-objdump-19 --macho --arch=i386 --private-headers`: **i386 `MH_DYLIB`, 17 load commands, `sizeofcmds=1732`**.
- Listed i386 dependencies: `/usr/lib/system/libsystem_kernel.dylib` (self ID), `libsystem_c.dylib`, `libcompiler_rt.dylib`, `libdyld.dylib`.
- Verified by output of `llvm-nm-19 --arch=i386 -g`: `_mach_msg`, `_mach_port_allocate`, `___thread_selfid`, `_sys_thread_selfid`, `_kernelrpc_mach_port_allocate`. Do not confuse `___thread_selfid` with the literal symbol `_thread_selfid`.
- User-reported `sha256sum`: `430337295ac6cb0167a6e2272c243b00496179b38e0cf51a5cf4bb153fc70586`.
- **PASS for FAT output, i386 header and listed exports.** **SKIP** for a successful i386 guest launch, syscall contract, `mldr32` runtime or Logic Studio 8.

### CA-11J: exact recorded two-level ordinal grouping

`CA11J_STATUS=ORDINAL_AUDIT_PASS`; 3 undefined externals in PulseAudio, 107 in CoreAudio; zero weak imports in either. These are **Mach-O imports attributed to a library ordinal**, not verified bindings under dyld.

| Image | Ordinal provider | Undefined externals |
| --- | --- | ---: |
| PulseAudio | `/usr/lib/libSystem.B.dylib` (LIB_1) | 3 |
| CoreAudio | `/usr/lib/libc++.1.dylib` (LIB_1) | 25 |
| CoreAudio | `CoreFoundation.framework/Versions/A/CoreFoundation` (LIB_2) | 8 |
| CoreAudio | `/usr/lib/native/libpulse.dylib` (LIB_3) | 25 |
| CoreAudio | `/usr/lib/libSystem.B.dylib` (LIB_4) | 33 |
| CoreAudio | `/usr/lib/libc++abi.dylib` (LIB_5) | 16 |

PulseAudio's three entries assigned to libSystem are `___cxa_atexit`, `__elfcalls` and `dyld_stub_binder`; CoreAudio's 33 assigned to libSystem include Blocks, Dispatch, `__Unwind_Resume`, `___cxa_atexit` and other runtime support symbols. **Caution:** earlier 33 name-only direct-provider misses aligned with this libSystem ordinal group, but absence of these names in a tiny libSystem umbrella export list is not proof that reexports or custom dyld mechanisms will fail. Investigate bind/reexport/loader semantics before concluding either PASS or FAIL of actual resolution.

Current explicit CA-12 guest smoke remains **FAIL**, `mach_msg_overwrite` / RPC code `-111`, exit `137` on timeout; source root cause unproven. Do not restart the server or edit shellspawn in this JACK lot.

### GitHub coordination preflight

- Verified remote audio branch `work/core-audio` HEAD `e05f18ab851fe676039903c66a26a4c3f137317e`; default branch is `master`, not `main`.
- At analysis start, `work/coreaudio-ninja-convergence` HEAD `2c24a3735a7647a61e1498489410db5c2ba38fc6`, PR #5 open **draft** targeting `work/core-audio`.
- Compare at that HEAD: **11 commits ahead, 0 behind, three file paths only**: `docs/audio/COREAUDIO_JACK_CONVERGENCE.md` and two `tests/regressions/coreaudio-wrapgen` Python files. New sync commit here changes **only this existing shared document**.
- No i386 branch with `i386` in its name surfaced from the GitHub branch-name search; that does **not** imply no i386 work in local build trees or other branches.

## 21. JACK-01B: historical JackRouter / JACK2 / alternative fork study

**Pinned inspected upstream refs:**

- Legacy `jackaudio/jack-router` main `97ce963f7684c33c15132ed0eb7a899654b30a3a`; historical-only, unmaintained per [README](https://github.com/jackaudio/jack-router/blob/main/README.md).
- `jackaudio/jack2` develop `17959465a722225a36a8b612aed26764036f258e` (official server/client API reference).
- `thestk/rtaudio` master `06f97b633c06ea747d6478f0e87b6e1178104511`; `mozilla/cubeb-coreaudio-rs` trailblazer `076ecf68dbf20087d2fa8e9210a1965e341f66d0`.

**Source findings:**

- [Legacy `JackRouter.cpp`](https://github.com/jackaudio/jack-router/blob/main/macOS/jackrouter/JackRouter.cpp) implements an **`AudioHardwarePlugIn` factory** for actual macOS HAL (`CoreFoundation`, `IOKit`); `TJackClient.cpp` uses `jack_client_open`, `jack_set_process_callback`, JACK ports and `jack_port_get_buffer` to invoke Mac `AudioDeviceIOProc` callbacks. JACK drives the audio cycle.
- [Second historical implementation](https://github.com/jackaudio/jack-router/blob/main/macOS/jackrouter2/Source/JackRouterDevice.cpp) uses CoreAudio HAL object/device/stream machinery and a JACK process callback; it uses a try-lock that can drop cycles when contended. It is a **behavioral study reference**, not RT-correct code ready for a Linux Mach-O runtime.
- [Design note](https://github.com/jackaudio/jack-router/blob/main/macOS/docs/JackRouter-AudioServerPlugin.md) explicitly says old `AudioHardwarePlugIn` no longer works since macOS Catalina and proposes `AudioServerPlugin`: `coreaudiod` subprocess, graph activation, shared memory, semaphores, sockets or RPC, and `jack_cycle_wait` / `jack_cycle_signal`. It is a **design proposal**, not an implemented portable d4rling HAL.
- [JACK official non-callback API](https://jackaudio.org/api/group__NonCallbackAPI.html) documents `jack_set_process_thread` with `jack_cycle_wait` / `jack_cycle_signal` and strict real-time limits. A one-client simple `jack_set_process_callback` is a lower-risk first proof than reproducing a synchronous multi-client HAL activation graph.
- [madhatter68/JackRouter](https://github.com/madhatter68/JackRouter): `JackBridge`, MIT license, experimental user-space driver + daemon; README specifies 44.1/48 kHz and independent CoreAudio app callbacks outside the JACK graph.
- [TreeFallSound/JackRouter](https://github.com/TreeFallSound/JackRouter): MIT-licensed downstream `JackBridge`, **Apple Silicon arm64/macOS**, `AudioServerPlugIn` + Linux-style JACK client daemon and POSIX shared-memory ring (clock-domain guidance in `docs/architecture.md`). Valuable **separation and clock/latency** reference, but no x86_64/i386 or Darling compatibility shown; do not install or execute their macOS scripts.
- [RtAudio](https://github.com/thestk/rtaudio) includes JACK + ALSA + PulseAudio backends (MIT license) but is a generic cross-platform API rather than an Apple HAL replacement. [cubeb-coreaudio-rs](https://github.com/mozilla/cubeb-coreaudio-rs) is macOS-specific with an ISC-style permission grant; useful for state/format tests but not a ready Linux JACK backend.

**Licensing check is per file, not just repo badge:** legacy `JackRouter.cpp` declares GPL **v2 or later**; `TJackClient.cpp` declares GNU Library GPL **v2 or later**; `jackrouter2` files carry original Apple sample-specific notices and conditions; `JackLibAPI.cpp` in JACK2 declares LGPL **v2.1 or later** even though JACK2 root `COPYING` reproduces GPL v2. Darling CoreAudio files declare GPL **v3 or later**. No third-party code has been imported. Review each prospective copied component individually before licensing decision; prefer fresh implementation using publicly documented APIs.

## 22. JACK-01C: source-grounded d4rling HAL gap matrix

| Contract | Current source on `work/core-audio` | Verified implementation state | JACK integration implication |
| --- | --- | --- | --- |
| Mach-O CoreAudio API exports | `src/CoreAudio/CoreAudio/AudioHardware.cpp` | `AudioObjectGetPropertyData*`, `AudioDeviceCreateIOProcID`, `AudioDeviceStart/Stop` exported; CA-11D/11G prove link/defined exports, **not API runtime** | Reuse one public HAL surface; do not ship a second Mac plug-in API |
| AudioObject registry and device enumeration | `AudioHardware.cpp::initObjects` | PulseAudio system, output and input instantiated; **duplicate map key** `kAudioObjectSystemObject+1` for extra event output intended at `+3`, so extra device insert is discarded | Add JACK device/backend only through existing registry after explicit selection; fix ID contract separately with tests |
| Device properties and PCM format | `AudioHardwareImpl.cpp` | **Demonstrated source bug**: `mBytesPerFrame` multiplies by `mSampleRate`; expected bytes per frame depend on channels and bits, not sample frequency | Correct with targeted characterization before linking JACK; validate interleaved/non-interleaved stereo and exact bytes |
| IOProc lifecycle | `AudioHardwareImpl.{cpp,h}` | `m_proc`/`m_streams`, create/start/stop; stop accesses `m_streams` without the start-side lock; lifecycle/reentrancy not qualified | Require callback-safe ownership, bounded stop and no RT lock inversion |
| Backend abstraction | `AudioHardwareStream.h`, `pulse/AudioHardwareStreamPA.h` | Polymorphic `AudioHardwareStream`; PulseAudio-specific subclass contains `AudioDeviceIOProc`, stream and lock | Natural insertion for independent `AudioHardwareImplJACK`/`AudioHardwareStreamJACK` or transport interface, not wholesale HAL replacement |
| Output callback & copying | `pulse/AudioHardwareStreamPAOutput.cpp` | Uses `pa_stream_begin_write`, calls guest IOProc then `pa_stream_write`; error/size/callback audit not completed | JACK needs planar `float` port buffers, bounded frames, no malloc or mutex in callback; do not transplant PA buffer assumptions |
| Input and duplex | `pulse/AudioHardwareImplPAInput.cpp`, `AudioToolbox/AudioQueue.cpp` | PulseAudio input class exists; `AudioQueueNewInput` explicitly returns `unimpErr` | Recording and duplex integration/AudioToolbox gaps remain independent acceptance gates |
| Time and latency | `HostTime.mm`, `AudioHardwareImpl.cpp` | `AudioGetCurrentHostTime()` exported but **stub returns zero**; time getters return zero/placeholder | JACK frame_time, monotonic host ticks, buffer scheduling, latency/safety offset must be reconciled before a valid DAW claim |
| Build/ELF wrapper | `cmake/wrap_elf.cmake`, `src/libelfloader/wrapgen/wrapgen.cpp` | 64-bit C function wrapper exists (`_elfcalls`/ELF dlopen+dlsym); header says **TODO: wrapgen32**, not present as a qualified i386 JACK path | 64-bit wrapper experiment possible; do not claim i386 JACK or callback reentry support |
| Loader and 32-bit launch | `src/startup/mldr/mldr.c`, `elfcalls/elfcalls.c` | FAT/thin dispatch and 32-bit `reexec32` path in source; native ELF calls supplied to guest; **CA-12 guest runtime FAIL** | Must qualify host JACK thread invoking guest Mach-O callback, TLS/register/stack lifetime, and i386 mode separately |
| CoreMIDI / ALSA | Existing `work/core-audio` and parallel CoreMIDI work | Independent MIDI path; no JACK PCM integration proven | Preserve ALSA sequencer routing; do not couple JACK PCM success with MIDI tests |

## 23. JACK-01D: candidate architecture tradeoffs and gate decision

| Option | Advantages | Blocking costs | Status |
| --- | --- | --- | --- |
| A. Rehost historic `AudioHardwarePlugIn`/`AudioServerPlugIn` | Historic parity and HAL device behavior reference | Duplicates d4rling HAL, depends on macOS `coreaudiod`/IOKit/plugin environment, licensing and obsolete APIs | **NO-GO for direct port** |
| B. Native JACK backend under existing d4rling HAL | One CoreAudio API, reuse device/stream lifecycle, easiest to compare with existing PulseAudio | In-process Mach-O → ELF JACK symbols and Linux JACK RT callback → Mach-O IOProc; `wrapgen32` absent for i386; runtime CA-12 FAIL | **Preferred design, GO UNDER CONDITIONS** |
| C. RtAudio/cubeb mediation | Generic API / existing audio state-management patterns | Extra indirection; still requires HAL contracts and cross-ABI callbacks; cubeb is macOS-specific | **Reference only** |
| B2. Native Linux ELF JACK **helper process** under the same d4rling HAL | One HAL; 64-bit ELF daemon can serve i386 clients via versioned shared-memory + control IPC, avoiding in-process 32-bit libjack | Explicit ring-buffer latency, xrun, clock drift, crash/reconnect, serialization, security, IPC lifecycle required | **Fallback/possible primary for i386, research gate** |

**Architecture choice:** keep a single Mach-O CoreAudio API and a backend-neutral PCM stream contract. Retain the working PulseAudio backend. For the first safe JACK feasibility gate, test a **Linux-side JACK client** separately, then decide whether a direct 64-bit wrapper can register a callback safely. If not, use a host ELF helper and shared memory without trying to load 64-bit libjack into a 32-bit guest. No automatic network fetch or runtime installation.

**Target invariants (not yet implemented):** JACK graph controls `nframes`/sample rate; default playback must emit silence on underrun or stopped stream; no allocation, logging, I/O, blocking mutex, dynamic library loading, teardown or guest RPC inside the JACK process callback; preallocate all buffers; explicit state transitions; no callbacks after stop/free; planar/interleaved mapping specified; independent input/output streams; counters for xruns, overrun, underrun, time drift; all sample time and host time valid and monotonic; no implicit promised zero-latency; keep PulseAudio as fallback.

**Mach-O / ELF mechanism evidence:** `wrapgen.cpp` emits `extern struct elf_calls* _elfcalls` and ELF symbol resolvers; `elfcalls.c` provides host `dlopen_fatal` and `dlsym_fatal` plus host-thread APIs. This provides a plausible *calling direction Mach-O → ELF*, but reverse reentry on arbitrary JACK RT threads and bridge lifecycle are **not qualified**. A 32-bit application cannot call a 64-bit in-process JACK shared object; requiring a 32-bit wrapper/runtime or out-of-process transport is not optional.

## 24. JACK-01E / JACK-01F: prototype criteria and convergence

**JACK-01E actual PCM prototype: SKIP (not safe to assert a real JACK buffer handoff).** With CA-12 failing and no local terminal exposed to this GitHub-only analysis, do not create an untested production HAL patch or claim JACK runtime PASS. Prepare bounded gates:

1. On the 5700X *read-only only*, inspect available `libjack.so.0`, `jackd`, `pw-jack`, `pkg-config`, architecture (`file`/`readelf`), and active user audio sockets. No downloads/install/start/stop daemon.
2. Mock lifecycle and buffer conversions **outside** the existing build trees: 0, 1, 64, 128, 1024 frames; mono/stereo, 44.1/48/96 kHz, planar float32/interleaved; callback stop/restart; zero-fill underrun; bounded ring; sample-time monotonicity. Tests must be genuinely run before PASS.
3. Once CA-12 guest runtime is independently healthy, qualify a minimal Mach-O guest to host libjack registration in an isolated prefix; verify Linux → guest callback reentry, thread-specific Darling setup and teardown with no audio hardware dependence. For i386, verify the separate bridge path or stop.
4. Only then route a known synthetic buffer through a JACK dummy server/port and read it back, quantify samples, xrun and latency; preserve PulseAudio fallback. No real user audio or Logic tests before loader/ABI gate.
5. Phase later: actual JACK2 or PipeWire-JACK routing and ALSA, CoreAudio AudioUnit/AudioToolbox, MIDI synchronization and Logic Studio 8 guest. Each remains **SKIP** now.

**JACK-01F coordination:** This source comparison and stage plan are published only in the shared document on PR #5, with no source import. Ownership: Ninja retains i386, CA-12 and current builds; JACK branch may prepare isolated tests without modifying Ninja-owned source files, and must requalify/coordinate before any future merge.

**Overall verdict: GO SOUS RÉSERVES for JACK architecture research and isolated offline tests; NO-GO for an installed JACK backend, claimed PCM playback, i386 JACK runtime or Logic Studio 8.**

## 25. JACK-01E0 — 5700X host preflight; no JACK runtime available (2026-10-26)

**Source:** user-pasted output from Bash on the 5700X under Debian 13 WSL2, running a read-only preflight in `~/d4rling-carbon-qualif`. This GitHub-only update did not run host commands.

| Gate | User-reported observation |
| --- | --- |
| JACK commands | `jackd` ABSENT; `jack_lsp` ABSENT |
| PipeWire compatibility and server commands | `pw-jack` ABSENT; `pipewire` ABSENT |
| Core inspection utilities | `pkg-config`, `ldconfig`, `readelf` PRESENT |
| Dynamic linker cache | `libjack.so` / `libjack.so.0` NOT LISTED |
| Build metadata | `pkg-config --modversion jack` returned absent |
| Process sample | No process named `jackd`, `pipewire`, `wireplumber` found in the `ps` snapshot |
| i386 loader | `~/d4rling-build-i386/src/startup/mldr/mldr32` exists; Linux ELF **32-bit i386 PIE**; interpreter `/lib/ld-linux.so.2` named by `file` |
| Side effects | `NO_BUILD_NO_DOWNLOAD_NO_RUNTIME_CHANGE=PASS`; no daemon started or installed |

`JACK01E0_STATUS=PREFLIGHT_COMPLETE` is a **test execution PASS**, but **JACK availability is BLOCKED** for real client/PCM tests. `ldconfig -p` not listing libjack is not a machine-wide filesystem search, and absence of current processes does not rule out a later/externally provided audio server. Do not claim a runtime JACK test or automatic install.

**i386 distinction:** `mldr32` is an actual constructed ELF 32-bit host executable, distinct from previously confirmed Mach-O FAT `libsystem_kernel.dylib` x86_64+i386. The loader exists as a file but **has not been executed successfully**; CA-12 remains FAIL on guest process RPC `-111`, timeout exit 137. A build artifact is not a working guest loader.

### Next offline gate JACK-01E1

Without `libjack`, prefer a **pure standard-library PCM ring/callback contract model** on the 5700X (no repository or system modifications). Test fixed/preconfigured capacity, stereo planar float32, zero frames, exact input/output sequences, wraparound, overflow atomicity, underrun zero-fill, start/stop and restart, per-cycle `nframes` and frame clock for 44.1/48/96 kHz. Record exact test pass/fail counts and prevent presenting these mock tests as real-time memory-safety or actual JACK execution. **No downloads** and do not touch concurrent Ninja builds.

After that, read-only i386 `file`, `readelf -l` and `ldd` against `mldr32` can establish runtime *dependencies and ELF interpreter presence* but not guest startup. Do not run loader or restart Darling while CA-12 remains blocked. Actual JACK library install or host daemon startup requires separate user authorization.

## 26. JACK-01E1 — Offline PCM ring-buffer model: 12/12 PASS (2026-10-26)

**Evidence provenance:** user's actual 5700X Debian 13 WSL2 terminal output, running a **Python standard-library-only inline script**, not JACK. Executed inside `~/d4rling-carbon-qualif` without changing files, installing packages, compiling, or starting the Darling runtime.

| Qualification | User-reported observed result |
| --- | --- |
| Python unittest methods | **12 executed / 12 PASS / 0 failures**; `Ran 12 tests in 0.001s`, `OK` |
| Final result | `JACK01E1_STATUS=PASS_MODEL_ONLY` |
| Real JACK or PipeWire | `REAL_JACK_TEST=NOT_EXECUTED` |
| File side effects | `FILES_MODIFIED=NO` |

**Qualified logical behavior in the Python model only:** frame cycle lengths 0/1/64/128/1024; mono and stereo independent planar channels; 44.1/48/96 kHz virtual frame clock; ring wraparound; atomic reject on overflow; silence zero-fill on underrun with counter; stop/restart and no write while stopped; monotone counting of processed frames; invalid/negative input rejection. `test_frame_sizes` and `test_sample_rates` each perform multiple `subTest`s inside one of the 12 methods.

**Persistent regression artifact published separately on this convergence branch:** [`tests/regressions/jack-transport/test_pcm_contract_model.py`](../../tests/regressions/jack-transport/test_pcm_contract_model.py), Git blob `b66c0fa435bde544a0221162ac28a6b58e676ab9`, 12 `test_` methods. The published file reproduces the user's tested model and adds a module guard/header. The exact committed file **has not yet been executed on the 5700X**; its on-host 12/12 must not be stated as tested from the GitHub branch until run. No GitHub CI was launched (`[skip ci]`).

**Explicit limits and risks:** this Python model allocates lists during `cycle()`, holds no thread synchronization, does not model cache coherence / actual SPSC atomic order, buffer ownership after stop, dynamic JACK buffer changes, cross-ABI calls, device/stream enumeration, xrun timing or real PCM playback. Thus the 12/12 PASS is an *executable specification*, not a RT-safe transport or JACK adapter. Never reuse Python `PCM` for real callbacks.

**Next native gate JACK-01E2:** strictly isolated C++17 native SPSC ring-buffer prototype and test runner in a disposable directory, with preallocated storage, bounded planar floats, clearly single producer/single consumer, explicit errors and counters, no callback-path allocation/blocking/logging, and start/stop only under quiescence. Check compiler/toolchain availability first; keep Ninja/CoreAudio/i386 build trees untouched and do not install or download JACK. The first C++ prototype must be tested on the 5700X before any PASS claim; add separate concurrent/thread-sanitizer qualification later. Neither CA-12 nor Logic Studio 8 is touched.

## 27. JACK-01E2 — Isolated native C++17 SPSC PCM contract prototype (2026-10-26)

**Source:** `tests/regressions/jack-transport/pcm_spsc_native_contract.cpp`, Git blob **`ee719b7514743081c04d255f3ae66cf9f1c54fe5`** (6,923 bytes). The Git blob was compared to the exact locally tested source and matched. Published to **convergence branch only**, not `work/core-audio`, not an audio engine implementation.

### Execution provenance and evidence

- In the assistant's **isolated Linux container** (not the 5700X): C++17 compile with `c++ -std=c++17 -O2 -pthread -Wall -Wextra -Werror`; binary ran under `timeout 20s`.
- **11/11 native self-test checks PASS**: frame sizes 0/1/64/128/1024; mono; ring wraparound; atomic overflow-rejection behavior (logical); zero-filled underrun; stop+restart with buffer flush; virtual frame clock and rates; stopped write rejected; invalid repeated stop; invalid config; **50,000 frames in sequence in a 2-thread SPSC producer/consumer stress scenario**.
- Assistant container also compiled and ran the **exact same source** with `-fsanitize=address,undefined -fno-omit-frame-pointer`; output remained **11/11 PASS**, no sanitizer diagnostics reported. **Not** a ThreadSanitizer run, not a real-time deadline benchmark and not a formal concurrency proof.
- `JACK01E2_STATUS=PASS_NATIVE_MODEL_ONLY`; `REAL_JACK_TEST=NOT_EXECUTED`. **The published C++ probe has not yet been run on the user's 5700X**; do not report a 5700X PASS.
- The previously user-executed JACK-01E1 Python suite remains **12/12 PASS on 5700X**, distinct from the C++ prototype.

### Native prototype contract and limits

`PCMQueue` preallocates a planar interleaved-in-memory buffer at construction, uses release/acquire atomic head/tail counters for **one producer and one consumer**, stores monotone frame counts and xrun counters and zero-fills shortages. `write()`/`read()` have no explicit allocation or blocking operations and are declared `noexcept`. The test's use of `std::thread::yield()` is limited to the non-realtime stress-test harness; it is **not** part of the callback API.

**Important:** stop/start, destruction and constructor are valid only when producer and consumer are quiescent; this has not been extended to concurrent shutdown. Caller buffers must be valid and sized for `nframes`; these are explicit preconditions and not fully checked. A native container PASS does not establish scheduling, priority inversion freedom, callback-domain ABI safety, `std::atomic` implementation on all targets, dynamic buffer reconfiguration, latency/xrun performance, JACK protocol compatibility, or i386 support. Keep this code in `tests/regressions` as a **nonproduction experiment** until separate review and qualification.

### Next on-host JACK-01E2H gate

Without Git checkout or package installation: disclose an **exact 6,923-byte read** from the pinned GitHub source, verify Git blob SHA `ee719b7514743081c04d255f3ae66cf9f1c54fe5`, then compile using existing C++17 host compiler in a new isolated folder outside Ninja build directories and run 11 native self-tests. If the user does not explicitly choose to execute/download, do not fetch. On-host sanitizer checks are optional and should run only if compiler runtimes are already installed. CA-12 RPC remains FAIL and is not exercised. Real JACK unavailable per JACK-01E0.

## 28. JACK-01E2H — Verified on 5700X: native PCM SPSC 11/11 PASS (2026-10-26)

**Evidence:** exact stdout supplied by user from Debian 13 WSL2 on machine `5700X` (the assistant did not directly execute these commands on that host). The earlier §27 container-only evidence is now supplemented with a host run of the pinned source.

**Canonical single qualification directory:** `/home/Deniel/d4rling-audio/qualif`. No future scattered `~/d4rling-jack-*`, no new independent build trees and no relocation of the existing i386/Carbon/audio build trees. Keep these files in this **single directory**: `pcm_spsc_native_contract.cpp`, `pcm_spsc_native_contract`, `build.log`, `test.log`.

### Actual JACK-01E2H host transcript

- Source retrieval: **explicit one-time GitHub fetch**, declared 6,923 bytes. Terminal printed `SOURCE_ABSENTE: recuperation GitHub 6923 octets`; future runs should **reuse** the local source instead of downloading it again.
- `git hash-object` matched the pinned Git blob `ee719b7514743081c04d255f3ae66cf9f1c54fe5`: `HASH_PASS`.
- C++17 compiler invocation completed: `BUILD_PASS`.
- All **11** native checks printed `PASS`: frame sizes, mono, wraparound, overflow atomicity, underrun zero fill, stop and restart, rates and monotonic frame clock, stopped write refused, invalid double stop, invalid configuration, SPSC 50,000 frames in order.
- Native summary: `JACK01E2_PASS=11/11`, `JACK01E2_STATUS=PASS_NATIVE_MODEL_ONLY`, `JACK01E2H_STATUS=PASS_NATIVE_MODEL_ONLY`.
- Explicit `REAL_JACK_TEST=NOT_EXECUTED`. No evidence of actual PipeWire/JACK runtime, real audio output, valid i386 callback ABI, deterministic real-time deadlines, or success of Darling CA-12. This host run was **not** an ASan/UBSan/TSan run.

**Convergence decision:** `GO` for isolated C++17 prototype development, `NO-GO` for calling it a functional JACK/CoreAudio backend. Retain the shipped PulseAudio prototype and all Ninja-built artifacts. Do not install JACK or start/stop any audio daemon without separate authorization.

**Next verification gate (JACK-01E3):** use **only** `/home/Deniel/d4rling-audio/qualif` for sanitizer test outputs. Check the already-downloaded source hash again; conditionally compile with an existing compiler and `-fsanitize=address,undefined` when supported (no packages or downloads); run under timeout; record exact stderr and 11/11 counts. Address/Undefined sanitizers are a memory diagnostic, **not** a proof of real-time behavior or race freedom. ThreadSanitizer, if ever used, requires a separate isolated and supported runtime qualification. In parallel, source-side RT review of preallocation, `std::atomic<uint64_t>` lock-freedom on **i386**, bounded `nframes`, memory ordering, caller-buffer lifetime and stop quiescence; do not modify the active HAL or CA-12 runtime for this.

## 29. JACK-01E3 — ASan/UBSan 11/11 PASS on the 5700X (2026-10-26)

**Provenance:** user-pasted terminal stdout from `Deniel@5700X` (Debian 13 WSL2), run with `cd "$HOME/d4rling-audio/qualif"`. These commands were run on the user's machine; this GitHub update did not itself execute that host command.

| Gate | Evidence in terminal log | Status |
| --- | --- | --- |
| Canonical directory | `/home/Deniel/d4rling-audio/qualif` | PASS |
| Source integrity | `SOURCE_HASH=PASS`, pinned C++ source blob `ee719b7514743081c04d255f3ae66cf9f1c54fe5` (as configured in script) | PASS |
| Compiler | `/usr/bin/clang++-19` | PRESENT |
| Sanitizer build | `ASAN_BUILD=PASS`, C++17 `-fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all` | PASS |
| Native self-tests | 11 named PASS, including 50,000 ordered SPSC frames | **11/11 PASS** |
| Run exit | `TEST_EXIT=0` | PASS |
| ASan / UBSan diagnostics | No diagnostics in printed `asan_test.log` and `JACK01E3_STATUS=PASS_ASAN_UBSAN` | PASS on observed tests |
| Real JACK | `REAL_JACK_TEST=NOT_EXECUTED` | SKIP |

**Artifacts stay under this one directory only:** `pcm_spsc_native_contract.cpp`, the existing native probe, `pcm_spsc_native_contract_asan`, `asan_build.log` and `asan_test.log`. No extra `d4rling-*` folders were introduced; no package downloads, JACK server execution, changes to the Ninja build directories or host installation were reported.

**Important limits:** ASan checks address issues and UBSan checks configured undefined behavior in exercised paths; neither establishes thread race freedom, real-time bounded scheduling, JACK callback compatibility, actual audio output, i386 runtime or CA-12 RPC recovery. The SPSC test has one producer, one consumer, with quiescent start/stop; it is not a concurrent shutdown test.

**Next lot JACK-01E4:** optional `-fsanitize=thread` concurrency diagnosis, with the **same already downloaded source** and output files only under `/home/Deniel/d4rling-audio/qualif`. First qualify whether the existing toolchain's TSan runtime works on WSL2, then run the 50,000-frame SPSC test. If toolchain compilation or sanitizer runtime is unsupported, report `SKIP_TOOLCHAIN`/`INCONCLUSIVE`, not a code FAIL. TSan must not be combined with ASan in the same executable; no installation, downloads, no `darling exec`, no JACK daemon start, no alteration of the existing PulseAudio/i386/Carbon sources.

**Verdict:** **PASS for JACK-01E3 instrumented isolated native model**. **NO-GO for functional JACK HAL or any Logic Studio 8 claim**.

## 30. JACK-01E4 — ThreadSanitizer PASS on 5700X (2026-10-26)

**Evidence:** user-pasted terminal output from the existing Debian 13 WSL2 host `5700X`. This result was not executed remotely by the GitHub assistant.

- Working directory **unchanged**: `/home/Deniel/d4rling-audio/qualif`. Reused existing `pcm_spsc_native_contract.cpp`, pinned Git blob SHA `ee719b7514743081c04d255f3ae66cf9f1c54fe5`; `SOURCE_HASH=PASS`.
- C++17 compilation with the **existing** `clang++-19` and `-fsanitize=thread -O1 -g -pthread -fno-omit-frame-pointer -Wall -Wextra -Werror` succeeded (`TSAN_BUILD=PASS`).
- **11/11 PASS** including the **50,000-frame one-producer/one-consumer stress**. Runtime exited with `TEST_EXIT=0`; the user log did not contain any ThreadSanitizer warning or fatal error.
- Exact reported verdict: `JACK01E4_STATUS=PASS_TSAN`; `REAL_JACK_TEST=NOT_EXECUTED`. Log path: `/home/Deniel/d4rling-audio/qualif/tsan_test.log`.
- Prior on-host gates remain independent: JACK-01E1 Python 12/12, JACK-01E2H C++ native 11/11, JACK-01E3 ASan+UBSan 11/11.

**Verdict:** **PASS for ThreadSanitizer-instrumented, exercised SPSC model tests on the 5700X**. This is not proof of race freedom in arbitrary interleavings; **stop and restart were tested only with producer and consumer quiescent**, not with concurrent shutdown. The loop's `yield()` occurs only in the test driver, not in a JACK callback. No real-time deadlines, Mach-O/ELF callback crossing, JACK graph or Logic Studio 8 were exercised; CA-12 RPC `-111` remains independently blocked.

### Next gate JACK-01E5: i386 feasibility without changing directory structure

After three successful native sanitizer gates, **do not rerun them unnecessarily**. Use only the existing `/home/Deniel/d4rling-audio/qualif` to attempt a separate *32-bit Linux* build of the already pinned C++17 test (`clang++-19 -m32`) using already installed headers/libraries. If multilib development packages or the dynamic loader are missing, report **SKIP_TOOLCHAIN** or **INCONCLUSIVE_RUNTIME**, not an audio-code FAIL, and **do not install packages automatically**. If successful, verify the executable is i386 ELF, run the original 11 tests, and examine `std::atomic<uint64_t>` lock-free guarantees on that platform before placing any such counters inside a prospective guest callback. A 32-bit Linux ELF test is not a substitute for a Mach-O i386/dyld/`mldr32` smoke test; direct Mach-O-to-ELF JACK callbacks and CA-12 remain unqualified.

**Folders and branch coordination:** no temporary `~/d4rling-*` directories, no changes to the existing Ninja build trees, Carbon/UI, audio/PulseAudio or i386 source. PR #5 stays draft, no CI and no merge. No downloads or new JACK daemon.

## 31. JACK-01E5 — i386 C++ toolchain preflight SKIP (2026-10-26)

**Evidence:** output supplied from `Deniel@5700X` Debian 13 WSL2, command executed within the single canonical directory `/home/Deniel/d4rling-audio/qualif`. The GitHub agent did not execute this host command.

- `SOURCE_HASH=PASS`: C++ SPSC source unmodified, pinned Git blob `ee719b7514743081c04d255f3ae66cf9f1c54fe5`.
- `clang++-19 -m32 -std=c++17` failed during **the preliminary atomic-header test**, before attempting to compile or run the native i386 PCM prototype.
- Exact diagnostic: `fatal error: 'bits/c++config.h' file not found`, included from `/usr/lib/gcc/x86_64-linux-gnu/14/../../../../include/c++/14/bits/version.h`, via `<atomic>`. This indicates that the compiler's selected **32-bit libstdc++ target headers/configuration are unavailable through that include search path**. This does not prove 32-bit code generation, ELF loader, C compiler, or Darling i386 are nonfunctional.
- Printed verdict: **`JACK01E5_STATUS=SKIP_I386_TOOLCHAIN`**. No i386 atomic `is_lock_free()` outputs, no i386 PCM binary, no 11/11 i386 model tests, no JACK runtime. Do **not** count this as an audio source regression.
- Distinguish earlier **PASS** of built `mldr32` ELF i386 and Mach-O FAT `libsystem_kernel.dylib` i386 slice (I386-13) from this C++ `<atomic>` dependency gap. Those are independent qualifications.

### Next safe gate JACK-01E5B — targeted toolchain diagnosis

1. Read-only inspect installed `clang-19`, C/C++ compilers, target-specific `bits/c++config.h`, `libstdc++` development packages (e.g. 32-bit/multilib) and relevant headers; **do not substitute x86_64 `bits/c++config.h` into the i386 build**, as that could mask ABI incompatibility.
2. If helpful, compile a single freestanding **C11, headerless** ELF i386 atomic *object* using existing `clang-19` (`-m32 -ffreestanding -nostdinc -c`) in `/home/Deniel/d4rling-audio/qualif`. Record `readelf -h`, `llvm-nm-19 -u`, and generated code/lock-free declaration. Such an object-only test is **not** a linked or executed i386 atomic test and must not be represented as one.
3. Only if a usable 32-bit C++ stdlib and loader are already present, repeat the previously blocked i386 C++ tests. Otherwise report and retain SKIP; do not download or install dependencies without separate user authorization.
4. Continue independent architecture feasibility analysis for an x86_64 ELF JACK-helper IPC bridge to i386 Mach-O applications. Keep current Ninja builds, CA-12 runtime and CoreAudio/PulseAudio code untouched; no new folders outside the canonical `qualif` directory.

**Verdict:** PASS for JACK-01E5 preflight/error classification, **SKIP** for attempted i386 PCM run. Previously verified native x86_64 JACK-01E2H/01E3/01E4 PASS results remain valid; **real JACK, Mach-O i386 guest and Logic Studio 8 remain unqualified**.

## 32. JACK-01E5B — Freestanding i386 C11 64-bit atomic codegen (2026-10-26)

**Source:** terminal stdout pasted by the user from 5700X / Debian 13 WSL2, existing qualification directory `/home/Deniel/d4rling-audio/qualif/`. No compile or execution on the user host was initiated from the GitHub connector.

| Evidence | Observation | Qualified result |
| --- | --- | --- |
| Host toolchain | `clang-19`, `clang++-19`, `gcc`, `g++`, `readelf`, `llvm-nm-19`, `llvm-objdump-19` all present | Tool inventory PASS |
| i386 C++ stdlib header | `/usr/include/i386-linux-gnu/c++/14/bits/c++config.h` ABSENT; x86_64 counterpart PRESENT; `/usr/include/c++/v1/atomic` ABSENT | C++ i386 toolchain gap remains |
| `g++-multilib` | `unknown ok not-installed` | No automatic install |
| Freestanding C object | `clang-19 -m32 -std=c11 -O2 -ffreestanding -nostdinc -fno-stack-protector -x c -c` | `CODEGEN_PASS`, ELF32 Intel 80386 relocatable |
| Lock-free builtin | `atomic64_lockfree` contains `movl $1,%eax; ret` | **Compile-time declaration true only**; not a runtime or full-operation guarantee |
| RMW helper | `llvm-nm-19 -u` shows `__atomic_compare_exchange` and `_GLOBAL_OFFSET_TABLE_`; disassembly contains an external `calll` during `atomic64_increment` | 64-bit fetch-add lowering in this compiled configuration **depends on an external libatomic-style compare-exchange helper**; definitely not fully inlined code |
| Tests executed | `JACK01E5B_STATUS=OBJECT_I386_GENERATED`, `I386_EXECUTED=NO`, `CPP_I386_EXECUTED=NO` | No i386 native PCM, runtime or audio PASS |

**Key interpretation:** Do not convert `__atomic_always_lock_free(8,0)==1` into an assertion that the compiled read-modify-write path contains no library call. The object is unlinked, the existence/behavior of the helper on that host was not checked, and there was no executed i386 atomic code. `_GLOBAL_OFFSET_TABLE_` is expected in position-independent i386 object code, not automatically a missing audio runtime dependency. The helper may itself be lock-free or may take locks; **not determined**. It is unsafe to assume arbitrary helper calls are acceptable on a real-time audio callback.

**External reference:** LLVM's X86 feature table distinguishes `cx8`/`CMPXCHG8B` support for i686 from strict older i386 targets; compiler builtins or a compile-time constant alone cannot substitute for inspecting the actual generated code. The next gate compares explicit target flags rather than changing compiler packages.

### Next gate JACK-01E5C (same canonical directory, no downloads)

Read-only source piped to `clang-19` with `-m32 -march=i686 -std=c11 -ffreestanding -nostdinc -O2` to generate a separate object *within* `~/d4rling-audio/qualif`. Use `file`, `readelf`, `llvm-nm-19 -u`, `llvm-objdump-19 -d` to compare whether the code still calls `__atomic_compare_exchange` versus inlining `lock cmpxchg8b`. Report `INLINE_CMPXCHG8B` or `EXTERNAL_HELPER` only from actual object; no linker or i386 execution. Do not force a CPU ISA in production without checking the guest target CPU and Darling ABI. Regardless of outcome, do not load in-process 64-bit libjack into i386 and keep `CA-12` untouched.

**Verdict:** JACK-01E5B **PASS_OBJECT_CODEGEN**, C++ i386 tests **SKIP_TOOLCHAIN**, lock-free operations **not yet qualified**; JACK real transport and Logic Studio 8 **NO-GO**.

## 33. JACK-01E5C — i686 atomic64 codegen: explicit alignment removes external helper (2026-10-26)

**Evidence:** user-reported terminal stdout from Debian 13 WSL2 / 5700X, `cd /home/Deniel/d4rling-audio/qualif`; no commands were executed on the user host by GitHub tools. No changes to the current Ninja builds, runtime CA-12, or audio backend.

| Variant | Compilation | Undefined externals (`llvm-nm-19 -u`) | Observed instructions |
| --- | --- | --- | --- |
| `inc_arg(unsigned long long* p)`, no explicit 8-byte alignment guarantee | `ARG_BUILD=PASS`, ELF32 Intel i386 | `_GLOBAL_OFFSET_TABLE_` + `__atomic_compare_exchange` | External helper remains; not an inline-only atomic proof |
| `inc_aligned()` on an `__attribute__((aligned(8))) unsigned long long slot` | `ALIGNED_BUILD=PASS`, ELF32 Intel i386 | `_GLOBAL_OFFSET_TABLE_` only | **`lock` + `cmpxchg8b (%esi)`**, retry `jne` present in disassembly |

User-printed verdict: `ALIGNED_EXTERNAL_HELPER=NO`, `INLINE_CMPXCHG8B=PASS`, `JACK01E5C_STATUS=CODEGEN_INSPECTED`, `I386_EXECUTED=NO`, `REAL_JACK=NOT_EXECUTED`.

**Interpretation:** Target flags `clang-19 -m32 -march=i686 -std=c11 -O2 -ffreestanding -nostdinc -fno-stack-protector` generated an **inlined atomic 64-bit read-modify-write** for the specifically aligned global. Source-level alignment changes the generated dependency behavior. `_GLOBAL_OFFSET_TABLE_` is the ELF position-independent addressing symbol, not an `__atomic_*` helper. The unaligned/ordinary pointer variant still **references `__atomic_compare_exchange`**; do not hide or normalize that difference.

**Boundary:** `CMPXCHG8B` exists in the emitted object but the code has **not been linked or executed as i386**. Neither a one-off aligned global nor a compiler builtin implies that arbitrary heap-allocated PCM counters or Mach-O shared-memory IPC fields have correct alignment or cross-ABI memory semantics. C++ i386 standard-library headers remain unavailable; previous JACK-01E5 `SKIP_I386_TOOLCHAIN` still applies. No real JACK library, Linux JACK daemon or Logic Studio 8 runtime test. CA-12 RPC `-111` is unchanged.

### Next gate JACK-01E5D — source-level PCM counter layout codegen only

Generate a **headerless C11 i686 ELF32 object** in the same `~/d4rling-audio/qualif` from stdin. Define a `RingCounters` struct with `_Alignas(8)` on both `uint64`-equivalent fields (use `unsigned long long` without libc headers) and `_Static_assert` checks for struct alignment and member offsets. Compile `__atomic_load_n(..., __ATOMIC_ACQUIRE)`, `__atomic_store_n(..., __ATOMIC_RELEASE)` and `__atomic_fetch_add(..., __ATOMIC_ACQ_REL)`; inspect `llvm-nm-19 -u`, `llvm-objdump-19 -dr`. Verdict if no `__atomic_*` undefined references plus inline `cmpxchg8b` for RMW: **PASS_CODEGEN_ONLY**. Any helper reference should be reported and reviewed rather than linked into a callback by default. Do not claim an i386 runtime pass. No download, package install, guest execution, new directory, full Ninja build, or audio backend changes.

**Decision:** GO for validating i686 aligned counter ABI as a *candidate*; prefer Linux x86_64 JACK helper across a well-defined shared-memory/IPC boundary to avoid loading x86_64 libjack into a 32-bit Mach-O process. Real-time and cross-process correctness are separate gates.

## 34. JACK-01E5D — PCM counter structure i686 codegen PASS (2026-10-26)

**Host evidence:** User-supplied stdout, Debian 13 WSL2 on `5700X`, command run with `cd "$HOME/d4rling-audio/qualif"` from a different starting directory. The canonical output directory remained `/home/Deniel/d4rling-audio/qualif`. No change to Ninja build directories, PulseAudio, CA-12 or Darling runtime.

| Qualification | Evidence | Status |
| --- | --- | --- |
| Freestanding C11 code generation | `clang-19 -m32 -march=i686 -std=c11 -O2 -ffreestanding -nostdinc -fno-stack-protector` | `STRUCT_LAYOUT_BUILD=PASS` |
| ELF format | `ELF 32-bit LSB relocatable`, `readelf` class `ELF32`, machine `Intel 80386` | PASS object-only |
| Layout and alignment | `_Static_assert(_Alignof(RingCounters)>=8)`, `offsetof(rd)==0`, `offsetof(wr)==8`, `sizeof(RingCounters)==24` compiled | PASS **for this C11 i686 target** |
| External symbols | `llvm-nm-19 -u` emitted nothing | **0 undefined symbols** |
| Atomic increment | Disassembly contains `lock` + `cmpxchg8b 0x8(%ebp)` in `add_wr` and loop `jne` | `INLINE_CMPXCHG8B=YES`, PASS codegen |
| Audit summary | `JACK01E5D_STATUS=PASS_CODEGEN_ONLY`, `ATOMIC_EXTERNAL_HELPER=NO` | PASS limited to generated object |
| Execution | `I386_EXECUTED=NO`, `REAL_JACK=NOT_EXECUTED` | SKIP |

**Interpretation:** A deliberately 8-byte-aligned C11 structure can lower `__atomic_load_n` (acquire), `__atomic_store_n` (release) and `__atomic_fetch_add` (acq_rel) into 32-bit ELF object code with **no external atomics helper** under the tested i686 target. The excerpt explicitly demonstrates `lock cmpxchg8b` for the read-modify-write path; the other operations are inferred only from the empty undefined-symbol list and successful compilation, not individually disassembled. This is **not** a lock-free/run-time/concurrency proof for any shared-memory placement, i386 Mach-O ABI or JACK callback. C++ i386 `<atomic>` header still unavailable from the earlier JACK-01E5 preflight.

### Next gate JACK-01E6 — shared IPC header across target ABIs (not execution)

Create no new directory. Pipe one common **headerless C11 structure definition** into `clang-19` three times, generating independent objects within `/home/Deniel/d4rling-audio/qualif`: Linux ELF32 i686, Linux ELF64 x86_64, and optional Mach-O i386 Darwin target. Use fixed-width-equivalent `unsigned short/int/long long`, explicitly `_Alignas(8)` for 64-bit counters, and compile-time assertions for an explicitly versioned 64-byte header (`magic`, `version`, `flags`, `frame_capacity`, `channels`, `read_frames`, `write_frames`, `sample_rate`, `format`, `state`, `reserved`). Verify identical offsets (16/24) and total size; inspect object architectures, undefined atomics helpers and at least the i686 `cmpxchg8b` codegen.

If Mach-O cross-target codegen is unavailable, report `SKIP_TARGET_MACHO` without overwriting the ELF qualifications. **Object-only** results do not prove runtime cross-process mapping, endian/interoperability on a different CPU, actual permission or pointer handling, signal safety, time synchronization, real JACK, Logic Studio 8 or Darling CA-12. Adopt the IPC schema only after independent review of ring payload layout, shared-memory lifetime, version negotiation, 32/64-bit process interaction and audio callback constraints.

**Decision:** GO for isolated cross-ABI **layout** qualification; NO-GO for claiming an operational 32-bit JACK backend. PR #5 stays draft on `work/coreaudio-ninja-convergence`, `[skip ci]` documentation update only.

## 35. JACK-01E6 — One SharedPCM header compiled for ELF32, ELF64 and Mach-O i386 (2026-10-26)

**Provenance:** exact terminal stdout pasted by the user from the 5700X host (Debian 13 WSL2), with the working directory switched to the sole existing `/home/Deniel/d4rling-audio/qualif`. The following are compiler/object inspection results, **not** runtime IPC results. The GitHub agent did not execute the user-host command.

| Target | Build and object | Undefined `__atomic*` helpers | Observed RMW code | Layout checks |
| --- | --- | --- | --- | --- |
| `elf32` (`i386-linux-gnu`, `-march=i686`) | `BUILD_PASS`, ELF32 Intel 80386 | `ATOMIC_HELPER=NO_elf32` | `lock cmpxchg8b` at `write_frames` offset 0x18 | `LAYOUT_PASS=elf32` |
| `elf64` (`x86_64-linux-gnu`, `-march=x86-64`) | `BUILD_PASS`, ELF64 x86-64 | `ATOMIC_HELPER=NO_elf64` | `lock xaddq` at offset 0x18 | `LAYOUT_PASS=elf64` |
| `macho32` (`i386-apple-darwin`, `-march=i686`) | `BUILD_PASS`, Mach-O i386 object | `ATOMIC_HELPER=NO_macho32` | `lock cmpxchg8b` at offset 0x18 | `LAYOUT_PASS=macho32` |

**Compile-time contract assertions passed for all three objects**: `sizeof(SharedPCM)==64`, `_Alignof(SharedPCM)==8`, `read_frames` at byte 16, `write_frames` at byte 24, `state` at byte 40, and expected pointer widths for each compilation target. Header schema also contains `magic`, `version`, `flags`, `capacity_frames`, `channels`, `sample_rate`, `format`, and `reserved[5]`. `llvm-nm -u` produced no undefined symbols in this test and the disassembly showed architecture-specific inline atomic RMW instructions.

User printed `JACK01E6_STATUS=CODEGEN_AUDITED`, `SHARED_MEMORY_RUNTIME=NOT_EXECUTED`, `DARLING_RUNTIME=NOT_EXECUTED`, `REAL_JACK=NOT_EXECUTED`. **Verdict: PASS for cross-target object compilation and static header layout, NOT a shared-memory runtime pass.** Do not claim `mldr32` can load this Mach-O, actual i386 Mach-O linkage, Linux-to-Darwin process interaction, JACK graph operation, or Logic Studio 8.

### Next meaningful gate: JACK-01E7, actual Linux-to-Linux PCM IPC

Do not continue repeating atomic code-generation microtests. Create and run one bounded **two-process** producer/consumer synthetic PCM ring test on native Linux x86_64 with a `MAP_SHARED` mapping, the already-qualified 64-byte `SharedPCM` header, bounded capacity, 50,000 ordered stereo float32 frames, wraparound, under/overrun counters where feasible, guarded startup/shutdown, and a real process exit status. First verify with the native host C compiler; optionally sanitize subsequent runs without modifying the HAL. **Keep every test/source/log/binary inside `/home/Deniel/d4rling-audio/qualif`**, reusing the current directory rather than creating `~/d4rling-*` directories. No additional downloads, JACK packages, JACK server, new Ninja builds, Darling prefixes, or CA-12 changes.

The next IPC test establishes only a **Linux x86_64 parent/child process-sharing result**, not 32/64 process ABI interoperability and not the JACK callback/RT interface. For independent helper processes, fd passing, PCM clock and lifecycle, cross-ABI tests must follow with explicit preconditions and evidence.

**Coordination:** PR #5 remains draft `work/coreaudio-ninja-convergence` → `work/core-audio`; preserve active Ninja work and the existing PulseAudio backend. `[skip ci]` documentation only.

## 36. JACK-01E7 — two-process Linux x86_64 PCM IPC prototype prepared and container-qualified (2026-10-26)

**Code:** `tests/regressions/jack-transport/test_ipc_linux64_fork.c`, committed as `e8151e5e6c9c3530f45f02bd6cf7450195489180` on convergence branch only. Git blob SHA **`a4012803720134254f98ea304588caacb3a8390c`** equals the locally compiled/tested source (5,698 bytes). **This has not been executed on the user's 5700X; do not record a host JACK-01E7 PASS.**

**Independent assistant Linux container (not user WSL2) qualification:** compiled C11 with `cc -std=c11 -O2 -Wall -Wextra -Werror -pthread`, executed under `timeout 25s`; process exited 0 and printed `IPC_HEADER_SIZE=64`, `IPC_FRAME_COUNT=50000`, `IPC_READ_FRAMES=50000`, `IPC_WRITE_FRAMES=50000`, `IPC_CHANNELS=2`, `IPC_PROCESS_COUNT=2`, `IPC_CHILD_STATUS=0`, `JACK01E7_STATUS=PASS_IPC_LINUX64_TWO_PROCESSES`, `MACHO_RUNTIME=NOT_EXECUTED`, `REAL_JACK_TEST=NOT_EXECUTED`.

**What it tests:** a single anonymous Linux `mmap(MAP_SHARED|MAP_ANONYMOUS)` created before `fork`, parent producer and child consumer communicating through the same `SharedPCM` **64-byte header** with 256-frame stereo float32 ring payload. The test performs a pre-fork empty-queue zero-fill check, bounded capacity/overflow rejection and full-buffer drain, then exchanges **50,000 ordered two-channel frames** across two Linux **x86_64 processes** and checks child status and exact counters. Acquire/release atomic fences guard SPSC read/write cursors. The busy wait uses `sched_yield` solely in a test harness, not in an RT callback. Local alarm bounds the process tests.

**Scope restrictions:** This proves only Linux x86_64 parent-child `fork` with anonymous shared mapping in an isolated container. It does **not** demonstrate independently launched helper attachment, fd passing, i386-to-x86_64 shared mapping/atomic cooperation, Mach-O process and ELF process communication, `mldr32`, RT-safe scheduling, JACK graph audio or Logic Studio 8. `CA-12` RPC `-111` remains blocked; no alteration of the live CoreAudio/PulseAudio backend, Ninja builds, audio daemon or Darling prefixes.

**Next on-host JACK-01E7H:** use the already present `/home/Deniel/d4rling-audio/qualif` directory and a user-initiated **5,698-byte** fetch of the *pinned commit* source only if absent. Verify Git blob SHA `a4012803720134254f98ea304588caacb3a8390c`, compile using installed `clang-19` (no install or download except the disclosed source), run under timeout, and record stdout/exit status. Do not overwrite a local source that differs in hash. Repeat the test under sanitizers later only as a separate gate. Next after an on-host pass: actual Linux independent process+fd passing IPC or mixed ELF32/ELF64 test; no more atomic codegen microtests.

**Decision:** cross-target JACK-01E6 CODEGEN_AUDITED **PASS** on user host, JACK-01E7 Linux IPC test **PASS in isolated assistant container**, host JACK-01E7H **PENDING**, runtime JACK/Darling/Logic **NO-GO**.

## 37. JACK-01E7H — 5700X Linux two-process PCM IPC PASS (2026-10-26)

**Evidence provenance:** stdout pasted by the user after running a read/compile/run probe on `Deniel@5700X`, Debian 13 WSL2, with `cd "$HOME/d4rling-audio/qualif"`. The GitHub agent did not execute the command on that host. User shell's starting path `/mnt/c/Users/Ordi` was incidental; `WORKDIR=/home/Deniel/d4rling-audio/qualif` is the actual location.

| Probe checkpoint | Actual user stdout |
| --- | --- |
| Source | `SOURCE_FETCH=5698_BYTES`, `SOURCE_HASH=PASS`; checked pinned Git blob `a4012803720134254f98ea304588caacb3a8390c` |
| C11 native build | `BUILD=PASS` |
| Shared header | `IPC_HEADER_SIZE=64` |
| Two-channel count | `IPC_CHANNELS=2` |
| Process topology | `IPC_PROCESS_COUNT=2` (parent producer + child consumer via `fork`) |
| Stereo frames sent/received | `IPC_FRAME_COUNT=50000`, `IPC_WRITE_FRAMES=50000`, `IPC_READ_FRAMES=50000` |
| Child | `IPC_CHILD_STATUS=0` |
| Verdict | `JACK01E7_STATUS=PASS_IPC_LINUX64_TWO_PROCESSES`, `JACK01E7H_STATUS=PASS` |
| Unperformed | `MACHO_RUNTIME=NOT_EXECUTED`, `REAL_JACK_TEST=NOT_EXECUTED` |

**Qualified result:** PASS of the isolated C11 **Linux x86_64 parent-child IPC test on the actual 5700X host**. Shared anonymous `mmap` was created before `fork`, then transferred 50,000 ordered float32 stereo frames across two processes using SPSC acquire/release counters, with tested queue overflow/empty-queue preflight. User's exit status is consistent with completion of the `set -euo pipefail` probe and final marker. The later official backend integration remains untouched.

**Limits:** This does not test a separately launched process opening an existing mapping; shared-memory fd transfer (`SCM_RIGHTS`), `memfd_create`, Linux ELF32↔ELF64 runtime sharing, guest Mach-O↔ELF64 IPC, `mldr32`, JACK audio graph, ALSA, Logic Studio 8, realtime deadlines, or the unrelated Darling CA-12 RPC error. Do not advertise those as PASS.

### Next gate JACK-01E8 — independent Linux exec + FD passing

Implement a bounded offline program where a Linux x86_64 producer creates a **memfd** backed 64-byte SharedPCM + 256-frame stereo ring, then **passes the fd over a UNIX-domain socket with `SCM_RIGHTS`** to a child after `exec` of the same test binary (separate program image), which uses `mmap(MAP_SHARED)` and consumes 50,000 ordered frames. Distinguish a socketpair passed across exec from an independently launched listener: only claim the topology actually tested. Bound waits and process lifetime, validate ancillary header/fd/capacity/version, and never create a persistent JACK daemon. Report terminal stdout plus exact test counts.

Keep **all** new local sources, compiled probes and logs under `/home/Deniel/d4rling-audio/qualif` with no new directory. No JACK installation/downloads without user action, no run of Darling/CA-12, no replacing PulseAudio, no Ninja builds, no CI. PR #5 remains draft against `work/core-audio`.

## 38. JACK-01E8 — Linux memfd + SCM_RIGHTS two-process PCM transport, isolated container PASS (2026-10-26)

**Source:** `tests/regressions/jack-transport/test_ipc_linux64_fdpass.c`, added to the draft PR #5 convergence branch at commit **`15de3ec8a90223ec304f947c26b4aadb3eb25312`**. The GitHub blob is **`4fca9b6e36a7a245a89965ebd103be7ff6be1537`** (exactly 8,902 bytes), independently verified to match the Linux isolated container's compiled/tested source. **This file was NOT yet run on the user's 5700X.**

**Assistant isolated Linux container results (not Debian13 WSL2):** `cc -std=c11 -O2 -Wall -Wextra -Werror -pthread` compile PASS. Two independently invoked Linux x86_64 program instances executed under bounded `timeout`: server creates a Linux memfd using `memfd_create`, makes a shared `mmap`, listens on a temporary filesystem UNIX socket, then sends its *memfd file descriptor* via `sendmsg`/`SCM_RIGHTS`. The separately launched client uses `recvmsg`/`MSG_CMSG_CLOEXEC`, checks descriptor size and versioned 64-byte header, maps it with `MAP_SHARED` and validates 50,000 ordered stereo float32 frames. Socket and mmap are cleaned up after normal completion; the test driver uses `sched_yield` **outside** any real-time JACK callback.

**Observed container output:** `SERVER_RC=0`, `CLIENT_RC=0`, `IPC_HEADER_SIZE=64`, `IPC_PROCESS_COUNT=2`, `IPC_SERVER_WRITE_FRAMES=50000`, `IPC_SERVER_READ_FRAMES=50000`, `IPC_SERVER_ACK=PASS`, `JACK01E8_SERVER_STATUS=PASS`, `IPC_CLIENT_RECEIVED_FD=YES`, `IPC_CLIENT_READ_FRAMES=50000`, `JACK01E8_CLIENT_STATUS=PASS`. The tested source and published GitHub blob **match**.

**Contract characteristics:** one test C11 source with `server`/`client` modes; no `fork` in test source; two invocations from the test shell create separate processes with their own mappings joined by fd passing. Fixed-capacity 256-frame, two-channel float32 ring with 64-byte versioned `SharedPCM`, 48kHz metadata, 50,000-frame synthetic test, lock-free-candidate acquire/release cursor operations on Linux x86_64. This test **does not use JACK** and does not prove deterministic audio callback timing, independent network service lifetime, mixed i386/ELF64 IPC or Mach-O guest participation. It is separate from the JACK-01E7H pre-fork shared anonymous mapping test (which did PASS on the 5700X).

**Next on-host gate JACK-01E8H:** reuse ONLY `/home/Deniel/d4rling-audio/qualif`, with an explicitly disclosed **8,902-byte GitHub source download if and only if the source is absent**, pinned to commit `15de3ec8a90223ec304f947c26b4aadb3eb25312`; verify `git hash-object` equals `4fca9b6e36a7a245a89965ebd103be7ff6be1537`. Compile with already-present Clang 19, run a bounded server in the background and bounded client in the foreground with unique temporary UNIX socket pathname **inside the existing qualif directory**, capture separate logs and exit codes, and clean only the temporary socket owned by that run. Do not overwrite mismatching sources, do not delete other users' files/sockets, do not install packages, invoke Ninja/CA-12/Darling/real JACK, or create further `~/d4rling-*` directories.

**Decision:** `JACK-01E7H=PASS` on 5700X; `JACK-01E8=PASS` in assistant's Linux isolated container only; **JACK-01E8H=NOT_EXECUTED** on the 5700X until user runs it. Real JACK/Logic Studio 8 **NO-GO**.

## 39. JACK-01E8H — 5700X Linux memfd + SCM_RIGHTS stereo PCM IPC PASS (2026-10-26)

**Evidence provenance:** user's actual Debian 13 WSL2 terminal stdout on `Deniel@5700X`, not a command executed by the GitHub agent. User started in `/mnt/c/Users/Ordi` but explicitly `cd` to the one canonical test directory `/home/Deniel/d4rling-audio/qualif`.

| Gate | Actual terminal evidence | Status |
| --- | --- | --- |
| Published source integrity | `SOURCE_FETCH=8902_BYTES`, `SOURCE_HASH=PASS`; expected Git blob `4fca9b6e36a7a245a89965ebd103be7ff6be1537` | PASS |
| Native C11 compilation | `BUILD=PASS` | PASS |
| IPC header | `IPC_HEADER_SIZE=64` | PASS |
| Process topology | `IPC_PROCESS_COUNT=2`; server and client launched as separate Linux x86_64 processes | PASS |
| `memfd` transfer | `IPC_CLIENT_RECEIVED_FD=YES` via Unix-domain socket `SCM_RIGHTS` | PASS |
| Stereo frames | `IPC_SERVER_WRITE_FRAMES=50000`, `IPC_SERVER_READ_FRAMES=50000`, `IPC_CLIENT_READ_FRAMES=50000` | PASS |
| Acknowledgement and exit status | `IPC_SERVER_ACK=PASS`, `JACK01E8_SERVER_STATUS=PASS`, `JACK01E8_CLIENT_STATUS=PASS`, `SERVER_EXIT=0`, `CLIENT_EXIT=0` | PASS |
| Final sentinel | `JACK01E8H_STATUS=PASS_LINUX_MEMFD_FDPASS` | PASS |
| Excluded runtime | `DARLING_RUNTIME=NOT_EXECUTED`, `REAL_JACK=NOT_EXECUTED` | SKIP |

**Qualified:** 50,000 stereo float32 frames passed in order between two distinct Linux x86_64 process images using a named Unix-domain socket, `sendmsg`/`recvmsg` with `SCM_RIGHTS`, and a Linux `memfd` mapped `MAP_SHARED` by both. The server remained bounded and temporary. The test binary uses user-owned socket/log paths exclusively in the existing `qualif` directory. No evidence of unrelated process interference.

**Not yet qualified:** ELF32-to-ELF64 *runtime* sharing, Mach-O i386 guest-to-native Linux process mapping, handling across Darling's loader and thread setup, audio callback deadlines/RT lock freedom, real JACK client/server, ALSA, AudioUnit/AudioToolbox, or Logic Studio 8 execution. CA-12 `mach_msg_overwrite`/dserver `-111` remains independently blocked.

### Next gate JACK-01E9 — 32-bit Linux runtime and mixed-architecture IPC

Move to an actual ELF32 Linux process exchanging data with a separate ELF64 Linux process. Before attempting `SCM_RIGHTS` cross-architecture, run a **single bounded no-libc ELF32 smoke probe** that uses the existing Clang 19 `-m32`, an i386 `_start` and an explicit Linux `exit` syscall. This tests whether WSL2 can execute a 32-bit binary despite missing i386 C++ multilib headers, without installing packages or touching the existing `mldr32`. Report execution unsupported as `SKIP_I386_RUNTIME`, not JACK regression.

After ELF32 execution is demonstrated, implement the mixed ELF32/ELF64 memfd+socket test with a fixed-width 64-byte header, strict untrusted header validation, safe lifecycle and no pointer values in the shared ABI. Continue using **only** `/home/Deniel/d4rling-audio/qualif` and no new source/build directories; do not rebuild existing Ninja/i386/Carbon/Audio trees. Defer guest Mach-O IPC until the independent Darling CA-12 runtime gate can be traversed; do not install JACK or its development libraries automatically.

**Verdict:** **JACK-01E8H=PASS on 5700X**; GO to bounded ELF32 runtime feasibility; NO-GO for asserting a working JACK/CoreAudio/Logic integration.

## 40. JACK-01E9 — Linux ELF32 static executable launched on 5700X (2026-10-26)

**Provenance:** user-pasted stdout from Debian 13 WSL2 (`Deniel@5700X`), executing inside the single existing `/home/Deniel/d4rling-audio/qualif` directory. This proof originates from the user's machine and has not been independently rerun via GitHub tools.

| Check | User terminal evidence | Verdict |
| --- | --- | --- |
| Compilation and linking | `BUILD_ELF32=PASS`, `clang-19 -m32 -nostdlib -static -no-pie -Wl,-e,_start -x assembler` | PASS |
| ELF format | `ELF 32-bit LSB executable, Intel i386, statically linked`; `readelf`: `Class ELF32`, `Type EXEC`, `Machine Intel 80386` | PASS |
| Native WSL2 i386 execution | Program invokes Linux i386 `exit(0)` using `int $0x80`; terminal `EXEC_EXIT=0` | PASS |
| Final verdict | `JACK01E9_STATUS=PASS_ELF32_NATIVE_EXEC` | PASS |
| Exclusions | `DARLING_RUNTIME=NOT_EXECUTED`, `REAL_JACK=NOT_EXECUTED` | NOT EXECUTED |

**Meaning:** The x86_64 Linux WSL2 host can execute a genuine 32-bit Linux ELF program *without i386 libc, dynamic loader or C++ standard-library headers*. This is separate from earlier i386 static/object codegen and independently built Darling `mldr32`. It **does not prove 32-bit C++ library availability, Mach-O guest runtime, or CoreAudio JACK operation**.

**Next gate JACK-01E10:** cross-bitness IPC using an *existing* 64-bit Linux `memfd`/`SCM_RIGHTS` server (JACK-01E8H) and a new **statically linked libc-free ELF32 client** compiled with the already-installed `clang-19 -m32`, operating on the same 64-byte SharedPCM header and 256-frame stereo float32 payload. The ELF32 client must perform Linux i386 socket syscalls, receive a memfd, validate ancillary metadata and header, mmap the shared region, verify ordered 50,000 stereo frames, advance 64-bit counters with acquire/release instructions, acknowledge completion and exit cleanly. Bound both processes via `timeout` and capture separate exit statuses. Before the host run, test the exact source against the known server in an isolated environment and pin the Git blob checksum. This test does not install multilib, JACK or touch Darling.

**Filesystem rule:** only `/home/Deniel/d4rling-audio/qualif`; no new `/home/Deniel/d4rling-*` working directories, no modifications to Ninja's build trees, no restart or installation of any Darling runtime/prefix, no CI (`[skip ci]`).

**Overall status:** JACK-01E9 **PASS_ELF32_NATIVE_EXEC**, JACK-01E8H **PASS_LINUX_MEMFD_FDPASS**, JACK-01E10 **PENDING**; actual Mach-O-to-ELF and JACK audio callback **NO-GO**.
## 41. JACK-01E10 — libc-free ELF32 client for ELF64 memfd server prepared, host runtime pending (2026-10-26)

**Code:** `tests/regressions/jack-transport/test_ipc_linux32_client.c` published in convergence branch commit `4354d72b58b7076d7f6ab843382748178bba2df8`, Git blob SHA **`94a2d53c082a0f1883742912ddce7a1a184386cf`**, **7,660 bytes**. The exact same blob was independently compiled in the assistant's isolated Linux container using installed Clang with `-m32 -march=i686 -std=c11 -O2 -nostdlib -static -fno-pie -ffreestanding -fno-builtin -fno-stack-protector -fomit-frame-pointer -Wall -Wextra -Werror -Wl,-e,_start`: **BUILD PASS**, ELF32 Intel 80386 static `EXEC`, **no unresolved symbols**. The container **does not support ELF32 execution** (`Exec format error` / shell fallback), so **NO runtime PASS is claimed** until the user runs JACK-01E10 on the 5700X.

**Cross-architecture protocol:** use the *already host-qualified* `jack01e8_linux_ipc_fdpass` **ELF64** server binary under the same existing `/home/Deniel/d4rling-audio/qualif`. Launch a separate, static, libc-free **ELF32 client** from `test_ipc_linux32_client.c`. It uses Linux i386 `int $0x80`, `socketcall` with 32-bit `msghdr`/ancillary headers, receives server memfd using `SCM_RIGHTS`, checks returned file size via i386 `lseek`, maps `mmap2(MAP_SHARED)`, verifies versioned 64-byte SharedPCM header and **50,000 ordered stereo float32 frames**, uses explicit acquire/release 64-bit cursor atomics, then sends a one-byte acknowledgement to server and reports its exit code.

**Security/test limits:** only a controlled local same-user test socket; no credentials/peer-auth enforcement or arbitrary external fd acceptance is designed. `sched_yield`, connection retry loops, `alarm`, error printing and regular syscalls belong exclusively to this test client, **not a real-time JACK callback**. The client source has been compile/link and format qualified but its i386 syscall ABI compatibility, 32/64 `SCM_RIGHTS` translation and interprocess PCM transfer have **not** yet been tested on WSL2.

**Next user-executable gate JACK-01E10H:** do not create directories, install multilib, download JACK libraries or change any Darling runtime. Reuse `~/d4rling-audio/qualif`, retrieve the pinned **7,660 byte** C source from commit `4354d72...` *only if absent*, verify `git hash-object` == `94a2d53...`, compile with existing Clang 19 and verify ELF32 static and no unresolved symbols. Start only the existing JACK-01E8 ELF64 server in server mode with a unique temporary Unix socket filename in `qualif`, then launch the new ELF32 client with an independent process image, bound both with `timeout`, check both exit codes and 50,000 transferred frames and clean only that owned socket.

**Result labeling:** PASS requires both `JACK01E8_SERVER_STATUS=PASS` and `JACK01E10_CLIENT_STATUS=PASS_ELF32_MIXED_IPC`, `SERVER_EXIT=0`, `CLIENT_EXIT=0`, and 50,000 frame counters. If it fails, retain logs and classify source of `socketcall`, CMSG/compat, mmap2 or atomic discrepancy rather than calling JACK failed. It tests mixed-bitness *Linux ELF32 ↔ Linux ELF64* only, **NOT Mach-O i386 ↔ ELF64 Darling**, and not JACK/ALSA/Logic Studio 8. CA-12 RPC failure still independent.

**State:** host JACK-01E9 **PASS_ELF32_NATIVE_EXEC**, native JACK-01E8H **PASS_LINUX_MEMFD_FDPASS**, new client JACK-01E10 **BUILD_PASS in assistant isolated container / HOST_RUNTIME_PENDING**, real JACK **NOT_EXECUTED**. PR #5 remains draft; `[skip ci]`; no Ninja build/prefix modifications.

## 42. JACK-01E10H — mixed ELF32 client / ELF64 server PCM IPC PASS on 5700X (2026-10-26)

**Evidence provenance:** exact terminal stdout supplied by user from `Deniel@5700X` Debian 13 WSL2, under canonical `/home/Deniel/d4rling-audio/qualif`. This GitHub update did not execute any commands on that machine.

| Gate | User-observed result |
| --- | --- |
| Source authenticity | User-initiated `SOURCE_FETCH=7660_BYTES`; `SOURCE_HASH=PASS`, expected Git blob `94a2d53c082a0f1883742912ddce7a1a184386cf` from convergence commit `4354d72b58b7076d7f6ab843382748178bba2df8` |
| ELF32 build | `BUILD_ELF32=PASS`, `ELF 32-bit LSB executable, Intel i386, statically linked`, ELF class 32, `Type EXEC`, `Machine Intel 80386` |
| Independent ELF64 server | Existing `jack01e8_linux_ipc_fdpass` started in `server` mode; 64-byte shared header |
| FD delivery over AF_UNIX socket | `IPC_ELF32_CLIENT_RECEIVED_FD=YES`, server accepted and transmitted Linux memfd via `SCM_RIGHTS` |
| Data validation | Server `IPC_SERVER_WRITE_FRAMES=50000`, `IPC_SERVER_READ_FRAMES=50000`; ELF32 client `IPC_ELF32_READ_FRAMES=50000` |
| Terminal handshakes | `IPC_SERVER_ACK=PASS`, `JACK01E8_SERVER_STATUS=PASS`, `JACK01E10_CLIENT_STATUS=PASS_ELF32_MIXED_IPC` |
| Exit codes | `SERVER_EXIT=0`, `CLIENT_EXIT=0` |
| Final marker | `JACK01E10H_STATUS=PASS_MIXED_ELF32_ELF64_IPC` |
| Deferred runtime | `MACHO_RUNTIME=NOT_EXECUTED`, `REAL_JACK=NOT_EXECUTED` |

**Qualification:** PASS of a real end-to-end **Linux ELF32 i386 process ↔ Linux ELF64 x86_64 process**, with a 64-byte layout-stable `SharedPCM` header, cross-process Linux `memfd` and Unix `SCM_RIGHTS` descriptor passing, and **50,000 ordered synthetic stereo float32 frames checked by the client**. Static i386 binary required no C++ multilib or i386 libc. This establishes *mixed Linux bitness IPC on the target machine*, not only compiler codegen.

**Limits and next engineering decision:** This is NOT a Mach-O i386 guest. The client uses native Linux i386 syscalls (`socketcall`/`mmap2`); these cannot simply be assumed compatible with Darling's Darwin guest syscall and libc ABI. JACK, ALSA, real PCM playback, scheduling deadlines, recovery after disconnect, clock sync, and Logic Studio 8 were never exercised. The previously reported Darling CA-12 Mach-O guest RPC failure (`mach_msg_overwrite`/dserver error `-111`) is still an **independent runtime blocker**, not repaired by this Linux IPC success.

**Next focused gate JACK-01E11:** STOP creating more synthetic transport/codegen variants. Coordinate with the concurrent Ninja/runtime owner to restore or at least reproduce guest process boot / CA-12 with a safe, read-only preflight before any Mach-O-to-ELF IPC experiment. Audit how guest Mach-O i386 can invoke a Darwin-side minimal socket/FD mapping/client contract through the existing Darling `libsystem_kernel`, syscall translation and `mldr32`, then prepare a *compile-only* isolated Mach-O guest adapter if and only if the available headers and loader ABI are grounded. Keep actual runtime launch behind a host-safe explicit gate, with no touching active prefixes or replacing CoreAudio/PulseAudio.

**Directory and publication rule:** all host tests belong inside the existing `/home/Deniel/d4rling-audio/qualif`. Existing `d4rling-core`, `d4rling-audio`, `d4rling-ui` build trees and runtime prefixes remain untouched; no package installs, no JACK daemon, no CI, `[skip ci]`; PR #5 stays draft from `work/coreaudio-ninja-convergence` into `work/core-audio`.

**Verdict:** `JACK-01E10H=PASS_MIXED_ELF32_ELF64_IPC` **on 5700X**, `MACHO_RUNTIME=NOT_EXECUTED`, `REAL_JACK=NOT_EXECUTED`, **GO** for targeted guest-boundary analysis only; **NO-GO** for end-to-end CoreAudio/JACK/Logic Studio 8.

## 43. JACK-01E11A — Darwin i386 guest socket ABI compilation probe (2026-10-27)

**Motivation / completed prior gate:** On the user `5700X` host, JACK-01E10H demonstrated **50,000 stereo frames** transferred between independent **Linux ELF32 i386** and **Linux ELF64 x86_64** processes through Linux `memfd` + `SCM_RIGHTS` (`PASS_MIXED_ELF32_ELF64_IPC`, process RCs 0/0). This does NOT exercise Darling/Mach-O. The next useful gate is a **source-level Darwin ABI adapter**, not more Linux SPSC model stress.

### Pinned ABI source inspection (not guesses)

Audited `src/external/xnu` gitlink on `work/core-audio` at commit `fa29287aa2f0115271e091f1031f53c9e024005d` (`darlinghq/darling-xnu`):

- [`bsd/sys/socket.h`](https://github.com/darlinghq/darling-xnu/blob/fa29287aa2f0115271e091f1031f53c9e024005d/bsd/sys/socket.h) declares Darwin `SOL_SOCKET=0xffff` (Linux is `1`), `SCM_RIGHTS=1`, `MSG_TRUNC=0x10`, `MSG_CTRUNC=0x20` and a **28-byte i386 `msghdr`** with **12-byte `cmsghdr`**. The `msg_controllen`/`msg_iovlen` types must be honored rather than assuming the Linux i386 `socketcall` ABI.
- [`bsd/sys/un.h`](https://github.com/darlinghq/darling-xnu/blob/fa29287aa2f0115271e091f1031f53c9e024005d/bsd/sys/un.h) defines Darwin `sockaddr_un` with an **8-bit `sun_len` preceding `sun_family`**, and `sun_path[104]`, total **106 bytes** for the i386 layout. Linux `sockaddr_un` is not wire- or source-layout-identical.
- [`bsd/sys/mman.h`](https://github.com/darlinghq/darling-xnu/blob/fa29287aa2f0115271e091f1031f53c9e024005d/bsd/sys/mman.h) defines `PROT_READ=1`, `PROT_WRITE=2`, `MAP_SHARED=1`, required for a guest mapping request. Handling a **Linux memfd passed into a Darwin Mach-O process remains unproven**.

### New code and independent compile-only qualification

Published `tests/regressions/jack-transport/test_darwin32_socket_abi.c` on the PR branch, commit `cd656607f0d2a2657d025f81808b264185479878`. Exact Git blob SHA **`82f0efb7606fe3119eb1c9465857a9c27b4ed2a5`**, **5,500 bytes**. This is a freestanding i386-only **Mach-O object probe**, not a runnable client, without SDK headers or i386 multilib. It statically asserts Darwin socket structure sizes and offsets plus the shared PCM header 64-byte alignment/layout and full payload 2,112 bytes.

**Independently tested in the assistant isolated Linux environment** (Clang 17, NOT user WSL2):

```sh
clang -target i386-apple-darwin -march=i686 -std=c11 -O2 -ffreestanding -nostdinc \
  -fno-stack-protector -fno-builtin -fno-pie -Wall -Wextra -Werror \
  -c test_darwin32_socket_abi.c -o test_darwin32_socket_abi.o
```

Compiler exit 0; `file` reported **`Mach-O i386 object`**. `llvm-objdump --macho --syms` showed defined `_jack01e11_darwin32_socket_probe` and `_memset`; six intentionally **undefined Darwin userspace imports** `_socket`, `_connect`, `_recvmsg`, `_mmap`, `_munmap`, `_close`. The test is not link-qualified and has **never run in Darling**. The user-host Clang 19 compile is still PENDING.

### Behavioral boundary

The probe's function prepares a Darwin `sockaddr_un`, calls Darwin userspace `socket/connect/recvmsg`, validates `SOL_SOCKET`/`SCM_RIGHTS` and a candidate 2,112-byte `MAP_SHARED` region with the 64-byte `SharedPCM` header. It deliberately performs **no PCM consumption and sends no acknowledgement**: **NEVER RUN IT AGAINST A LIVE JACK-01E8 SERVER**, because that server would wait for a consumer/ACK. Both the Linux-to-Darwin translation of ancillary `cmsg_level` and transfer/mapping of a Linux memfd into a Darling guest are **unqualified**. Missing guest runtime linkage, alias symbols, virtual filesystem pathname handling and CA-12 `mach_msg_overwrite` / dserver `-111` remain separate blockers.

### Next safe action

Run the **compile-only** test on the 5700X in the existing `/home/Deniel/d4rling-audio/qualif` directory using `clang-19 -target i386-apple-darwin ... -c`, verify pinned Git blob SHA and Mach-O i386 format; inspect undefined imports with `llvm-nm-19 -u`. **No executable or dylib link and no Darling/CA-12 runtime invocation**, no audio or JACK daemon, no new directories, no Ninja edits, no package installs or CI. If the host result is PASS, review the available Darling Mach-O i386 libSystem export/alias contract and launchability **separately** before any guest-to-Linux IPC integration.

**Verdict:** GO for the code-audited **Mach-O i386 ABI object** path; **NO-GO for guest↔Linux runtime, JACK CoreAudio or Logic Studio 8 claims**. PR #5 remains draft (`work/coreaudio-ninja-convergence` → `work/core-audio`).

## 44. JACK-01E11H — 5700X Darwin i386 Mach-O ABI object BUILD PASS; import-check false negative (2026-10-27)

**Actual user-host evidence:** `Deniel@5700X`, Debian 13 WSL2; actual `WORKDIR=/home/Deniel/d4rling-audio/qualif`. Source Git blob `82f0efb7606fe3119eb1c9465857a9c27b4ed2a5`: `SOURCE_HASH=PASS`. `clang-19 -target i386-apple-darwin ... -c` reported `BUILD=PASS`; `file` reported `jack01e11_darwin32_socket_abi.o: Mach-O i386 object`. Thus this is a **verified user-host compile-only PASS**, not a link/runtime pass.

**Actual output of `llvm-nm-19 -u`:**

```text
_close
_connect
_mmap
_munmap
_recvmsg
_socket
```

The prior Bash verifier then emitted `IMPORT_MISSING=_socket` and exited early. This was **a test-harness false negative**: it used `grep -Eq " U ${symbol}$"`, which assumes nm prints a ` U ` type field, whereas this version of `llvm-nm-19 -u` **prints only symbol names**. All six expected undefined imports are visibly present. Do **not** label this as a missing Mach-O symbol or a failed compilation.

**Correct minimal check (reusing preexisting log, no rebuild):**

```sh
cd "$HOME/d4rling-audio/qualif" || exit 1
for symbol in _socket _connect _recvmsg _mmap _munmap _close; do
    grep -Fxq -- "$symbol" jack01e11_imports.log || { echo "IMPORT_MISSING=$symbol"; exit 1; }
done
echo JACK01E11H_IMPORTS=PASS_6_OF_6
```

**Scope:** `llvm-nm -u` displays **undefined imports referenced by the object**. It proves neither that those functions are exported by the installed guest i386 dylibs nor that the Mach-O linker and Darling runtime can resolve them. The probe performs no real PCM loop, no acknowledgment, no guest runtime test and no JACK execution.

**Evidence-backed source-level next step:** In the fork's pinned `darlinghq/darling-Libsystem` submodule `08df454b6eb0df9400aa4c39839a7efd6efd2c3c`, `CMakeLists.txt` defines `/usr/lib/libSystem.B.dylib` as a **reexporter** of `libsystem_c.dylib` and `libsystem_kernel.dylib` (among others). The `darling-xnu` submodule `fa29287aa2f0115271e091f1031f53c9e024005d` builds `libsystem_kernel.dylib` with 32-bit `libsyscall_32` objects. Therefore the correct next gate is a **read-only inspection of the actual i386 Mach-O exports and reexports in the already installed `/opt/d4rling-qt-i386/libexec/darling/usr/lib` tree** on the 5700X, not another test of Linux atomics or a blind `darling exec` run. Do not assume an apparent absence in the umbrella dylib means an underlying reexport is missing. The prior CA-12 RPC -111 problem remains independent.

**Verdict:** `JACK-01E11H=PASS_BUILD_MACHO_I386_OBJECT`, expected six undefined imports observed (original checker FAIL due to wrong output parsing); symbol **resolution/linking=UNQUALIFIED**, `DARLING_RUNTIME=NOT_EXECUTED`, `REAL_JACK=NOT_EXECUTED`. PR #5 remains draft; no Ninja changes, no CI, no JACK install, no additional host directories.

## 45. JACK-01E11I — Guest-imports PASS; installed QT i386-prefix system dylibs are x86_64-only in inspected paths (2026-10-27)

**Provenance:** exact stdout pasted by user from `Deniel@5700X` Debian 13 WSL2. Command used `cd "$HOME/d4rling-audio/qualif"` and inspected preexisting files under `/opt/d4rling-qt-i386/libexec/darling/usr/lib`. No command was issued to the host from GitHub.

**Corrected import verifier:** `grep -Fxq -- "$symbol" jack01e11_imports.log` printed `IMPORT_PASS=` for **all six** `_socket`, `_connect`, `_recvmsg`, `_mmap`, `_munmap`, `_close`, followed by `JACK01E11H_STATUS=PASS_6_IMPORTS`. This corrects the previous false negative in JACK-01E11H; the object still contains six **undefined references**, not proven resolved exports.

**Actual installed prefix:**

| Inspected existing path relative to `/opt/d4rling-qt-i386/libexec/darling/usr/lib` | `file -L` observation | i386 inspection |
| --- | --- | --- |
| `libSystem.B.dylib` | Mach-O **64-bit x86_64** dynamically linked shared library, non-FAT as printed | `llvm-nm-19 --arch=i386 -g --defined-only` exited `NM_READ=INCONCLUSIVE`; printed `No architecture specified` |
| `system/libsystem_kernel.dylib` | Mach-O **64-bit x86_64** dynamically linked shared library, non-FAT as printed | same `NM_READ=INCONCLUSIVE`, same diagnostic |
| `system/libsystem_c.dylib` | Mach-O **64-bit x86_64** dynamically linked shared library, non-FAT as printed | same `NM_READ=INCONCLUSIVE`, same diagnostic |

User script ended `JACK01E11I_STATUS=STATIC_INSPECTION_COMPLETE`; `LINK=NOT_EXECUTED`, `DARLING_RUNTIME=NOT_EXECUTED`, `REAL_JACK=NOT_EXECUTED`.

**Precise interpretation:** The inspected files in the **installed QT prefix** do not expose an i386 Mach-O slice according to `file`. Do NOT mistake the prefix's label `qt-i386` for an installation guarantee. The `llvm-nm --arch=i386` errors **do not prove absence of the symbols in the repository** and should not be counted as six export failures. Export lookup/linking on the actual i386 runtime remains **BLOCKED / UNQUALIFIED** for these specific paths. Earlier I386-13 evidence reported a **FAT i386+x86_64 `libsystem_kernel.dylib` produced by an i386 build**, independently of this installed prefix. Locate that artifact and check the matching `libSystem.B.dylib`/`libsystem_c.dylib` in the existing inactive/active build tree by **read-only file-format inspection**, not by copying/installing over `/opt`.

### Next safe gate JACK-01E11J — compare installed prefix vs build artifacts, read-only

Inspect `file -L` (and `llvm-lipo-19 -info` only if installed) for the same three names under `/opt/d4rling-qt-i386/libexec/darling/usr/lib`, and run a targeted `find` within `/home/Deniel/d4rling-core/d4rling-build-i386` with `-maxdepth` and exact file basenames to locate candidates. Report **which exact files have a genuine i386 Mach-O slice**; do not run `llvm-nm --arch=i386` on a thin x86_64 file or infer that a missing result is a linker failure. Retain all artifacts in place, no new folders, no Ninja/relink/install, no guest execution or JACK daemon.

If only `libsystem_kernel.dylib` has an i386 slice but `libSystem.B.dylib` or `libsystem_c.dylib` do not, the guest dynamic linking path remains blocked; it requires a **coherent i386 guest runtime set**. The earlier static ELF32 Linux memfd client success **cannot substitute for missing Darwin dylibs**. CA-12's RPC `-111` remains an independent blocker even after successful linking.

**Verdict:** `JACK-01E11H_IMPORTS=PASS_6_OF_6`, installed x86_64 dylib architecture **CONFIRMED for three paths**, `I386_LINK_EXPORTS=NOT_QUALIFIED`, `MACHO_RUNTIME=NOT_EXECUTED`, `REAL_JACK=NOT_EXECUTED`. PR #5 draft, `[skip ci]` documentation only.

## 46. JACK-01E11J — i386 FAT kernel built, but installed guest System libraries are x86_64-only (2026-10-27)

**Provenance:** User-pasted stdout from `Deniel@5700X`, Debian 13 WSL2. Command explicitly `cd` into sole canonical `/home/Deniel/d4rling-audio/qualif`, inspected `/opt/d4rling-qt-i386/libexec/darling/usr/lib` and `/home/Deniel/d4rling-core/d4rling-build-i386` **read-only**. No user machine commands run by this documentation update.

| Existing artifact / relative path | `file -L` and `llvm-lipo-19 -archs` result |
| --- | --- |
| `/opt/d4rling-qt-i386/libexec/darling/usr/lib/libSystem.B.dylib` | thin `x86_64`, **no i386 slice** |
| `/opt/d4rling-qt-i386/libexec/darling/usr/lib/system/libsystem_kernel.dylib` | thin `x86_64`, **no i386 slice** |
| `/opt/d4rling-qt-i386/libexec/darling/usr/lib/system/libsystem_c.dylib` | thin `x86_64`, **no i386 slice** |
| `/home/Deniel/d4rling-core/d4rling-build-i386/src/external/xnu/darling/src/libsystem_kernel/libsystem_kernel.dylib` | **FAT universal Mach-O with `x86_64 i386` slices**, `I386_SLICE=YES` |

Exactly **one matching build-tree candidate** was found by the user script's basename-restricted `find -maxdepth 18` (`BUILD_CANDIDATES=1`); **no** `libSystem.B.dylib` nor `libsystem_c.dylib` was found by that scan. The scan's scope is *not* a proof of global absence, nor does an existing FAT kernel demonstrate an operational guest system library set. Terminal verdict `JACK01E11J_STATUS=ARCH_INVENTORY_COMPLETE`, `FILES_MODIFIED=NO`, `NINJA=NOT_EXECUTED`, `DARLING_RUNTIME=NOT_EXECUTED`.

**Interpretation:** The i386 kernel Mach-O is **already produced** by the i386 Ninja build and can be read without rebuilding or installing. The named `/opt/d4rling-qt-i386` installation is **not yet an i386 guest System stack** for the three inspected dylibs, regardless of directory naming. The guest `libSystem.B` normally **reexports** `libsystem_kernel` and `libsystem_c`; reexports and direct symbols must be distinguished. The `libsystem_kernel` CMake target in pinned Darling XNU uses conditional `$<TARGET_OBJECTS:libsyscall_32>` and a FAT library (`make_fat(system_kernel)`), which is consistent with the observed universal artifact. No need to rerun any JACK transport/codegen microtests.

### Next gate JACK-01E11K — binary exports and build-target availability, no Ninja

1. Read the **FAT i386 slice** of the existing `/home/Deniel/d4rling-core/d4rling-build-i386/src/external/xnu/darling/src/libsystem_kernel/libsystem_kernel.dylib`; inspect exported `_socket`, `_connect`, `_recvmsg`, `_mmap`, `_munmap`, `_close` with an architecture-aware `llvm-nm-19` (if necessary `llvm-lipo-19 -thin i386` only to an owned file in `/home/Deniel/d4rling-audio/qualif`, never into a build or prefix directory). These are **defined exports** and must not be confused with the six **undefined imports** in `jack01e11_darwin32_socket_abi.o`. The six may be split among kernel and libc, and reexports should be accounted for.
2. Inspect existing `build.ninja` metadata **without executing Ninja** for the two absent target output paths (`libSystem.B.dylib`, `libsystem_c.dylib`) to determine whether outputs are planned, disabled or renamed; do not interpret a missing output file as proof of a configuration bug. Avoid reading large binary files recursively.
3. Keep CA-12 RPC/dserver `-111` separate. No install/copy into `/opt`, no rebuild of active Ninja trees, no Darling execution, no JACK install/start, no CI; only existing qualif directory for any logs.

**State:** `JACK-01E11J=PASS_INVENTORY`, `FAT_LIBSYSTEM_KERNEL_I386=YES`, `INSTALLED_SYSTEM_I386=NO (three inspected dylibs)`, `GUEST_DYLIB_COHERENCE=BLOCKED`, `JACK_REAL=NOT_EXECUTED`; PR #5 remains draft. Candidate Mach-O i386 object `JACK-01E11H=PASS_BUILD`, but link and runtime unresolved.

## 47. JACK-01E11K — i386 `libsystem_kernel` defines all six required guest socket/mapping functions (2026-10-27)

**Provenance:** Actual `Deniel@5700X` Debian 13 WSL2 stdout supplied by user, from `/home/Deniel/d4rling-audio/qualif`. No operations were executed on the user's WSL2 host by the GitHub agent. All host inspection was read-only.

**Input binary:** `/home/Deniel/d4rling-core/d4rling-build-i386/src/external/xnu/darling/src/libsystem_kernel/libsystem_kernel.dylib`. `file -L` identified a two-architecture universal Mach-O shared library (`x86_64` and `i386`), `llvm-lipo-19 -archs` printed `ARCHS=x86_64 i386`; final `I386_SLICE=PASS`.

**Guest i386 defined symbols**, obtained by `llvm-nm-19 --arch=i386 -g --defined-only`: `NM_I386=PASS`, with **all six** checks positive:

| Symbol required by JACK-01E11H guest object | Actual audit |
| --- | --- |
| `_socket` | `KERNEL_EXPORT=YES:_socket` |
| `_connect` | `KERNEL_EXPORT=YES:_connect` |
| `_recvmsg` | `KERNEL_EXPORT=YES:_recvmsg` |
| `_mmap` | `KERNEL_EXPORT=YES:_mmap` |
| `_munmap` | `KERNEL_EXPORT=YES:_munmap` |
| `_close` | `KERNEL_EXPORT=YES:_close` |

**Interpretation:** The i386 slice contains the six required **globally defined symbols**. This reconciles the six undefined Mach-O i386 object imports with an actual matching-architecture *build artifact*. It is **NOT yet** proof of dyld export-trie visibility, successful Mach-O linker resolution, availability in the installed guest runtime, nor execution inside Darling. The installed `/opt/d4rling-qt-i386` prefix's `libSystem.B.dylib`, `libsystem_kernel.dylib` and `libsystem_c.dylib` were separately shown thin x86_64 only by JACK-01E11J.

**Ninja manifest inspection:** The user's `awk` stopped after the first 12 `build` lines containing the strings `libSystem.B.dylib` or `libsystem_c.dylib` in *any* position. It printed one direct `C_SHARED_LIBRARY_LINKER__system_c_Debug` rule for `src/external/libc/libsystem_c.dylib`, plus multiple **consumer/dependency rules** referring to `libSystem.B.dylib` or `libsystem_c.dylib`. These 12 lines **do not establish whether** the defining `build src/external/libsystem/libSystem.B.dylib: ...` rule exists or whether either output is buildable under current flags. Nor do they demonstrate that any of the two missing binaries actually exists on disk. User terminal ended `JACK01E11K_STATUS=STATIC_AUDIT_COMPLETE`, `NINJA_EXECUTED=NO`, `BUILD_FILES_MODIFIED=NO`, `DARLING_RUNTIME=NOT_EXECUTED`, `REAL_JACK=NOT_EXECUTED`.

### Next safe gate JACK-01E11L — precise target availability, *no build*

From `/home/Deniel/d4rling-audio/qualif`, read only `/home/Deniel/d4rling-core/d4rling-build-i386/CMakeCache.txt` and `build.ninja`. Query **exact output rules** for `src/external/libsystem/libSystem.B.dylib` and `src/external/libc/libsystem_c.dylib`, clearly distinguishing target definitions (`^build <output>:`) from other rules that merely mention those paths as dependencies. Also check on-disk existence and file formats for those exact two target paths, and relevant `BUILD_TARGET_32BIT`, `BUILD_TARGET_64BIT`, `TARGET_i386` cache values. Do not make false claims from `grep`/`awk` first-12 truncation; use `RULE=NOT_FOUND` or `FILE=ABSENT` only for the specified paths, not the entire repository.

**Next decision:** If the umbrella and libc Mach-O i386 outputs are absent but their build rules exist, coordinate a future **targeted, safely isolated** build with the concurrent Ninja owner; do not start it from this lot. If build rules are missing, first inspect CMake config. Do **not** copy the FAT kernel into `/opt`, restart guest prefixes, run Ninja, modify existing build trees, install packages, start JACK or execute guest Mach-O. CA-12 dserver RPC `-111` remains a separate runtime blocker.

**Verdict:** `JACK-01E11K=PASS_6_OF_6_DEFINED_I386_KERNEL_SYMBOLS` (host evidence); `LIBSYSTEM_C_TARGET_RULE=OBSERVED`, `LIBSYSTEM_B_TARGET_RULE=UNRESOLVED`, `GUEST_DYNAMIC_LINK=NOT_EXECUTED`, `DARLING_RUNTIME=NOT_EXECUTED`, `REAL_JACK=NOT_EXECUTED`. Draft PR #5 (`work/coreaudio-ninja-convergence` → `work/core-audio`) remains unmerged; `[skip ci]` documentation only.
