# Draft — darlinghq/darling-dyld (not opened)

**Title:** libdyld: read the Darwin TSD through %fs in the i386 tlv_get_addr fast path

**Body:**

On i386 under Darling, Linux (glibc) owns `%gs`, and the Darwin TSD lives in
`%fs`. `os/tsd.h` in darling-xnu's libsyscall already selects `%fs` for
`DARLING && __i386__` (`OS_GS_RELATIVE` = `address_space(257)`,
`_OS_PTR_MUNGE`). However, the i386 fast path of `_tlv_get_addr` in
`src/threadLocalHelpers.S` still reads the per-thread block from
`%gs:key*4`.

As a result, every thread-local access from an i386 image misses the block
that `tlv_allocate_and_initialize_for_key()` registered with
`pthread_setspecific()` (which writes the `%fs` slot). The lazy path allocates
and registers a new zero-filled block each time, so:

- a value stored in a `thread_local` variable is never read back (for example,
  CarbonCore's `MemError()` always returns `noErr` after a failing Memory
  Manager call);
- each access leaks one block (16 bytes for a 2-byte variable; 1000 reads leak
  16000 bytes).

x86_64 is not affected: Darwin's TSD is in `%gs` there, which is what the
x86_64 path reads.

**Change:** under `DARLING`, the i386 fast path reads `%fs:0x0(,%ecx,4)`. The
lazy-allocation path and the x86_64/arm64 paths are unchanged.

**Testing** (Darling built with `COMPONENTS=gui_stubs`, i386 + x86_64, Debian
WSL2; guest runs in fresh prefixes):

- probe calling `GetHandleSize(NULL)` / a foreign handle / `SetHandleSize(h, -1)`
  then `MemError()`: i386 before 4/10, after 10/10; x86_64 10/10 both;
- instrumentation of CarbonCore's own TLV descriptor (key 257): before the
  change, the stored `-109` sits in the `%fs` slot while the `%gs` slot reads 0
  and the `%fs` block is replaced on every access; after, `MemError()` returns
  `-109` and the slot stays stable;
- 100 and 1000 cycles of a QuickTime/Memory Manager workload: heap stable
  after the change, 240 bytes per cycle growth before;
- no regression seen in existing i386 CarbonCore/Security/Carbon Events
  witnesses and a BSD syscall dispatcher witness.

**AI assistance:** the diagnosis, probes and patch were prepared with the help
of an AI coding assistant and reviewed and tested by the submitter, who takes
responsibility for the contribution.
