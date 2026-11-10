# SoundHack SH04 — Mach-O i386 two-level symbol ordinals (10 November 2026)

**Status:** `TEST PASS` on synthetic **host** files; application loading, GUI, DSP and audio remain `BLOCKED`. This lot only extends the SoundHack-specific fixture. No production frameworks or shared state files changed.

## Source of truth and ownership

- D4rling: `fr4nck/d4rling`, `master`; first preflight HEAD `afed46219191cb0d93cdb2e09f92e0413c14cfeb`. Other QuickTime and BSD work continued in parallel; this lot modifies only `reproduction/fixtures/soundhack-i386/` and this new evidence file.
- Previous SH01–SH03: `f563a9f47b5d6056d87a3f354781f406405abb94` (27/27 host tests).
- Apple [XNU mach-o/nlist.h](https://github.com/apple-oss-distributions/xnu/blob/main/EXTERNAL_HEADERS/mach-o/nlist.h): `GET_LIBRARY_ORDINAL`, `SELF_LIBRARY_ORDINAL`, `EXECUTABLE_ORDINAL`, `DYNAMIC_LOOKUP_ORDINAL`, `N_WEAK_REF`, `N_INDR`; two-level ordinals index *load* commands in order, not `LC_ID_DYLIB`. Historical ordinal `0xfe` can mean library #254 if 254 load commands exist.
- Apple's [OS X ABI Mach-O File Format Reference](https://www.symbolcrash.com/wp-content/uploads/2019/02/ABI_MachOFormat.pdf) confirms dylib IDs and ordinals. This is a reference only, no SDK or proprietary headers copied.
- Original SoundHack 0.896 code remains pinned at `tomerbe/SoundHack@df6f0bc89243b93573b391afa5ab371cce56ac95` (MIT). Neither source nor binary is embedded in this fixture.

## Corrected failure mode

The SH02 fixture compared undefined imports to the union of all provider export names. For a two-level Mach-O, this can report a **false match** if a symbol exists in provider B but the consumer's `n_desc` ordinal requires provider A. Such a false PASS is unacceptable when preparing SoundHack's actual i386 import inventory.

`macho_audit.py` now records each undefined external symbol's 8-bit ordinal, linked library name, optional (`N_WEAK_REF`) flag and special lookup class. For two-level consumers it checks exports against a provider's **matching `LC_ID_DYLIB` install name**, never against another provider merely exporting the same spelling. `LC_ID_DYLIB` does not occupy a consumer import ordinal; malformed out-of-range ordinals and install-name commands on non-dylib images are rejected. `N_INDR` aliases do not count as concrete definitions.

Ambiguities are **not** converted into success: absent provider identity, dynamic/flat/self/main lookup, prebound or common symbols, indirect exports, or dyld-info paths produce `STATIC_INCONCLUSIVE` under `--strict`. Weak missing imports are reported under `optional_missing_nlist` separately; they do not prove functional behavior. This tool still does not resolve `LC_DYLD_INFO` bind opcodes, reexports, dependent-framework closure, executable search paths, symbol ABI or actual guest calls.

## Reproducible tests

From the repository root (Python 3, standard library; no SDK):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 -p 'test_*.py' -v
```

**Observed in isolated Linux container:** Python 3.13.5; **39/39 TEST PASS** (previous 27 retained, 12 new). New cases include a correct two-level match, same-name wrong-provider rejection (`exit 2`), no verified provider ID (`exit 3`), optional weak import, invalid ordinal, `LC_ID_DYLIB` exclusion from ordinals, ordinal order, invalid/duplicate dylib ID commands, dynamic lookup, common symbol and `N_INDR` alias.

Independent examination of temporary **synthetic** fixtures, not committed:

- `file sh04-ordinal-consumer.macho` -> `Mach-O i386 executable, flags:<|TWOLEVEL>`.
- `llvm-objdump --macho --private-headers sh04-ordinal-consumer.macho` -> `LC_LOAD_DYLIB` `/A/Correct.dylib`, `LC_SYMTAB`, `nsyms 2`.
- `llvm-objdump --macho --syms` -> strong undefined `_SoundHackPlay` plus weak undefined `_Optional`.

The private synthetic `sh04-ordinal-consumer.macho` is **not** SoundHack and has no observed loader execution. GitHub Actions and paid runners were not used.

## Real executable / next gate

The original publisher's freeware page lists SoundHack 0.896 Intel/PPC (Mac OS X 10.4+). Its linked archive `https://tre.ucsd.edu/wordpress/wp-content/uploads/2016/12/SH896.dmg_.zip` could not be accessed here: `curl` reports `Could not resolve host: tre.ucsd.edu`. **No real file hash, binary import inventory, runtime or audio success** has been obtained. Source-derived QuickTime playback stubs from SH03 remain a known conditional playback blocker, not proof of the first launch failure.

The original `ToolBox/SoundHack.c` also shows `ToolBoxInit`, `DialogInit`, `GlobalInit` (which calls `InitializePlay` -> `Pa_Initialize`), and `CapabilityCheck` (Carbon/System `Gestalt`, `SndSoundManagerVersion`) before `MainLoop`. This is the next independent **startup** contract to qualify without changing other owners' production code.
