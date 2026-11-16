# SoundHack SH19 — isolated host-only gate for the authentic 0.896 application

**Scope:** SoundHack-only, offline static inspection tool. No Logic work, no
Darling production source changes, no copied SoundHack binaries, no guest run.

## Inputs and objective

On the separate **10400**, SH18 extracted the 2007 SoundHack 0.896 legacy
Mac installer and its actual universal `SoundHack.app`. The observed original
`Contents/MacOS/SoundHack` has SHA-256
`6fb11c708079ca3b8f91dc53ab0d8ae732fbb8be32f0e22e34114764b9be089c`
and PPC + i386 slices. Its verified disk image and archive remain on that
machine in the protected validation directory. They were **not transferred
to, inspected or executed in the agent's current test container**.

## Development

New `reproduction/fixtures/soundhack-i386/sh19_app_gate.py` reuses the
existing `macho_audit.py` parser without duplicating Mach-O decoding. It
requires the official SHA-256, i386 `MH_EXECUTE`, FAT PPC+i386, bundle
`Info.plist` with matching `CFBundleExecutable`, and a bounded regular-file
inventory. It reports `LC_LOAD_DYLIB` and nlist counts. If explicitly given
an existing private Darling sysroot it checks **literal** library file paths
within that root, including traversal/symlink-escape rejection. It does not
equate file presence with dyld resolution, ABI, GUI or audio PASS.

New `test_sh19_app_gate.py` uses synthetic fixture files and a mocked
interface to the pre-existing independently tested Mach-O parser. It tests
correct inventory, optional prefix semantics, bad original hash, PPC-only,
thin/non-universal format, incorrect filetype, parser digest contradiction,
symlink files/directories and escaping paths, invalid or contradictory
`Info.plist` and malformed install-name commands.

## Executed checks and results

Python syntax compilation: **PASS** (both new files).
Unittest (`PYTHONPATH=/mnt/data python3 -m unittest -v test_sh19_app_gate`):
**14/14 PASS** after adjusting one assertion that incorrectly expected
the term `i386` rather than the actual conservative `Universal Binary`
failure message. The adjustment changed only the test assertion to match
the established fail-closed behavior. All 14 tests then passed.

The passing tests exercise **synthetic and mocked inputs only**. No real
SoundHack.app, Mac guest, Carbon user interface or audio result was tested
by this SH19 lot. The real app may reveal mismatches not simulated by the
fixtures, including missing Info.plist or resource-fork requirements.

## Reproduce (already installed Python, from repository root)

    python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 -p 'test_sh19_app_gate.py' -v
    python3 reproduction/fixtures/soundhack-i386/sh19_app_gate.py --app /authorized/SoundHack.app --sysroot /authorized/private-install/libexec/darling

Do not infer a specific local path exists on the 5700X: the original app
was extracted on the 10400 and must be explicitly verified on any target.
The tool itself does not download, modify or install anything. With no
`--output` it prints JSON only; with `--output` it creates a **new** report,
never overwriting prior files.

## Classification / next obstacle

**`SH19_HOST_GATE_TEST_PASS` — STATIC TOOL ONLY.**

Original SoundHack app's dynamic library closure, loadability, display
and sound remain **NOT QUALIFIED**. Next valid step is to make the pinned
application available in an explicitly authorized isolated 5700X
validation location and execute this tool against that exact app and an
existing, provenance-checked private sysroot. Only then choose a single
live guest-run blocker and produce a minimal reproducer for its owner.
