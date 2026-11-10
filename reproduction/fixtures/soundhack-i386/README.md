# SoundHack 0.896 — SH01–SH13 static, archive and host witnesses (i386 target)

These fixtures use **Python 3 standard-library** host tools. The static auditors
read files only; SH07 explicitly creates one new output WAV and compiles pinned
upstream FFT code in a private temporary directory. No Apple SDK,
SoundHack executable, bundled media, GUI, audio driver, Linux guest or
additional Python package is included. License for these new tests/tools: GPL-3.0-or-later (D4rling).

## Scope

- `macho_audit.py`: bounds-checked thin/FAT Mach-O (32/64, endian) reader;
  reports selected slice, `LC_LOAD_*` dylibs, `LC_SYMTAB` **nlist** undefined
  and external defined names. Flat images compare by name; two-level images
  also check `n_desc` import ordinals against matching provider `LC_ID_DYLIB` IDs.
- `quicktime_stubs.py`: a source-pattern witness for **14 specific QuickTime
  functions** used by `SoundFile/Play.c` in Tom Erbe's SoundHack source at
  `tomerbe/SoundHack@df6f0bc89243b93573b391afa5ab371cce56ac95`.
- `gestalt_startup_gate.py`: extracts the real current CarbonCore `Gestalt()`
  function and executes it in an isolated **host C++ mock** to check SoundHack's
  Carbon and system-version gates. Requires an existing C++17 compiler.
- `test_*.py`: positive, mutation/negative, malformed and CLI checks. Synthetic
  Mach-O samples are generated in temporary directories; no fake SoundHack
  executable is distributed.

This is not a dyld bind/opcode resolver. Reexports, dyld bind opcodes, true symbol binding, lazy binding and
application run-time resolution are **not** proven. Import ordinals and weak
reference flags are parsed, but do not certify actual symbol binding. Even an ordinal/ID/name match does not mean a callable ABI or
working implementation. Files with `LC_DYLD_INFO[_ONLY]` are deliberately inconclusive
in strict symbol comparison. Explicit `STUB` and missing definitions are
reported separately; a missing `STUB` string never certifies functionality.

## Reproduction from the D4rling checkout (Linux Python 3)

```sh
python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 -p 'test_*.py' -v
python3 reproduction/fixtures/soundhack-i386/quicktime_stubs.py \
  --quicktime-source src/frameworks/QuickTime/src/QuickTime.c --strict
```

The second command is **expected to exit 2** while the listed QuickTime entry
points are explicit stubs; JSON still identifies each function. Exit 3 means
missing/ambiguous source entries or unreadable input; exit 0 means no marker
was found for any listed function, **not** a playback PASS.

With a separately obtained **legitimate** SoundHack 0.896 application bundle:

```sh
python3 reproduction/fixtures/soundhack-i386/macho_audit.py \
  --consumer '/authorized/path/SoundHack.app/Contents/MacOS/SoundHack' --arch i386
```

A binary belonging to a **coherent, authorized** D4rling installation may be
inspected separately using repeatable `--provider /path/to/QuickTime` and
`--provider /path/to/lib...` arguments. For bounded static checks, add `--strict`:
exit 0 = bounded nlist comparison with no mandatory missing symbol in the supplied set;
exit 2 = unresolved mandatory symbol(s); exit 3 = invalid/incomplete or inconclusive
inputs. Missing weak references are reported separately as optional. Two-level
imports require a matching provider `LC_ID_DYLIB` install name; without it,
strict mode is inconclusive, not a false success. Absence of
unresolved names is **not** runtime success. Default output is JSON on stdout.
The binary inspection limit is 128 MiB per input, without extraction or write.

## Provenance and boundaries

- Primary app source: https://github.com/tomerbe/SoundHack (MIT; no source copied).
- Official original freeware distribution: https://www.soundhack.com/freeware/
  (released in 2007 as Intel/PPC Universal Binary). Redistribution rights of
  the executable are not established by the source license.
- Qualification, exact source evidence, blocker and test environment:
  `docs/evidence/soundhack-sh01-2026-11-10/README.md`.
- Changes here do **not** modify QuickTime, Carbon, BSD, dyld, CoreAudio,
  the original Logic engine, CI or `experiments/petite-victoire/`.

