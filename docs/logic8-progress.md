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
