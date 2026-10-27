# Mach-O i386 loader smoke fixture (host-only generator)

This directory supplies an independent, deterministic i386 Mach-O executable
for testing the Darling **binary loader**, not the Darwin C library.

## Host regression (no Darling or Apple SDK)

On any Linux development host with Python 3 and optionally the `file` tool:

```sh
sh tests/regressions/macho-i386/run.sh
```

The runner executes **54 Python `unittest` cases** (17 generator, 13 symbol-analysis,
16 source-contract and 8 pinned-fetch integrity checks), generates two one-page Mach-O i386 files in a
temporary directory, optionally checks the format with `file`, and removes
the temporary files. It never starts Darling or executes the guest
instructions on the host. No network, compiler, linker, root privilege, SDK or
submodule is required.

Expected summary:

```text
HOST_TESTS=PASS
GUEST_EXECUTION=NOT_ATTEMPTED
```

## What is checked

- Little-endian 32-bit Mach-O header, i386 CPU and executable type.
- `__PAGEZERO` and `__TEXT` mappings, single `__text` section.
- `LC_UNIXTHREAD` with the intended EIP at `base + 0x200`.
- The embedded Linux i386 `write` and `exit` syscall arguments.
- A deterministic marker, alternate base, and rejection of bad VM bases.
- CLI refusal to overwrite existing files or symlinks.

The fixture uses `int 0x80` with **Linux**, not Darwin, syscall numbers.
It does **not** validate dyld, 32-bit libSystem, Carbon, CoreAudio, or QuickTime.
Its direct syscall path intentionally bypasses Darling's Darwin API layer.

## Optional guest smoke test (separate, NOT run by CI)

Only on a machine with a working Darling installation and an **already
initialized, disposable test prefix**:

1. Verify that `DPREFIX` selects the disposable prefix, **not** the default
   `~/.darling`, any production/original prefix, or another user's prefix.
2. Generate the fixture using `python3 -B
   tests/regressions/macho-i386/generate.py --output
   "$DPREFIX/usr/local/bin/macho-i386-smoke"` after verifying that this
   destination does not already exist. The generator refuses to overwrite.
3. Use the installed Darling launcher: `DPREFIX="$DPREFIX" timeout 12s
   darling exec "$DPREFIX/usr/local/bin/macho-i386-smoke"`.
4. Confirm the **exact marker** `D4RLING_I386_MACHO_OK` and exit status
   **43**. Keep launcher output, build version and an original-runtime
   integrity check with the report.
5. Inspect any lingering experimental `darlingserver`/`mldr` processes.
   Clean up only if their executable, owner and test-prefix identity are
   verified. Never stop the original runtime by PID guesswork.

Guest invocation is deliberately manual because `darling exec` can spawn
background launchd/mldr descendants even after the foreground command exits.
These steps must not be enabled by default in GitHub Actions.

## Bounded i386 linker-symbol inventory (read-only)

The optional `symbol_providers.py` helper examines an existing linker-error
log and locally compiled build artifacts. It requires `llvm-lipo-19` and
`llvm-nm-19` **only when running this actual scan**, not for the 30 unit tests.

Example on a machine with the QT-110 build tree and linker log:

```sh
LOG=/path/to/qt110/link-1.log
BUILD=/path/to/d4rling-build-i386
OUT=/path/to/new-i386-symbol-report.json
python3 -B tests/regressions/macho-i386/symbol_providers.py \
  --link-log "$LOG" --build-dir "$BUILD" --output "$OUT"
```

The scanner reads ld64's quoted unresolved symbols, enumerates candidate
`.a`/`.dylib` artifacts under `build/src`, verifies each candidate has an
i386 slice, and records global definitions in a JSON report. Fat files are
thinned into a temporary location for `llvm-nm`, without changing their
source. A target report must not already exist.

The default scan is bounded to 200 candidate artifacts, and records
`truncated`, failures and `no-i386-slice` outcomes. A symbol appearing in
a candidate does **not** prove the archive is self-contained, that the
library's link order is correct, or that runtime calls work. Symbols listed
as not found are only unlocated **within the scanned candidate set**.

The new candidate-name filter explicitly includes `libmalloc`, a separate
Darling submodule that was outside the earlier QT-111 filename selection.
Actual provider coverage on the 5700X has **not been rerun** with the new
tool; no QT-111 numbers are reinterpreted as new scan results.


## Source-level explanation of the QT-110 static i386 link failure (QT-112)

Inspection of the **fork-pinned submodules** (not the latest unpinned
upstream trees) explains the missing three symbols:

- `__libkernel_functions`: C global `_libkernel_functions` is defined
  in `libsyscall/wrappers/_libkernel_init.c` (Darling XNU pin
  `fa29287aa2f0115271e091f1031f53c9e024005d`). That file is
  assigned to `syscall_dynamic_sources` and the object target
  `libsyscall_dynamic`. The `system_kernel_static32` archive instead
  lists `libsyscall_32`, `libsyscall` and `emulation_dyld`, without
  `libsyscall_dynamic`. The normal dynamic `system_kernel` does list
  `libsyscall_dynamic`. This explains why trying to link the static
  archive alone leaves the initializer state unresolved; it does not
  establish that Darling lacks the symbol.
- `_malloc` and `_free`: C functions `malloc` and `free` exist
  in `src/malloc.c` in the pinned `darling-libmalloc` source
  (`a57991e2651226a675654bd96e5d9ab6bec288c5`). Its CMake build
  adds this file to the `system_malloc` circular dynamic target, not
  to a standalone kernel static archive.
