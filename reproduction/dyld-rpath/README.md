# DYLD-RPATH-01 — i386 dynamic Carbon witness

**Status (3 November 2026):** Phase A **PASS** on 5700X for exact source
transfers, Python syntax, three compiled/linked and inspected Mach-O i386
variants, and protected input integrity. Phase B guest runtime **NOT EXECUTED**.
No claimed rpath runtime fix. Branch: `work/dyld-i386-rpath-qualification`.
No production source, CMake, Ninja, CoreAudio/JACK, Carbon source, host system
installation, active Darling process, or shared prefix is modified by this lot.

## Why this test

PROJECT_STATE.md already records a genuine Carbon i386 guest that returns
code 0 and writes `D4RLING-CARBON-EVENT-I386-OK` through `@loader_path`,
including NORMAL/BYPASS and a missing-dylib negative control. Repeating it
without changing the variable is not research. The remaining bounded question
is whether the same program and same event implementation also work through
`@rpath` with a declared executable rpath.

The existing `reproduction/build-carbon-probe.py` and
`reproduction/run-guest.sh` from merged PR #7 are pinned by Git blob IDs
inside the new script; `fixtures/carbon-event.c` is also pinned. This
keeps the C logic and original test conditions constant.

## Variants (each in a new separate private subdirectory)

| Variant | Library LC_ID_DYLIB / exe LC_LOAD_DYLIB | Exe LC_RPATH | Runtime criterion |
| --- | --- | --- | --- |
| `loaderpath` | `@loader_path/libD4CarbonEvents.dylib` | absent | NORMAL/BYPASS both exit 0 + exact Carbon marker |
| `rpath` | `@rpath/libD4CarbonEvents.dylib` | `@executable_path` | NORMAL/BYPASS both exit 0 + exact Carbon marker |
| `rpath_no_lc` | `@rpath/libD4CarbonEvents.dylib` | absent | explicitly reject with `Library not loaded` mentioning `@rpath` and no marker |

This is intentionally a *comparative* diagnosis. Even if the positive rpath
case fails, there is no automatic dyld patch or retry with changed flags.
The stderr, exit codes and Mach-O load commands are evidence.

## Local prerequisites and scope

Target: Ryzen 5700X / Debian 13 WSL2 / user Deniel, no sudo.
Existing, independently reviewed (do not replace):
- Historical Carbon checkout:
  `/home/Deniel/d4rling-ui/d4rling-carbon-qualif`
- Existing i386 Ninja build tree (read inputs only):
  `/home/Deniel/d4rling-core/d4rling-build-i386`
- Existing **private experimental** installation (read inputs only):
  `/home/Deniel/d4rling-qt432-438-rRJ1fhT1/installation`
- Existing Python 3, clang-19, llvm-otool-19, llvm-lipo-19, linker
  produced by the build. No package installation or download from this script.
- The script and three pinned reproduction files must coexist in a
  `reproduction/` directory within a separately staged copy of the recovery
  kit. If missing, STOP; do not checkout/reset/fetch in the historical tree.

The source checkout may have nine important uncommitted modifications. The
script only reads it; compiled objects, Mach-O images and logs go to a newly
created directory under `/home/Deniel`, never to a build tree or prefix.
It preserves existing outputs on every outcome rather than removing evidence.

## Explicit source transfer, if needed

The 5700X's old protected checkout is not expected to contain this new
PR branch. Do **not** switch it or fetch branches into it. Instead stage
the five small source files below in a new private directory. Any transfer
from GitHub requires the user's **explicit action**, with progress and
volume disclosed. The total expected transfer is **21,312 bytes**, not a
dependency/model/package download.

| File | Commit source | Git blob SHA-1 | Bytes |
| --- | --- | --- | ---: |
| `reproduction/qualify-rpath-i386.py` | PR #8 `7186dbb31a7e209eb48d2ad9e8b23f2593bd5a93` | `18f9cb60c650c21d07e07cf67dea0d6f10867cc0` | 14,184 |
| `reproduction/build-carbon-probe.py` | merged PR #7 `e78f87723b3fd797abafaf7cd2b678c1b10ed4a9` | `90e5001a37aa27105ed5bd2c9ff4e74f47771787` | 3,158 |
| `reproduction/run-guest.sh` | same | `7b654180dae2184433b799e81ec06ff60146a180` | 1,532 |
| `reproduction/fixtures/carbon-event.c` | same | `67857751a333cbf1bb0f8ff1a8fd3ea101b239ab` | 1,508 |
| `reproduction/fixtures/atomic-bridge.h` | same | `eec3c84883b37ffbf6f976b4f92d37ccca762bff` | 930 |

All five must be checked against their Git blob hashes before execution.
No remote source is executed automatically by a GitHub comment or this PR.

