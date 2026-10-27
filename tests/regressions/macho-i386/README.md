# Mach-O i386 loader smoke fixture (host-only generator)

This directory supplies an independent, deterministic i386 Mach-O executable
for testing the Darling **binary loader**, not the Darwin C library.

## Host regression (no Darling or Apple SDK)

On any Linux development host with Python 3 and optionally the `file` tool:

```sh
sh tests/regressions/macho-i386/run.sh
```

The runner executes 17 Python `unittest` cases, generates two one-page Mach-O
i386 files in a temporary directory, optionally checks the format with `file`,
and removes the temporary files. It never starts Darling or executes the guest
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