- The pinned `darling-Libsystem` CMake source
  (`08df454b6eb0df9400aa4c39839a7efd6efd2c3c`) expressly
  reexports `system_malloc` and `system_kernel` via `libSystem.B.dylib`.

Therefore the next **actual** i386 validation should close the dynamic
`system_kernel` + `system_malloc` + `libSystem` dependency graph,
rather than artificially declaring the static kernel archive a complete
application library. The circular build may still have further missing
dependencies; the source inventory cannot prove a successful i386 build.

Pinned source inspection is recorded as analysis, **not** a fresh
5700X execution, build, ABI test or demonstration of 32-bit libSystem.

### Recheck the pinned source contract offline

On an existing checkout containing the initialized XNU, Libsystem and
libmalloc submodules, the following read-only command validates nine
specific source relationships and can create a reproducible JSON report:

```sh
python3 -B tests/regressions/macho-i386/source_contract.py \
  --checkout /path/to/d4rling-checkout \
  --output /path/to/new-qt112-source-contract.json
```

The JSON target must not already exist. This source-only check requires
Python 3 but no compiler, no runtime and no linker; incomplete submodules
fail explicitly rather than being treated as evidence that definitions
are absent.

References at pinned commits:
- [Darling XNU kernel build](https://github.com/darlinghq/darling-xnu/blob/fa29287aa2f0115271e091f1031f53c9e024005d/darling/src/libsystem_kernel/CMakeLists.txt)
- [Darling XNU syscall object-group assignment](https://github.com/darlinghq/darling-xnu/blob/fa29287aa2f0115271e091f1031f53c9e024005d/libsyscall/CMakeLists.txt)
- [Darling XNU kernel initializer](https://github.com/darlinghq/darling-xnu/blob/fa29287aa2f0115271e091f1031f53c9e024005d/libsyscall/wrappers/_libkernel_init.c)
- [libmalloc CMake](https://github.com/darlinghq/darling-libmalloc/blob/a57991e2651226a675654bd96e5d9ab6bec288c5/CMakeLists.txt)
- [libmalloc C functions](https://github.com/darlinghq/darling-libmalloc/blob/a57991e2651226a675654bd96e5d9ab6bec288c5/src/malloc.c)
- [libSystem reexports](https://github.com/darlinghq/darling-Libsystem/blob/08df454b6eb0df9400aa4c39839a7efd6efd2c3c/CMakeLists.txt)


### GitHub-only verification of the **actual pinned sources**

The source-contract unit tests use deliberately small synthetic CMake
inputs. A **separate** GitHub Actions job, `pinned-source-contract`,
downloads six precise files from the fork's pinned XNU, libmalloc and
Libsystem commits, checks each against its expected Git blob SHA, then
runs `source_contract.py` on those files. No downloaded code is
executed. The job does not build Darling or need the 5700X.

This verification uses network access on the GitHub runner; if it fails to
download, it reports an incomplete check rather than fabricating a pass.
The regular host-only test job remains fully offline.

To reproduce independently, in a temporary workspace:

```sh
WORK=$(mktemp -d)
python3 -B tests/regressions/macho-i386/fetch_pinned_sources.py \
  --output-dir "$WORK/pinned"
python3 -B tests/regressions/macho-i386/source_contract.py \
  --checkout "$WORK/pinned" --output "$WORK/source-contract.json"
```

The script refuses a pre-existing output directory and fails on mismatched
Git blob hashes. These source-code checks cannot establish the availability
of i386 build artifacts, dynamic linking or a working runtime. The corresponding
production build and test of `libSystem` i386 still require the 5700X.

## Earlier evidence (not a fresh run of this fixture)

The local QT-106 through QT-111 qualification series on Debian 13 / WSL2,
dated 2026-10-27, recorded:

| Lot | Observed result | Scope |
| --- | --- | --- |
| QT-106 | x86_64 autonomous Mach-O marker; exit 42 | Linux direct syscalls |
| QT-107 | native Linux ELF32 marker; exit 37 | Linux kernel ELF32 support |
| QT-108R | independent hand-built i386 Mach-O marker; exit 43 | Loader, Linux direct syscalls |
| QT-108R | x86_64 dynamically linked Mach-O marker; exit 42 | dyld path, no Darwin API call |
| QT-109 | x86_64 Mach-O `getpid`, `write`, `_exit`; exit 47 | First Darwin libSystem API execution |
| QT-110 | i386 `libsystem_kernel_static32.a` thin slice, 870 members, `_getpid` and `_write` defined | Static objects, not full dynamic runtime |
| QT-111 | 36/39 missing symbols had a possible provider among 17 examined i386 libraries | Bounded dependency search |

The QT-111 bounded scan did not locate `__libkernel_functions`, `_malloc`
or `_free` among its selected libraries. This is **not evidence that the
symbols are absent from Darling**. Some candidates are intermediate or
first-pass libraries and may not form a linkable, self-contained dependency
set. In QT-110, both attempted static i386 links failed on unresolved symbols;
no linked Darwin API i386 executable was produced.

The QT-111 report and archive were saved on the test machine, not uploaded
with this commit. The newly checked-in generator uses a different marker
from the historical QT-108R binary and has **not** yet been run under Darling.

## Follow-up acceptance criteria

- Host-only fixture tests pass on a clean runner (this directory).
- The checked-in fixture is independently executed on the target machine,
  yielding the new marker and exit 43 without affecting the original prefix.
- A separate i386 Darwin API test resolves its dependency closure, links
  successfully, then executes through libSystem. Do not count the loader smoke
  test as proof of that later milestone.

No changes to Darling's production loader or system libraries are made here.
All new files are GPL-3.0-or-later; upstream implementation code was not copied.
