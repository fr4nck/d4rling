# D4rling SoundHack SH12 - offline cctools-port link replay

Date: 10 November 2026. Scope: **verified SH10 ZIP -> pinned SH08 Mach-O i386 object -> existing cctools linker discovery -> existing SH11 fail-closed link gate**. No install, SDK, network, D4rling guest or sound output. Status on this test host: **LINKER_ABSENT** (exit 3), not a link PASS.

## Source and provenance

- Canonical project: `fr4nck/d4rling`, branch `master`. Last previously integrated SoundHack milestone: SH11 commit `98a4a99aed6e661b5bc2d250e00ef40617e25b42`.
- Referenced cctools submodule: `darlinghq/cctools-port@d9456c221e1f462e17c0b3297748bc089d5a861e`, stored as a Git submodule of D4rling. Its README lists an i386 target. The README is NOT proof that an authorized linker was built and tested.
- Input was the existing SH10 offline ZIP, 7,705 bytes, SHA-256 `2fb5c48ecc0ab879a2f60285574f275dd320bc076a1d3ad587a9584adc2d542b`.
- Canonical Darwin static archive inside the ZIP: 4,000 bytes, SHA-256 `c11833539630b5aa70d6d63a44d4063eb11a12f0f316884094b0b64f38707169`.
- Restored FFT `MH_OBJECT` i386 prefix: 3,236 bytes, SHA-256 `c5e059e4ce39e2f1b95a925d0eebcac09ded0c36748db0e422b1bca3b7ee1409`. Four trailing LF bytes in the Darwin `ar` member are verified as archive alignment and are never treated as modified FFT code.
- Original source: Tom Erbe `tomerbe/SoundHack@df6f0bc89243b93573b391afa5ab371cce56ac95`, MIT; no original source added here. MIT notice within SH10 ZIP is checked. This does not grant a separate right to redistribute SoundHack.app's historical executable.

## What SH12 implements

New `reproduction/fixtures/soundhack-i386/sh12_cctools_replay.py` reuses the existing `i386_link_gate.inspect_macho` and `darwin_archive_gate.qualify` from SH09-SH11 instead of writing another Mach-O parser or linker.

1. Validate ZIP entry set, CRC, bounded uncompressed size, MIT notice and qualification metadata; verify the pinned static archive SHA-256.
2. Read the exact FFT member with the existing `llvm-ar`, check the expected 4-byte Darwin alignment and the original SH08 object SHA-256, and inspect its i386 Mach-O structure.
3. Find native host ELF executables with cctools-port ld64 names **only within a single explicitly designated build root**, in bounded known cctools-port build paths. Ignore scripts, symlinks, wrong host architecture, `ld64.lld` and locations outside the given tree. If more than one candidate exists, refuse automatic choice.
4. If exactly one eligible linker exists, record its measured SHA-256 and pass it to the existing SH11 gate with `--ld64-sha256` semantics. This records **binary identity only** and does not establish its source-tree or toolchain provenance. The SH11 gate is responsible for link invocation, checking `MH_DYLIB` i386, install name, expected symbols, and rejecting opaque/unverified dyld data.
5. Optional `--linked-output` writes **only** a new, structurally verified dylib, with exclusive creation. In the actual test no linked file was produced.

On the current isolated Linux x86_64 host, no cctools `ld64` exists in the bounded build tree. `ld64.lld` 17 is present but rejects the Darwin i386 target. The previously attempted git fetch of cctools also failed DNS. No package was installed and no cctools build occurred.

## Tests and actual observation

Environment: Linux x86_64, Python 3.13.5, preinstalled Clang 17, LLVM ar/objdump 17. The genuine SH10 ZIP and SH08 object were supplied to the test environment; **not a mock SoundHack binary**.

- SH12 alone: **19/19 PASS**, including recovery of the authentic SH08 object, archive tampering, missing MIT notice, malformed or duplicated ZIP entries, symlinks, wrong ELF architecture/type, ambiguous linker discovery and exclusive-output protection when linker is unavailable.
- SH09-SH12 combined: **77/77 PASS**, 0 SKIP, 0 FAIL, from `unittest discover` with `SH08_I386_OBJECT` and `SOUNDHACK_SH10_PACKAGE` pointing to the authentic artifacts.
- Without an SH10 ZIP: SH12 tests **11 PASS, 8 SKIP**, 0 FAIL; no source-dependent test pretends to pass.
- Actual CLI replay on the real package: exit **3**, JSON status `LINKER_ABSENT`. Archive and FFT hashes match the known evidence. No linked-out file was created.
- Positive local ELF **discovery** tests use inert synthetic byte buffers that are **never executed**. They are not proof of a successful cctools link.

## Reproduce from a canonical Linux/WSL D4rling checkout

Before the command: have the released SH10 ZIP already downloaded from this conversation to an authorized local directory, and a previously built canonical cctools-port build under one known root. Do **not** invent these inputs. The command performs no download or installation. 

```sh
cd /authorized/canonical/d4rling
python3 reproduction/fixtures/soundhack-i386/sh12_cctools_replay.py \
  --sh10-package /authorized/SH10/d4rling-SH10-archive-i386.zip \
  --build-root /authorized/canonical/build-core-i386 \
  --linked-output /authorized/new/libSoundHackFFT_i386.dylib
```

The output pathname must not exist. Exit `0` is reserved for SH11's bounded `LINK_STRUCTURE_PASS`; exit `2` is a disproved contract; exit `3` means no linker, ambiguous linker, malformed/unavailable prerequisite, or link failure/inconclusive output. The tool prints JSON for all ordinary outcomes.

## Non-claims and next step

Neither linked dylib, Darwin guest execution, SoundHack.app launch, QuickTime/Carbon GUI, real audio device playback nor Logic Studio 8 is qualified. This project should not keep adding synthetic tests in lieu of the missing real linker. The next relevant step is to run SH12 with the **actual canonical cctools-port build linker**, then use a coherent D4rling guest install to qualify loading. The separately tracked Carbon `gestaltCarbonVersion ('cbon')` blocker in issue #13 also remains relevant to full SoundHack.app startup.