## Stage A: compile + inspect (never executes guest)

From **Bash inside Debian 13 WSL2** and from the separately staged recovery
kit root containing `reproduction/qualify-rpath-i386.py`:

```sh
cd /home/Deniel/EXISTING_RECOVERY_KIT_COPY
python3 reproduction/qualify-rpath-i386.py \
  --source /home/Deniel/d4rling-ui/d4rling-carbon-qualif \
  --build /home/Deniel/d4rling-core/d4rling-build-i386 \
  --installation /home/Deniel/d4rling-qt432-438-rRJ1fhT1/installation \
  --output /home/Deniel/d4rling-dyld-rpath-01
```

`/home/Deniel/EXISTING_RECOVERY_KIT_COPY` is illustrative, **not** a
verified existing path; substitute the real directory if available.
The destination must **not already exist** and must be outside the source,
build, and installation paths. Do not run the example unedited.

Expected static marker `DYLD_RPATH_STATIC=PASS`, report at
`.../result.json`, and `DARLING_GUEST_RUNTIME=NOT_EXECUTED`.
If the linker rejects the rpath link, retain the error log and report
`BUILD_BLOCKED` instead of claiming that dyld was executed.

## Actual 5700X Phase A evidence — 2026-11-03

The user supplied the terminal transcript from Debian 13 WSL2, user
`Deniel`, Ryzen 5700X. All five explicit downloads completed and each
Git blob hash check returned `HASH_PASS`; there is no evidence of any
unrequested package/model download. The Python script passed `py_compile`
then built/inspected the three Mach-O i386 variants using existing tools.
The old protected checkout was used read-only.

Observed terminal markers:

```text
SOURCE=reproduction/qualify-rpath-i386.py BYTES=14184
HASH_PASS=reproduction/qualify-rpath-i386.py
HASH_PASS=reproduction/build-carbon-probe.py
HASH_PASS=reproduction/run-guest.sh
HASH_PASS=reproduction/fixtures/carbon-event.c
HASH_PASS=reproduction/fixtures/atomic-bridge.h
PYTHON_SYNTAX=PASS
WORKDIR=/home/Deniel/d4rling-dyld-rpath-01
STATIC_LOADERPATH=PASS
STATIC_RPATH=PASS
STATIC_RPATH_NO_LC=PASS
DYLD_RPATH_STATIC=PASS
DARLING_GUEST_RUNTIME=NOT_EXECUTED
INPUT_INTEGRITY=PASS
REPORT=/home/Deniel/d4rling-dyld-rpath-01/result.json
```

**Interpretation:** exact production/fixture source-transfer identity,
compiler/linker success, i386 Mach-O and `LC_RPATH` metadata gate,
and unchanged hashed inputs are **PASS**. The report and raw linker/load-command
logs remain in the private host directory, not committed. There was
**no guest runtime invocation**; the `@rpath` positive and negative cases
have not been judged from real dyld behavior, and historical RPC `-111`
is not tested.

Next stage, if explicitly authorized, is **a new invocation** with a
different `--output` and `--run`. Do not overwrite the Phase A directory;
do not patch dyld based only on its static metadata.

## Stage B: explicit isolated runtime (only after reviewing Stage A)

Re-run Stage A with a **different, new output path** and `--run` to enable
runtime. This compiles its own probe instead of editing Stage A artifacts.
Before starting anything, the runner checks that the private
`darling` binary embeds the private `darlingserver` path, and that the
server embeds the same private `mldr` loader path; mismatches block execution.
The pinned `run-guest.sh` then uses a new user/mount/PID/network/IPC/UTS
namespace, a fresh `DPREFIX`, stdin=/dev/null and bounded `timeout`.
It must not contact, restart, kill, mount over or install into the active
global Darling instance.

```sh
cd /home/Deniel/EXISTING_RECOVERY_KIT_COPY
python3 reproduction/qualify-rpath-i386.py \
  --source /home/Deniel/d4rling-ui/d4rling-carbon-qualif \
  --build /home/Deniel/d4rling-core/d4rling-build-i386 \
  --installation /home/Deniel/d4rling-qt432-438-rRJ1fhT1/installation \
  --output /home/Deniel/d4rling-dyld-rpath-01-runtime \
  --run --timeout 20
```

Accept `DYLD_RPATH_RUNTIME=PASS` only when both baseline modes, both
positive rpath modes and the negative rpath mode satisfy their separate
expectations. A failed baseline is `BLOCKED_BASELINE`, not proof that
`@rpath` is broken. A new `@rpath` mismatch is
`FAIL_RPATH_DIAGNOSTIC`, not a successful remediation.

## Distinct proof levels and required follow-up

