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
