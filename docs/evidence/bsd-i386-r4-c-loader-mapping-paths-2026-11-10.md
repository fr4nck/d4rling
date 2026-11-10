# BSD i386 R4-C — loader mapping paths (static source qualification)

Date: 2026-11-10. GitHub master at analysis: `c9331a9475a46a02a8a10724e07cb15ded6a2b4a`.
Scope: `src/startup/mldr/loader.c`, read-only analysis; no guest, loader or host execution.

## Source observations

The template function `load32` initializes `uintptr_t slide = 0`. For `MH_EXECUTE | MH_PIE` or `MH_DYLINKER`, it computes a reservation from segment ranges, calls `mmap((void*)base, mmapSize, PROT_NONE, MAP_ANONYMOUS | MAP_PRIVATE | MAP_EXTRA, -1, 0)`, stores the returned address as `slide`, then unmaps the reservation. This is the current source's *slide variable*, not a value observed from historical R3 logs.

For each `LC_SEGMENT`, the code has **distinct mapping requests**:

1. If `filesize < vmsize` and `slide != 0`: anonymous `compatible_mmap((void*)addr, seg->vmsize, ..., MAP_FIXED_NOREPLACE, ...)`, with `addr = seg->vmaddr + slide` for nonzero `vmaddr`, but `addr = 0` when `seg->vmaddr == 0`.
2. If `filesize < vmsize` and `slide == 0`: anonymous `compatible_mmap((void*)PAGE_ALIGN(seg->vmaddr + seg->vmsize - (seg->vmsize - seg->filesize)), PAGE_ROUNDUP(seg->vmsize - seg->filesize), ..., MAP_FIXED_NOREPLACE, ...)`. This simplifies to a page-aligned `seg->vmaddr + seg->filesize`, **not necessarily `seg->vmaddr`**.
3. If `filesize > 0`: file-backed `compatible_mmap((void*)(seg->vmaddr + slide), seg->filesize, ..., MAP_PRIVATE | MAP_FIXED_NOREPLACE or MAP_FIXED, fd, seg->fileoff + fat_offset)`.

All three failure branches print `seg->vmaddr` rather than the requested `addr` or page-aligned expression: `Cannot mmap segment %s at %p: %s`. Therefore the log address **cannot by itself identify the failed effective mapping request**; this applies even with `slide == 0` in the anonymous tail path.

## Bounded conclusion

Historical AUD-R3's `__TEXT at 0x1000` does not establish whether the failing call was anonymous or file-backed, what address was passed to `compatible_mmap`, or the value of `slide`. Linux `vm.mmap_min_addr` should not be lowered as a diagnostic shortcut.

## Proposed next gate (not implemented)

A separately qualified, opt-in diagnostic build can report on failure only: `GEN_32BIT`, segment name, anonymous/file-backed branch, requested address and length, `slide`, mapping flags, errno, and original `seg->vmaddr`. Avoid printing sensitive addresses in normal releases, and avoid changes to the mapping policy. Validate a synthetic fixture before any use on historical executables. Do not modify production loader until the opt-in diagnostic path is reviewed and tested.

Status: **STATIC SOURCE OBSERVATION**, not runtime validation.
