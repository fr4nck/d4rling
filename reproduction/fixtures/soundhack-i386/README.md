# SoundHack 0.896 — SH01–SH03 static witnesses (i386)

These files are **read-only, standard-library Python 3** tools. No Apple SDK,
SoundHack executable, media, GUI, audio, Linux guest or additional package is
included. License for these new tests/tools: GPL-3.0-or-later (D4rling).

## Scope

- `macho_audit.py`: bounds-checked thin/FAT Mach-O (32/64, endian) reader;
  reports selected slice, `LC_LOAD_*` dylibs, `LC_SYMTAB` **nlist** undefined
  and external defined names. Flat images compare by name; two-level images
  also check `n_desc` import ordinals against matching provider `LC_ID_DYLIB` IDs.
- `quicktime_stubs.py`: a source-pattern witness for **14 specific QuickTime
  functions** used by `SoundFile/Play.c` in Tom Erbe's SoundHack source at
  `tomerbe/SoundHack@df6f0bc89243b93573b391afa5ab371cce56ac95`.
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