1. C compiler/linker output and Mach-O `LC_ID_DYLIB`, `LC_LOAD_DYLIB`,
   `LC_RPATH` inspection: source/link qualification only.
2. Normal/BYPASS exited 0, exact marker and private namespace:
   qualified guest execution for **this one Carbon witness**.
3. The `rpath_no_lc` negative must fail with explicit dyld error.
4. A complete dyld, QuickTime 7, Logic Studio 8, JACK, CoreAudio, all syscalls
   and historical RPC `-111` are **not** qualified by this test.

Do not announce results before a 5700X execution transcript and locally
preserved reports. Do not merge this draft into master before reviewing the
actual case matrix, private installation layout and input integrity.


## 2026-11-03 — B1/B2/B3/B4/B5 runtime findings

Evidence was transcribed from the user's Debian 13 WSL2 shell, not run
by the GitHub connector. Reports remain private under
`/home/Deniel/d4rling-dyld-rpath-01-runtime`,
`/home/Deniel/d4rling-dyld-rpath-b2`,
`/home/Deniel/d4rling-dyld-rpath-b3`,
`/home/Deniel/d4rling-dyld-rpath-b4`, and
`/home/Deniel/d4rling-dyld-rpath-b5`.

| Probe | Host result | Evidence |
| --- | --- | --- |
| B1 baseline `@loader_path` direct NORMAL + BYPASS | PASS 2/2 | exit 0, Carbon marker |
| B1/B2 `LC_RPATH=@executable_path` | FAIL | exit 1, dyld library not loaded |
| B2 `@rpath` without `LC_RPATH` | expected failure | exit 1, missing dylib; exact marker not rechecked in B2 summary |
| B3 absolute guest `LC_RPATH=/Volumes/SystemRoot/...` | PASS | link, static contract, guest exit 0, exact marker and `RPATH successful expansion` |
| B4 `LC_RPATH=@loader_path` | FAIL | link/static PASS, guest exit 1, missing dylib, input integrity PASS |
| B5 guest i386 realpath of root, B4 and its own executable | FAIL/FAIL/FAIL | Mach-O i386 compile/link PASS, guest exit 0, `realpath()` returned NULL three times, input integrity PASS |

B5 did **not** capture `errno`. It demonstrates NULL results for exactly
three guest paths, not that all uses of Darwin `realpath()` fail.

The pinned source submodule in `reproduction/submodules.lock.json` is
`darlinghq/darling-dyld@63f667cf06d7ed59553adebb0c8d70a117135ac9`.
Its `src/ImageLoaderMachO.cpp` function `ImageLoaderMachO::getRPaths()`
uses `realpath()` as the only gateway for `@loader_path` and
`@executable_path` in LC_RPATH. This is a strongly supported explanation
for the B1/B2/B4 vs B3 differential. Why guest realpath fails remains open,
and the installed dyld binary's exact source provenance still needs checking.

## Unapplied candidate: bounded absolute loaded-path fallback

`reproduction/patches/dyld-rpath-realpath-fallback.patch`
is a **source-only experimental candidate**, NOT applied to production or
installed dyld. It has two narrowly limited hunks targeting exactly
`src/ImageLoaderMachO.cpp` at the above pinned commit:

- Preserve the successful realpath branch unchanged.
- Only when realpath fails, accept the absolute path of the *already-loaded*
  image (loader image or main executable), provided that path is not NULL,
  is absolute and fits strictly within `PATH_MAX` using `strlcpy`.
- Preserve both existing `context.allowAtPaths` restrictions. No new
  `DYLD_*` overrides, no global `realpath` interposition and no changes
  to direct `@loader_path` or absolute `LC_RPATH` handling.
- Accept that this changes fallback behavior for uncanonicalized loaded
  images. Treat symlink, path normalization, relative-image, missing-image,
  traversal, restricted-program and extremely long path cases as mandatory
  review/negative tests before adoption. No security claim is made yet.

**Static source-context proof only:** the two hunks' old context matches
exactly the pinned original `ImageLoaderMachO.cpp` (two independent
8-line hunks); a candidate text reconstruction was checked without
executing C++ compiler, patch application on a host repository, or runtime.

**Proposed next gate:** apply the patch only within a new, independently
owned copy of the pinned dyld source, verify via `git apply --check`
and a precisely scoped, explicitly approved private build, then run the
same B1–B4 positive/negative matrix with baseline and candidate in
otherwise identical namespace-isolated guest installations. Do not copy
libraries into the active `/opt` prefix or overwrite any historical
build tree. If a private dyld build or isolated guest installation cannot
be obtained, report BLOCKED, not a PASS. The `realpath()` subsystem
failure should be handled separately from this compatibility fallback.

PR #8 remains draft and unmerged until direct patched guest runtime
evidence and adversarial review are available.
