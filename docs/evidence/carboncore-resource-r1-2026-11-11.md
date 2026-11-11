# CarbonCore Resource Manager R1 — 11 November 2026

Repository: fr4nck/d4rling; sole branch: master.
Preflight HEAD: 35973d9b9cfbb04fb767c59d288523fb2fb6733b.
Scope: ResourcesImpl.cpp/.h and a new isolated host regression suite.
Out of scope: installed Darling prefixes, CMake, submodules, M1/M2, G1-G4,
QuickTime, CoreAudio, SoundHack, Logic Studio 8, x86_64/Cocoa.

## Apple contracts and provenance

- [Resource fork format](https://ciderpress2.com/formatdoc/ResourceFork-notes.html):
  the type count belongs at the start of the type list; reference list offsets
  are relative to that start; names use a Pascal-length byte; resource data
  blocks begin with a big-endian 32-bit length.
- [Resource Manager RemoveResource](https://leopard-adc.pepas.com/documentation/Carbon/Reference/Resource_Manager/Reference/reference.html):
  removing a resource from its file map must not free its handle. The caller
  can dispose of the detached handle explicitly.
- [Apple Technical Note TB40](https://leopard-adc.pepas.com/technotes/tb/tb_40.html):
  corrects older partial-resource documentation. WritePartialResource does
  not automatically extend a resource on disk. The older documented
  inputOutOfBounds/resourceInMemory/writingPastEnd errors do not reflect the
  original Resource Manager behavior. Do not implement false-success writes.

## Actual production changes

- Byte-wise BE16/BE24/BE32 decoding instead of unaligned C++ structure and
  bitfield reinterpretation.
- Checked file section, resource map, type array, reference array, Pascal
  name and resource data extents before reading any bytes; overflow-safe
  range arithmetic.
- Empty type lists, unnamed resources, unsigned Pascal-name lengths and
  signed resource IDs; reject duplicate IDs for a given type.
- Proper attribute initialization and header self-containment (memory).
- No invalid handle insertion after allocation failure; retry remains possible.
- Avoid pointer arithmetic on a null resource handle in dataChanged.
- RemoveResource no longer frees a detached handle or uses an erased map
  iterator. Its caller retains ownership of the handle.

The pre-existing Resources::save() still does no persistent write and is NOT
claimed as implemented. No GUI, decoder, audio or i386 feature is claimed.

## Reproduced host tests

The source and header were compiled and exercised with a host-only
MacTypes/MacMemory/xattr adapter. Synthetic, original resource-fork files
were generated and read from temporary paths; there was no SDK, audio,
installed Darling, or proprietary sample.

GCC 14.2: O0 68/68 PASS; O2 68/68 PASS; ASan+UBSan.
Clang 17: O0 68/68 PASS; O2 68/68 PASS; ASan+UBSan.
GCC 14.2: 5/5 source mutants killed by contract assertions.
Clang 17: 5/5 source mutants killed by contract assertions.

Tests include one/two resources with independent data and names, a 200-byte
Pascal name, 0-byte resource, missing name, invalid/truncated file structures,
out-of-range lengths and pointers, duplicate IDs, handle ownership and
failure/retry of resource-handle allocation. This proves only host behavior.

Verified Git blob SHAs:
ResourcesImpl.cpp: 372496b37acaf4547ed05638cbc03fe0707cc90a
ResourcesImpl.h: 12790458bb94d38f10ad3fd2d038667884acf7b2
test.cpp: c5764b57982efada42104e4e7e7a9ec72d3674af
run.sh: 6ef2bd19ea0ee2d75147f7fc34d979095556ad02
check_mutations.py: 0d57e197136e7f1a1d7b9065b8a9e42fe7752099

## Reproduction on Linux

From a checkout at the R1 commit:

    bash tests/regressions/carboncore-resource-r1/run.sh g++
    bash tests/regressions/carboncore-resource-r1/run.sh clang++
    D4_R1_OPT_LEVEL=-O2 bash tests/regressions/carboncore-resource-r1/run.sh g++
    D4_R1_OPT_LEVEL=-O2 bash tests/regressions/carboncore-resource-r1/run.sh clang++
    python3 -B tests/regressions/carboncore-resource-r1/check_mutations.py g++
    python3 -B tests/regressions/carboncore-resource-r1/check_mutations.py clang++

The runner pins production file/header SHA, compiles the real implementation
with test-only shims, runs with ASan/UBSan and cleans its temporary directory.

## Still blocked and next act

No Darwin i386 link/load, real CarbonCore + M2 memory integration,
real application resource file, macOS resource xattr, guest execution,
SoundHack interface or Logic Studio 8 operation was tested.

The next bounded lot R2 should correct the actual Resource Manager public
read/write semantics, especially the disk persistence stub in save(), and
introduce differential persistent round-trip tests using the Apple TB40
contract. Do not announce success until disk bytes are verified.

Decision: R1 host PASS, guest integration and persistent writer NO GO.