## SH04 — two-level ordinal qualification (2026-11-10)

The `macho_audit.py` tool now classifies the ordinal of each imported nlist
symbol and rejects a same-name match from the **wrong provider**. Special
ordinals, common/prebound, indirect definitions and incomplete provider
identity remain explicitly inconclusive. `LC_DYLD_INFO` bind opcodes are not
resolved. The independent source references, 12 new negative/positive cases
(**39 total host tests**) and exact limitations are in
`docs/evidence/soundhack-sh01-2026-11-10/SH04-ordinal-qualification.md`.

## SH05 — host startup gate (2026-11-10)

The source-level `CapabilityCheck()` of SoundHack requires Carbon version
(`'cbon'`) and system version (`'sysv'`) before `MainLoop`. This bounded
**host-only** witness tests D4rling's real `Gestalt()` implementation against
the two thresholds without altering production code:

```sh
python3 reproduction/fixtures/soundhack-i386/gestalt_startup_gate.py \
  --gestalt-source src/frameworks/CoreServices/src/CarbonCore/Gestalt.cpp \
  --expected-blob dffdd4cb26c7f191c6e2b5fc97298c79a8d75dff
```

On the pinned source the command is **expected to exit 2** and report
`HOST_STARTUP_GATE_BLOCKED` (`cbon` unimplemented, `sysv` overwritten by
`sysa` fallthrough). If a concurrent owner changes Gestalt.cpp, the pinned
run fails closed with exit 3 until its source is requalified. Never present
the simulated C++ host result as SoundHack guest execution, ABI, GUI or audio.
See `docs/evidence/soundhack-sh01-2026-11-10/SH05-startup-gestalt.md` for
actual compiler output, test provenance and CarbonCore owner handoff.

## SH06 — original Tom Erbe FFT numerical test (host only)

The new [fft_host_probe.py](fft_host_probe.py) compiles the **unaltered**
MIT-licensed upstream SoundHack 0.896 Math/FFT.c (and FFT.h) from a separately
authorized, pinned source checkout. Both Git blobs are checked before
compilation. The script executes FFT and RealFFT against an independent
double-precision direct DFT oracle, then performs a two-tone spectral notch
with the original RealFFT. No Apple SDK, SoundHack binary, media, guest or
audio device is required; no automatic network access or installation occurs.

    SOUNDHACK_MATH_DIR=/authorized/path/SoundHack/Math \
      python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 -p 'test_fft_host_probe.py' -v
    python3 reproduction/fixtures/soundhack-i386/fft_host_probe.py \
      --source-dir /authorized/path/SoundHack/Math

On the observed pinned source: **24/24** FFT numerical cases and the spectral
notch passed on host GCC 14.2 and Clang 17, with **13/13** unit checks including
original-code mutations. Without SOUNDHACK_MATH_DIR, the unit suite runs the
local negative checks and skips the 3 original-source-dependent cases.
Exit 0 = bounded HOST_DSP_PASS, 2 = numerical FAIL, 3 = inconclusive.
**No SoundHack guest runtime, audio file, Darwin i386 ABI or audio-output PASS.**
See [SH06 evidence](../../../docs/evidence/soundhack-sh01-2026-11-10/SH06-host-fft.md).

## SH07 — WAV file processing with original SoundHack FFT (host only)

The new [wav_fft_render.py](wav_fft_render.py) reuses SH06's upstream source
hash validation, compiles the **unaltered** original SoundHack Math/FFT.c on
the host, and filters an actual **mono PCM16 WAV** with RealFFT (periodic
Hann windows, quarter-frame hop, overlap-add normalization). It never
fetches/installs third-party software, plays sound, or edits a D4rling
framework. The test sources are NOT redistributed in this repository.

Example, from the canonical checkout with the already-authorized original
SoundHack Math source directory available:

    export SOUNDHACK_MATH_DIR=/authorized/path/SoundHack/Math
    python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 -p 'test_wav_fft_render.py' -v
    python3 reproduction/fixtures/soundhack-i386/wav_fft_render.py \
      --math-dir "$SOUNDHACK_MATH_DIR" --input /authorized/input.wav \
      --output /authorized/NEW-output.wav --notch-hz 3000

