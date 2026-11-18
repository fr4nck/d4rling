# mldr — universal binaries, FAT_MAGIC_64 and bounded slice selection

Port of [Darling #2069](https://github.com/darlinghq/darling/pull/2069)
(merge `3edffc15309c9ccefe9d3a59db70a24886a9ee28`) onto D4rling; see issue #18
and [the evidence note](../../../docs/evidence/mldr-fat64-issue18-2026-11-18.md).

## Host tests

```sh
tests/regressions/mldr-fat64/run-host.sh          # cc
CC=clang tests/regressions/mldr-fat64/run-host.sh
```

- `tests/mldr/fat_slice.c` — the upstream test, unchanged (27 checks).
- `fat_slice_cap.c` — D4rling complement (5 checks). The upstream
  "count above the cap" case is already rejected by the table-length check, so
  it survives a mutant without the `MLDR_FAT_MAX_ARCHES` cap. Here the table
  fits both the buffer and the file, and only the cap can reject it.

Both are built for 64-bit and 32-bit hosts, and the upstream test once more
under ASan/UBSan. The CMake test `mldr_fat_slice` (upstream) is also declared
in `src/startup/mldr/CMakeLists.txt`.

## Guest witnesses

- `fatprobe.m` — prints the architecture of the slice mldr ran
  (`FATPROBE arch=i386|x86_64`). Built with the Darling SDK for i386 and x86_64.
- `makefat.py I386 X86_64 OUTDIR` — synthetic universal executables:
  FAT32/FAT64, both byte orders, an out-of-file record next to a valid one, a
  slice past the end, an absurd `nfat_arch`.
- `makedyld.py DYLD OUTDIR` — header variants of the installed universal
  `dyld` (FAT64 big/little endian, FAT32 little endian, absurd `nfat_arch`,
  x86_64 slice past the end). The slices are byte-identical to the original.

mldr loads `dyld` itself through `load()`, so a FAT64 `dyld` placed in an
OverlayFS layer of a private mount namespace exercises the FAT64 path of
`mldr` and `mldr32` in a real guest, for every process of the container. The
installation itself is never modified.

A FAT64 *executable* started through `execve` does not reach mldr: the
emulated `execve` in the xnu submodule
(`libsystem_kernel/emulation/.../process/execve.c`) only recognises
`FAT_MAGIC`/`FAT_CIGAM`, upstream as well. This is outside this port.
