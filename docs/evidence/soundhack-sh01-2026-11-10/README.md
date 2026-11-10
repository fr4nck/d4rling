# SH01–SH03 — SoundHack 0.896 / Carbon i386 — 10 November 2026

**Evidence levels:** `SOURCE` (inspected upstream/project files), `TEST PASS`
(synthetic host tests), `BLOCKED` (not executable / not measured). This is **not**
a D4rling `RUNTIME PASS` or `AUDIO PASS`.

## Primary inputs — pinned and not redistributed

| Input | Version / source inspected | Finding |
|---|---|---|
| Application identification | https://www.soundhack.com/2007/08/soundhack-0-896-universal-binary/ | 0.896 (9 August 2007), Intel/PPC Universal Binary, CoreAudio playback/recording, OS X 10.4+ |
| Source/version confirmation | https://www.soundhack.com/2020/07/soundhack-source-code-on-github/ | Author explicitly identifies GitHub source as version 0.896, CarbonLib |
| Source snapshot | https://github.com/tomerbe/SoundHack/tree/df6f0bc89243b93573b391afa5ab371cce56ac95 | MIT LICENSE, copyright Tom Erbe; no vendor source copied |
| Audio routing | `SoundFile/Play.c` blob `b05e1757122f729bf2de3a149e1e9572dc484238` | `GetPlayerType` selects QuickTime or PortAudio according to file type/packing; `StartQTPlay`, `StartPAPlay` separate |
| Application GUI/main | `ToolBox/SoundHack.c` blob `634ba7a49132b4643d3a3dc8de2da2e1c91209b7` | Includes QuickTime Movies/Components and Carbon-related helpers; no guest GUI test |
| D4rling QuickTime | `src/frameworks/QuickTime/src/QuickTime.c` blob `c0ede69d0593d8aed6cad3eef726276acb40413a` | Explicit stub bodies still present in the SoundHack QuickTime playback call path |

Upstream sources are MIT licensed, but that does **not** prove executable
redistribution permissions. The official archive currently points to
`https://tre.ucsd.edu/wordpress/wp-content/uploads/2016/12/SH896.dmg_.zip`;
its bytes, SHA-256, embedded executable architecture and import set **were not
obtained** (network unavailable in the inspection container). No Mac binaries,
SDK or sample media are committed.

## Source-to-source playback matrix — NOT binary imports

| SoundHack path | Direct API(s) | D4rling `QuickTime.c` at inspected blob |
|---|---|---|
| Open movie | `OpenMovieFile`, `NewMovieFromFile`, `CloseMovieFile` | `EXPLICIT_STUB` (3/3) |
| Configure playback | `GetMovieTimeScale`, `SetMovieActiveSegment` | first bounded implementation; second `EXPLICIT_STUB` |
| Control/play | `NewMovieController`, `MCDoAction`, `StartMovie` | `EXPLICIT_STUB` (3/3) |
| Poll/time | `MoviesTask`, `IsMovieDone`, `GetMovieTime` | `EXPLICIT_STUB` (3/3) |
| Stop/dispose | `StopMovie`, `DisposeMovieController`, `DisposeMovie` | first two `EXPLICIT_STUB`; last bounded implementation |

**12 of 14** named QuickTime entry points contain explicit `STUB` markers in
the inspected D4rling implementation; 2 have non-stub implementations.
This list is **only** the `Play.c` playback call chain, not a complete import
inventory for SoundHack. `InitializePlay()` calls `Pa_Initialize()`; the
PortAudio path uses `Pa_OpenDefaultStream`, `Pa_StartStream`, classic file
`PBRead`, `SetCurrentA5` and memory/IO callbacks. Those guest APIs and the
actual Intel binary import table have **not** been reconciled against D4rling.

**Reproducer / handoff to QuickTime owner:** inspect the entries above in the
actual `QuickTime.c`, then execute the `quicktime_stubs.py --strict` command
from the fixture README. Expected source exit **2** with explicit stub markers.
`StartQTPlay` in the pinned SoundHack `Play.c` checks the initial
`OpenMovieFile` error but then continues even when no movie is instantiated;
it returns `true` without a final playback success check. Current D4rling
stubs return `NULL` with generic declarations. **Potential false-success and
ABI risk**, not a measured guest crash. QuickTime's owning thread should
first qualify typed error/handle contracts (especially `OpenMovieFile` and
`NewMovieFromFile`) and a controlled failure path before any positive result.
No QuickTime production patch is proposed or published in this lot.

## SH02 — observed host tests and independent witness

- Environment: isolated Linux execution container; Python 3.13.5,
  `file`, `llvm-objdump` available; no D4rling guest installation.
- `python3 -m unittest -v test_macho_audit.py test_quicktime_stubs.py`:
  **27/27 PASS**. Includes FAT i386 vs PPC selection, endian / x86_64,
  valid nlist import/export and by-name comparison, missing symbol (`exit 2`),
  missing provider/symtab (`exit 3`), malformed magic/load commands/FAT
  tables/overlaps/string offsets, and stub marker counterexamples.
- `file witness-i386.macho` independently recognized the generated fixture
  as **Mach-O i386 executable**. `file witness-universal.macho` recognized
  **Mach-O universal (PPC/i386)**. `llvm-objdump --macho --private-headers`
  independently identified the generated i386 `LC_LOAD_DYLIB` QuickTime path,
  `LC_SYMTAB`, `nsyms 3`. These are **generated fixtures**, not SoundHack.
- Source evidence from GitHub API was reviewed against the current master;
  that reading is distinct from tests run in this container.
- GitHub Actions: **not used**; no paid runners or CI modifications.

Reproduce fixture tests using the command in
`reproduction/fixtures/soundhack-i386/README.md`. No additional packages.
The parser deliberately refuses oversized, malformed, missing-slice and
symbol-inconclusive inputs rather than converting them into false PASS values.

## Five application milestones

| Milestone | Status | Missing proof |
|---|---|---|
| SH-LOAD | `BLOCKED` | Actual authorized i386 executable and coherent D4rling runtime |
| SH-GUI | `BLOCKED` | Carbon GUI rendered by that executable |
| SH-FILE | `BLOCKED` | Real WAV/AIFF opened under guest |
| SH-DSP | `BLOCKED` | Real SoundHack DSP output |
| SH-AUDIO | `BLOCKED` | Real audio output observed and verified |

**Next concrete gate:** obtain/hash the original authorized 0.896 executable
without redistributing it, run `macho_audit.py --arch i386` on it, and map
its real dylib/symbol requirements onto D4rling's *coherent build*.
In parallel, the QuickTime owner can use the 14-call source witness to target
an honest failure path or typed implementation. Neither requires a new D4rling
branch, changes to Logic audio or the user to start the 5700X now.