Outputs are exclusive-create only: an existing file or symlink is never
overwritten. Only 16-bit mono PCM WAV is supported, with explicit size,
sample-count and frequency bounds. Exit 0 = **HOST_WAV_RENDERED**, exit 3 =
**INCONCLUSIVE**; no other status implies SoundHack GUI, guest, real playback
or audio driver compatibility. With pinned original Math/ source: **18/18
SH07 unit tests PASS**; full SoundHack fixture suite: 79 cases, 78 PASS and
1 SKIP (separate SH05 checkout-path qualification).

The WAV example used independent 750 Hz / 3,000 Hz tones, keeping 750 Hz and
reducing 3,000 Hz approximately 61 dB. See [SH07 evidence](../../../docs/evidence/soundhack-sh01-2026-11-10/SH07-host-wav-render.md).

## SH08 — compile unchanged FFT source to a Darwin i386 Mach-O object

[fft_darwin_i386.py](fft_darwin_i386.py) uses existing Clang and the **pinned,
unaltered** upstream SoundHack Math/FFT.c and Math/FFT.h to generate a temporary
`i386-apple-darwin9` `MH_OBJECT` using `-nostdinc` and **prototype-only**
math declarations. No Apple SDK, host headers, D4rling installation, dynamic
libraries, binary downloads or audio device are required. It reuses the
existing `macho_audit.parse()` and `fft_host_probe.require_pinned()` rather
than adding a second Mach-O parser or source archive.

It checks target ILP32 widths (32-bit pointer, long and int), the i386 Mach-O
header, six defined original symbols and four unresolved symbols. The source
is never modified; by default the temporary object is deleted. To retain it,
pass `--output /authorized/new/file.o` (exclusive creation; never overwrite).

From a canonical D4rling checkout with an authorized original SoundHack Math
directory and an already installed Clang 17 with Darwin i386 support:

```sh
SOUNDHACK_MATH_DIR=/authorized/path/SoundHack/Math \
  python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 \
  -p 'test_fft_darwin_i386.py' -v
python3 reproduction/fixtures/soundhack-i386/fft_darwin_i386.py \
  --source-dir /authorized/path/SoundHack/Math
```

Observed **20/20 SH08 tests PASS** (including compilation against the real
source and negative controls); combined SH01–SH08 **99 cases, 98 PASS, 1 SKIP**.
Without external upstream source, SH08 gives **16 PASS / 4 SKIP**. Codes:
`0` = `TARGET_OBJECT_PASS`, `2` = target contract failure, `3` =
inconclusive. **This does not link an i386 Mach-O dylib, execute in the
D4rling guest, or demonstrate SoundHack/Logic audio.** The available
`ld64.lld` explicitly rejects `-arch i386`.

Evidence: [SH08 Darwin i386 object](../../../docs/evidence/soundhack-sh01-2026-11-10/SH08-darwin-i386-object.md).

## SH09 — verify i386 relocations, globals and real linker refusal

[**i386_link_gate.py**](i386_link_gate.py) consumes an existing SH08
Mach-O i386 object (no recompilation or copying of SoundHack sources).
It reuses `macho_audit.parse` and independently installed
`llvm-objdump --macho --reloc` to verify relocations, symbols,
target architecture and the exact reference SHA-256. A tiny
temporary **Darwin i386 object** supplies SoundHack's application
globals `Pi` and `twoPi` only; `sin` and `sinf` remain genuine
external dependencies. The `ld64` selected by `--ld64` is attempted
in a private temporary directory, and any output is checked for real
Mach-O i386 `MH_DYLIB` structure. A positive exit without a valid
binary is a failure; no binary is retained. For a static input-only
check, use `--no-link`.

From the canonical repository with an already-built SH08 object:

```sh
SH08_I386_OBJECT=/authorized/path/fft-i386.o \
  python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 \
    -p 'test_i386_link_gate.py' -v
python3 reproduction/fixtures/soundhack-i386/i386_link_gate.py \
  --object /authorized/path/fft-i386.o --no-link
python3 reproduction/fixtures/soundhack-i386/i386_link_gate.py \
  --object /authorized/path/fft-i386.o \
  --ld64 /authorized/canonical/build/path/to/ld64
```

