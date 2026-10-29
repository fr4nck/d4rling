# Logic Studio 8 work in the personal fork

This work is developed in `fr4nck/d4rling`. It has not been submitted to
`darlinghq/darling`. No Logic installation or execution has been performed.

## Reference and changes

Base: `60ba801decee7a00782f74f6be4c8ffb013f79ff`.
The first local work commit, `2b4a018fc2a71d12844aa0438075422756816685`,
contains the supplied HIToolbox window error-reporting patch and its 25 isolated
assertions. It implements no windowing backend.

The next change ports only the five declaration/definition corrections from
[VibeDarling PR 18](https://github.com/VibeDarling/darling/pull/18), original commit
`df1fe1b560b25310f83e64f3d1fa5a9be7f0a9a2`, by Cristian Magherusan-Stanciu.
The original commit records Claude assistance. The port was prepared with Codex.

- Match `AudioConverterNewSpecific`'s existing const class-description prototype.
- Declare `AudioHardwareGetPropertyInfo` in its existing C-linkage header block.
- Match the existing const-pointer definitions of `FSGetCatalogInfo` and
  `UCConvertUTCDateTimeToCFAbsoluteTime`.
- Replace duplicate Unicode-to-text declarations with the missing text-to-Unicode
  declarations, also within the existing C-linkage block.

Matching these declarations is intended to provide the plain C symbols that
guest applications import. Exported symbols have not been checked in rebuilt
Darling libraries; this is not a claim that Logic reaches those calls.

## Verification recorded on 2026-10-15

The five-file patch passes `git -c core.autocrlf=false apply --check` against
copies of the pinned source. Applied content matches the source patch, and the
reverse application check passes. The source files on the work branch were
compared to the pinned baseline before committing. Definitions in FileManager,
DateTimeUtils, UnicodeConverter and AudioHardware, plus AudioConverter's header
prototype, were inspected for the matching signatures.

The supplied HIToolbox assertions were executed on Debian 13.5 x86_64 using GCC
14.2.0, C++17, with their original minimal test header and no attribute shim:
original source 25 checks / 23 failures (exit 1), patched source 25 checks /
0 failures (exit 0). The delivered Linux runner also passed with 25 checks /
0 failures. The preexisting unused global `closeDisplay` declaration warning
appears in both builds. Windows MSVC results and test limitations are documented
in `tests/regressions/hitoolbox-windows/README.md`.

These assertions exercise the window-stub patch, not the five C API corrections.
No new tests or test results for those corrections are claimed.

## Remaining validation

A full Darling build and export inspection require a suitable toolchain and
dependencies. Direct checks confirmed GCC and Git in Debian; the earlier report
that all development tools were absent was caused by the WSL command invocation.
Clang, CMake, Ninja and pkg-config were not found. No packages were installed.

Genki ALSA/CoreMIDI and VibeDarling MIDI-constant and Cocotron changes are not
imported. Audio error handling, MIDI packet bounds and worker lifetime, locally
chosen property values, and coherent AppKit/backend rebuilding still require
investigation. No GUI rendering, audio hardware, MIDI hardware, Carbon ABI or
Logic compatibility has been validated.

## Additional source-level validation and fork maintenance

On 2026-10-15, workspace-local Clang 19.1.7 compiled the real DateTimeUtils.cpp
and UnicodeConverter.cpp before and after the header corrections. The real
CoreFoundation revisions were a3640a77410cf1825f7855172b1551ae7917c461 and nested
ea1ea0bb416025a8cc5a282df03c2e8f12788e2d. nm confirms C++-mangled names before
and plain C names after for UCConvertUTCDateTimeToCFAbsoluteTime,
CreateTextToUnicodeInfo and CreateTextToUnicodeInfoByEncoding.

This is a Linux x86_64 ELF object check with __APPLE_CC__=1,
DEPLOYMENT_RUNTIME_SWIFT=1 and a forced include of the real MacTypes.h. It is not
a complete Darling/Mach-O build, exported-library check or functional API test.
The Unicode functions remain stubs. DateTimeUtils emits its existing
LLONG_MAX-to-double warning on both versions. Three other corrected functions
remain unvalidated by compilation. Clang was extracted into the workspace from
Debian packages, without installing system packages; CMake/Ninja and full build
dependencies remain unavailable.

The default master branch is the integration line for upstream history and this
fork's changes. The README records the manual merge procedure; no periodic sync
is configured. All 149 sibling submodule URLs are made absolute under darlinghq
without changing their pinned revisions. See CREDITS.md for imported work and
attribution. Being integrated into this development fork does not imply that a
full application or full build has been validated.

## Carbon event contract follow-up (2026-10-15)

Based on master b932d448bbb317654a45640717925823d2fd3fb0, a focused work branch
corrects the public callback/UPP types and GetWindowEventTarget's return type.
The unavailable window target now returns null. The original window fixture and
one assertion follow this corrected contract.

Real-header host checks with Clang 19.1.7 fail on the old signatures and pass
in C11/C++17 after correction; incompatible callbacks are rejected. Both host
executables return exit 0, and the updated standalone GCC window checks report
25 checks / 0 failures. The delivered regression runner was executed as well.
Details, sources, commands and limitations are in
[the contract regression record](../tests/regressions/carbon-contracts/README.md).
No GUI, event dispatch, full Darling build, i386 guest ABI or Logic runtime
validation is claimed. This does not complete the event-core milestone.

## Carbon event objects follow-up (2026-10-15)

Parent c003abfdad4adebc327d8c5c1875d9761ef5b4d2, on the same work branch/PR.
CreateEvent now allocates metadata-bearing event objects with allocator ownership;
class/kind/time accessors and atomic reference counting are implemented.
GetCurrentEventTime uses the monotonic clock for zero-time creation.

The source-level creation probe reproduces false success on the parent and
passes after correction. The delivered host regression runner reports 54 checks /
0 failures, including four-thread retain/release stress and injected allocation
failure. The same checks pass with AddressSanitizer and leak detection. The
previous C/C++ signature checks still pass. Host nm shows the expected C names.

These tests compile real production source/headers but substitute a small,
identified CF allocator adapter. Real CoreFoundation integration, full Darling
and Mach-O builds, i386 guest validation, queues/dispatch and graphics remain
pending. No Logic/audio/MIDI result is claimed.
See [event regression details](../tests/regressions/carbon-events/README.md).


## Carbon parameters and event cloning (2026-10-18, GitHub-only)

On work/carbon-event-contracts (draft PR #2), SetEventParameter,
GetEventParameter, RemoveEventParameter and CopyEvent now manage typed
byte-owned records, error reporting, atomic lifetime integration and deep
copies of parameter bytes using the original allocator. The existing host
test runner includes a new parameter/clone regression suite and controlled
allocation failure cases. AppleEvent type conversions remain unsupported.
The short-buffer/type-mismatch error selection is provisional.

NEW TESTS: NON EXÉCUTÉS in this GitHub-only session; previous 54 checks
and AddressSanitizer belong to the 2026-10-15 run. No CoreFoundation runtime,
Mach-O, i386, event dispatch, UI, MIDI/ALSA or Logic test is claimed.
See tests/regressions/carbon-events/README.md.


## Post-merge Carbon queue and bounded dispatch (2026-10-22)

Starting at master `10d0e885ffd8133256d6e657065d35ba64b8deb7`, a first lot now
implements prioritized main-queue posting, no-wait filtered receiving, borrowed
peeks/owned pulls and synchronous application-target handlers. Handler snapshots
preserve storage through removal and nested delivery. Nonzero receive timeouts,
per-thread loops and window/dispatcher propagation remain unsupported.

Executed in an isolated Linux container: GCC C11 246 PASS / 0 FAIL and GCC
ASan+UBSan 246 PASS / 0 FAIL (leak detection off); GCC static analysis is clean.
These compile production source and CarbonEventsCore.h with minimal dependency
fixtures and a test-only CF adapter, not the full Darling SDK/CF runtime.
LeakSanitizer was attempted but blocked by the container; Clang and the
real-dependency runner were not available. No download or install was performed.
See [scope, commands, evidence and remaining limits](carbon-queue-dispatch-2026-10-22.md).
This is not a full Darling build or a Logic Studio 8 compatibility result.

## D4RLING local qualification handoff (2026-10-29)

[The structured BH–CE handoff](d4rling-reprise-2026-10-29.md) records the
existing local campaign evidence, technical decisions, protected environment,
report locations and next acceptance gates. It separates BK's observed x86_64
Mach-O execution, BM/BN-R2's intercepted i386 loading and CB's differential
i386 instruction-execution proof. CE contains 100 observations across four
runs (19 PASS, 81 INFO), including a repeated marker control and dynamic timeouts;
it does not establish 100 successful application executions or fully operational
i386 dyld. The injected CB payloads use direct Linux i386 syscalls. Darwin APIs,
Qt/QuickTime, CoreAudio/JACK and Logic compatibility remain unqualified by these
campaigns. Earlier Carbon results above retain their original scope.

The [selected evidence register](evidence/jack01e12-bh-ce-2026-10-29.json)
contains technical conclusions and qualification boundaries. The handoff uses
anonymized report path patterns; precise paths, content hashes, full raw reports,
private binaries and prefixes remain local. The nine protected local changes remain
uncommitted and outside this documentation publication. No qualification was
rerun for this handoff; the current local checkout was read only.

## Reproducible project consolidation (2026-10-29)

[PROJECT_STATE.md](../PROJECT_STATE.md) is now the entry point for future work.
[Reproduction instructions](../reproduction/README.md) preserve the historical
b7d0cb6 local overlay and ignored parameters.c, 160 submodule pins, observed Debian
package versions, Carbon witness sources and portable scripts. The latest audit
also recovers QT-1980 dynamic Carbon (8/8 concurrent cases), QT-1993/1994, the
PR6 scope and the completed static QT-2211–2710 reports. These complement the
BH–CE handoff; they do not qualify a complete multimedia application.

A fresh independent source copy passed 135 Carbon host checks and their ASan
repeat, C11/C++17 contracts, and a 179-step native launcher/loader/server build.
The rebuilt Carbon witness passed NORMAL/BYPASS with a missing-dylib negative
control using the existing private system libraries. See the exact
[validation scope](../reproduction/validation.md). The original nine-file local
checkout remains unchanged. Private project archives and raw evidence remain
separate from the public reproduction sources.
