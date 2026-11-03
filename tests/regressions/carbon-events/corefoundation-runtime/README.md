# Darling CoreFoundation + HIToolbox real-runtime smoke gate

This is an experimental **runtime** gate for `fr4nck/d4rling`, kept separate
from the existing `carbon-events/run.sh` host regression runner. It must NOT
be satisfied by a Linux ELF program or by the test-only CF allocator adapter.

## Contents

- `corefoundation-smoke.c`: 18 assertions of real `CFAllocatorGetDefault`,
  `CFAllocatorAllocate`, `CFAllocatorDeallocate`, `CFRetain`, `CFRelease`,
  `CFGetRetainCount` and `CFStringCreateWithCString` behavior.
- `carbon-smoke.c`: 18 assertions across real `CreateEvent`, metadata,
  typed parameter storage, `CopyEvent`, removal and final release, when
  linked with production HIToolbox and production CoreFoundation.
- `run.sh`: fail-closed check of an already built x86_64 Mach-O executable,
  real Mach-O CoreFoundation library, direct dylib imports and a separately
  provided Darling executable wrapper; captures exit status and exact summary.
- `test-runner.sh`: offline, mocked **control-flow** regressions for `run.sh`.
  The dummy files, mock `file`, mock `llvm-objdump` and mock runner are NOT
  a runtime or library test, even when the mock positive cases pass.

## Preconditions

1. An **already configured** Darling x86_64 Mach-O compiler/linker environment
   and matching real SDK headers are available. Do not silently fetch/install
   any dependencies. Compile each C source to its own x86_64 Mach-O executable.
2. Link `corefoundation-smoke.c` against the **real** CoreFoundation dylib.
   Link `carbon-smoke.c` against real HIToolbox AND CoreFoundation. A host ELF
   shim or compiled source with fake CF headers is not a substitute.
3. Supply a real x86_64 CoreFoundation Mach-O library file and a local executable
   wrapper which takes exactly one Mach-O file path, executes it within Darling,
   forwards stdout/stderr and returns the guest program's exit code. The wrapper
   depends on the actual local Darling environment; this repository does not
   supply an unverified generic command that might launch an ELF by mistake.

## Invoke after the real binaries exist

```
sh tests/regressions/carbon-events/corefoundation-runtime/run.sh \
  corefoundation /path/to/cf-smoke-macho /path/to/CoreFoundation /path/to/darling-runner
sh tests/regressions/carbon-events/corefoundation-runtime/run.sh \
  carbon /path/to/carbon-smoke-macho /path/to/CoreFoundation /path/to/darling-runner
```

The runner's exit codes are **0** if all its checks passed and the trusted
wrapper produced the exact 18/0 summary, **1** if a launched test failed, and
**2** if a prerequisite is missing or untrustworthy. It never builds or downloads.

The runner verifies that imports include CoreFoundation (and, for Carbon,
HIToolbox). It **does not prove** which image the Darling loader resolved at
runtime. For a genuine end-to-end PASS, retain independent loader evidence that
both tested executables used the supplied real CoreFoundation image. Without
that independent evidence, record only the supplied-wrapper result.

## Qualification of this lot (2026-10-26)

- Source syntax using local minimal header fixtures: Clang 17 C11 **2 PASS**,
  GCC 14 C11 **2 PASS**. These are syntax checks only, NOT real SDK builds.
- Shell script syntax: **2 PASS**.
- Mocked runner control flow: **9 PASS / 0 FAIL**, explicitly infrastructure
  only; no Mach-O was executed by any mock.
- The isolated host has Clang/GCC/`llvm-objdump` but no `darling`, `mldr`, or
  `darlingserver`. Its `ld64.lld` rejected a macOS-target link attempt as
  unsupported; no usable real Mach-O runtime binary was built.
- Real Mach-O compile/link with genuine CoreFoundation: **NOT EXECUTED**.
- Actual Darling/CoreFoundation and HIToolbox integration: **NOT EXECUTED**.
- No packages installed, no external dependencies downloaded and no use of the
  owner's workstation. No changes to MIDI/ALSA.

These tests cannot by themselves demonstrate Logic Studio 8 compatibility.
Preserve this PR as draft until real headers and real runtime integration have
been exercised, or explicitly separate the runner-only change for integration.

GPL-3.0-or-later. No third-party implementation copied; original Darling
attributions are preserved in the parent repository.
