# SoundHack SH11 — strict Darwin i386 linker handoff and verified artifact delivery

**Date:** 10 November 2026. **Qualification:** 58/58 host tests PASS across SH09-SH11; **LINK_TOOLCHAIN_BLOCKED** on actual original SoundHack FFT object with the installed linker. **No successful Mach-O i386 dynamic link, dyld load, guest run, SoundHack app launch, audio or Logic Studio 8 qualification.**

## Source of truth and the missing tool

- Canonical repository: `fr4nck/d4rling`, integration branch `master`. Baseline before SH11: `d50ca8afbe5e6cdbb7574e2e870180ce6a0c972b`, and upstream `AGENTS.md` / `fr4nck/PMSL-Arch` rules were read.
- Canonical Git submodule: `src/external/cctools-port` at **`darlinghq/cctools-port@d9456c221e1f462e17c0b3297748bc089d5a861e`**. The upstream project states it supports the i386 target, but that statement is not a verified local executable.
- No compatible cctools `ld64` was found in this Linux x86_64 container. `git ls-remote` of the pinned public source failed DNS resolution. The attempted temporary archive acquisition also failed. No download, package installation, clone, change to the user's hosts or build of cctools was performed.
- Installed `ld64.lld` **17.0.0**, executable SHA-256 **`5a87fb0aa6b15f972f76a51419ac5d1de8c7807e1a0fdd8dfba900f7d61bbbdd`**, still responds: `ld64.lld: error: missing or unsupported -arch i386`. That is a toolchain blocker, not a demonstrated failure of the original FFT algorithms.

## SH11 changes to the existing SH10 gate

Only `reproduction/fixtures/soundhack-i386/darwin_archive_gate.py` was extended; no parallel parser or linker was written. A new `test_sh11_cctools_handoff.py` provides the focused negative controls. No production, CI, framework, loader, audio or Petite Victoire source was edited.

- Optional **`--ld64-sha256 HEX`** checks the existing linker executable's bytes (bounded at 256 MiB) *before any build/output*. An invalid/mismatching pin fails closed without invoking the executable. Its observed SHA-256 is included in linker attempt JSON. A matching binary hash proves only **binary identity**, not that it was built from the pinned cctools submodule.
- Optional **`--linked-output /authorized/new/file.dylib`** requires `--ld64`. A successful external linker invocation is not enough: the previous `verify_linked()` gate must first verify `MH_DYLIB` i386, expected install name, exports and imports and reject unparsed `LC_DYLD_INFO`. Only then is the verified candidate copied to a fresh exclusive-created path. Existing files and symlinks are never overwritten, and the saved bytes are compared to the verified SHA-256. Archive and dylib output paths cannot coincide.
- A linker failure, nonexistent output, non-Mach-O output, unresolved opaque dyld data or missing/mismatched binary pin cannot produce a claimed linked file. SH10's default archive-only behavior and its previously checked output archive remain unchanged.

**Important:** tests that patch `verify_linked()` to return a synthetic digest qualify only the *delivery/copy control flow*. They do **not** show that a fake output is a real dylib. The actual production verifier is unpatched during the real-link attempt and all other tests.

## Reproduced results on the isolated host

Input: actual SH08 `MH_OBJECT` i386, **3,236 bytes**, SHA-256 `c5e059e4ce39e2f1b95a925d0eebcac09ded0c36748db0e422b1bca3b7ee1409`, compiled from Tom Erbe's unchanged MIT-licensed SoundHack FFT source. Neither original FFT source nor SDK is copied into the D4rling repository.

- **SH09-SH11 combined: 58/58 PASS, 0 FAIL, 0 SKIP.** Prior SH09 + SH10: 41/41; SH11 adds **17** tests. Tests include nonmatching/malformed linker SHA, missing linker, missing/invalid fake output, protected file/symlink, same output path, real `ld64.lld` refusal, source immutability and mock-only verification/copy controls.
- Actual pinned SHA `ld64.lld` invocation with `--linked-output` returned exit **3**, JSON status **`LINK_TOOLCHAIN_BLOCKED`**. No linked-output path was created.
- Independent archive-only replay: **`DARWIN_ARCHIVE_PASS`**, 4,000 bytes, deterministic SHA-256 **`c11833539630b5aa70d6d63a44d4063eb11a12f0f316884094b0b64f38707169`** (identical to SH10).
- Python 3.13.5, Clang 17.0.0, llvm-ar/llvm-objdump 17.0.0. Scripts passed `py_compile`. No guest/i386 runtime or sound device was available/tested.

## Reproduction: Bash, canonical D4rling checkout

These commands **do not build or install cctools** and assume the verified original SH08 object is independently available. Pass an existing cctools-port linker from the **canonical D4rling build** once qualified by its owner; do not substitute a random binary or mix builds.

```sh
cd /authorized/canonical/d4rling
export SH08_I386_OBJECT=/authorized/path/original-sh08-target.o
python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 \
  -p 'test_sh11_cctools_handoff.py' -v

# No linker: re-check the archive; this cannot claim a linked dylib.
python3 reproduction/fixtures/soundhack-i386/darwin_archive_gate.py \
  --object "$SH08_I386_OBJECT"

# Only after verifying a canonical cctools ld64 exists and recording its hash:
python3 reproduction/fixtures/soundhack-i386/darwin_archive_gate.py \
  --object "$SH08_I386_OBJECT" \
  --ld64 /authorized/canonical/build/path/to/ld64 \
  --ld64-sha256 /REPLACE_WITH_EXACT_64_HEX_DIGEST/ \
  --linked-output /authorized/new/libSoundHackFFT_i386.dylib
```

The SHA value shown is intentionally a placeholder, **not** a valid digest; the script rejects it until replaced with a measured digest of the real authorized linker. Never invent a pin. All outputs must use already authorized directories, and `--linked-output` must name a nonexistent file. Exit **0** only for the bounded archive-only or fully checked `LINK_STRUCTURE_PASS`; **2** for contract failure; **3** for blocked/inconclusive tooling or incomplete dynamic information. A `LINK_STRUCTURE_PASS` would validate structural output **only**, not symbol resolution at runtime, the app, an audio device or Logic.

## Next actual integration milestone

A real, coherent **cctools-port ld64 i386** must be accessible on the same machine as the original SH08 object. Re-run this SH11 gate with a verified linker digest and inspect the report; only if a fully checked dylib is retained should the owner proceed to a D4rling guest loader test. Before any SoundHack app test, authentic application bundle bytes and its imports remain required; CarbonCore `gestaltCarbonVersion` (`'cbon'`) is still missing in the inspected source and tracked in issue #13. No implementation was made for that owner-owned API here.