**SH09 21/21 tests PASS** on the isolated host with the original SH08
object available (without it, 19 PASS / 2 SKIP). Object: 48 relocations,
21 validated pairs and four imports; the globals companion resolves two
names, leaving `sin` and `sinf`. The available `ld64.lld` 17 returns
`missing or unsupported -arch i386` (**exit 3,
`LINK_TOOLCHAIN_BLOCKED`**, NOT a link PASS).
The `--no-link` result `LINK_INPUTS_READY` (exit 0) is **only static**.
A real valid linked candidate with unparsed dyld-info stays inconclusive.
No guest, app, math library, audio or Logic engine was tested.

Full [SH09 evidence](../../../docs/evidence/soundhack-sh01-2026-11-10/SH09-link-inputs.md).

## SH10 — deterministic Darwin i386 static archive, cctools-port handoff

[darwin_archive_gate.py](darwin_archive_gate.py) accepts a **verified SH08
i386 Mach-O MH_OBJECT** (default SHA-256
`c5e059e4ce39e2f1b95a925d0eebcac09ded0c36748db0e422b1bca3b7ee1409`)
and reuses SH09's object/globals and Mach-O verification. It compiles only
the `Pi`/`twoPi` companion, then runs the already installed
`llvm-ar --format=darwin rcD`. The result is an archive with exactly two
i386 object members and a Darwin `__.SYMDEF` index, NOT a dylib or program.

The verifier independently reopens both members, checks their nlist symbol
contracts and original bytes, and accepts only LLVM Darwin's documented
alignment bytes (`0x0a`) at the end of each member. After the constants
are accounted for, `_sin`/`_sinf` remain unresolved. SH10 performed an
identical two-build comparison, and the real SH08 source object produced
an archive of **4 000 bytes**, SHA-256
`c11833539630b5aa70d6d63a44d4063eb11a12f0f316884094b0b64f38707169`.

With a legitimate SH08 object in an isolated Linux environment:

```sh
export SH08_I386_OBJECT=/authorized/path/original-sh08-target.o
python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 \
  -p 'test_darwin_archive_gate.py' -v
python3 reproduction/fixtures/soundhack-i386/darwin_archive_gate.py \
  --object "$SH08_I386_OBJECT" --output /authorized/new/FFT-i386.a
```

The optional `--output` **exclusively creates** a new archive (no overwrite).
The default keeps the archive temporary. For a separately qualified,
already-built cctools-port `ld64`, pass `--ld64 /authorized/canonical/ld64`.
SH10 passes the archive to the real linker with `-all_load`, and rejects
success without a valid Mach-O image; opaque dyld bind info is INCONCLUSIVE.

Host tests: **20/20 SH10 PASS** including negative/fake linker cases and
the authentic SH08 object; together with SH09, **41/41 PASS**. The only
linker available in this environment is `ld64.lld` 17, which still rejects
`-arch i386` (`LINK_TOOLCHAIN_BLOCKED`, exit 3). No native cctools-port
linking, guest execution, Carbon GUI, audio device or Logic compatibility
is claimed. The canonical cctools-port submodule is pinned at
`d9456c221e1f462e17c0b3297748bc089d5a861e`.
Evidence: [SH10 static archive qualification](../../../docs/evidence/soundhack-sh01-2026-11-10/SH10-darwin-static-archive.md).

## SH11 — pinned linker, fail-closed dynamic library export (host only)

The existing [darwin_archive_gate.py](darwin_archive_gate.py) now accepts
`--ld64-sha256 HEX` (SHA-256 pin of the installed linker, checked **before**
running it) and `--linked-output /authorized/new/libSoundHackFFT_i386.dylib`
(exclusive creation **only after** `verify_linked()` accepts a real
i386 `MH_DYLIB`). A matching linker SHA is a binary identity check, **not**
proof of source provenance. A linker exit code of zero, a filename, or an
opaque `LC_DYLD_INFO` is never a guest/runtime PASS. Existing files and
symlinks are protected; ambiguous or failed links create no dylib.

SH11 adds [test_sh11_cctools_handoff.py](test_sh11_cctools_handoff.py):
**17/17 new host tests PASS**; SH09–SH11 **58/58 PASS** on Linux/Python
3.13.5. Some tests mock `verify_linked()` to exercise **only destination
delivery I/O**; those synthetic cases are never evidence of an actual link.

Real SH08 object + pinned `ld64.lld` 17: **`LINK_TOOLCHAIN_BLOCKED`**,
`missing or unsupported -arch i386`, exit 3, **no linked output**. Archive
replay is `DARWIN_ARCHIVE_PASS`, SHA-256
`c11833539630b5aa70d6d63a44d4063eb11a12f0f316884094b0b64f38707169`.
A true cctools-port `ld64` executable is still missing locally; the network
could not retrieve the canonical pinned submodule. No i386 dylib/guest/audio.

Run the host tests from the repository root (no network):

```sh
python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 \
  -p 'test_sh11_cctools_handoff.py' -v
```

To use a previously compiled, *canonical* cctools-port i386 `ld64`, supply
its absolute path, exact measured SHA-256 and a **nonexistent** output path;
do not reuse an unrelated linker or combine builds. The actual link remains
conditional, not qualified here. See [SH11 evidence](../../../docs/evidence/soundhack-sh01-2026-11-10/SH11-cctools-handoff.md).

## SH12 — offline link replay from authentic SH10 ZIP (no source rebuild)

The [sh12_cctools_replay.py](sh12_cctools_replay.py) utility reconstructs
the original **3,236-byte SH08 FFT Mach-O i386 object** from the already
distributed SH10 ZIP without redistributing or recompiling SoundHack sources.
It validates archive/FFT SHA-256 fingerprints, the MIT notice, ZIP integrity,
and Darwin ar alignment; it reuses the existing SH09/SH11 Mach-O and link gates.

The caller designates **one existing canonical build root**. SH12 looks only
in bounded cctools-port ld64 paths, rejects non-native ELF binaries, scripts,
symlinks and ambiguous candidates, records the candidate SHA-256, then invokes
the unchanged SH11 fail-closed verifier. SHA-256 proves a selected executable's
identity, **not** its source provenance. No hidden network or install action.

From the D4rling checkout (Bash, Linux/WSL):

    python3 reproduction/fixtures/soundhack-i386/sh12_cctools_replay.py \
      --sh10-package /authorized/SH10/d4rling-SH10-archive-i386.zip \
      --build-root /authorized/canonical/build-core-i386 \
      --linked-output /authorized/NEW/libSoundHackFFT_i386.dylib

The output pathname must not exist. Exit **0** only means the SH11 verifier
has qualified a linked Mach-O i386 *structure*. Exit **2** = contract failure;
**3** = missing/inconclusive tool or linked result. This is **never** a proof
of SoundHack guest start or real audio.

On the isolated test host the actual SH10 ZIP was verified and SH08 extracted,
but **no cctools-port ld64 was available**: status LINKER_ABSENT (exit 3).
SH09-SH12 full host suite: **77/77 PASS**, 0 SKIP with actual SH08/SH10 artifacts.
SH12 alone without external SH10 ZIP: **11 PASS, 8 SKIP**. See
[SH12 evidence](../../../docs/evidence/soundhack-sh01-2026-11-10/SH12-offline-cctools-replay.md).

## SH13 — detect the actual cctools-port ld64 output directory

The pinned cctools-port `cctools/ld64/src/ld/Makefile.am` declares
`bin_PROGRAMS = ld`. SH12 previously searched `.../ld64/src` but not
`.../ld64/src/ld`; a correct linker build could be falsely reported absent.

The existing bounded candidate search now also checks
`.../ld64/src/ld/ld` and `.../ld64/src/ld/.libs/ld` (Libtool may
leave a shell wrapper at the first path). Historical layouts remain supported,
and existing ELF, symlink, ambiguity and hash checks are unchanged. It
does **not** compile or install cctools and does **not** identify any linked
SoundHack binary.

```sh
python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 \
  -p 'test_sh13_ld64_build_paths.py' -v
```

**8/8** focused path-discovery tests PASS; SH09–SH13 **85/85 PASS** with the
pinned SH08 object and SH10 ZIP available for the larger suite. SH13's inert
ELF test fixtures are never run as linkers. A real i386 Mach-O link remains
blocked until an authorized, canonical cctools-port linker is built and used.
See [SH13 evidence](../../../docs/evidence/soundhack-sh01-2026-11-10/SH13-ld64-build-path.md).
