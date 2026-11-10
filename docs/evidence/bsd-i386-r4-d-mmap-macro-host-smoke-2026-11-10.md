# BSD i386 R4-D — host C smoke test of diagnostic macro

Date: 2026-11-10. Source reviewed: `src/startup/mldr/loader.c` at commit `d0d86f19286c1ed1802b5af9edc3a72e29f2911d`. Repository master at evidence publication: `3ec64e438d4a1397e3f61ccda09f1b3cfd4623db`.

## Method

An isolated C11 program reproduced the exact `MLDR_MMAP_DIAG` macro definition and conditional guard from the source, using a synthetic segment structure (`segname`, `vmaddr`) and simulated `errno=13`. GCC host compilation used `-std=c11 -Wall -Wextra -Werror`. No Darling source tree, SDK, Mach-O executable, guest process, or 5700X was available to the host compiler.

Three configurations compiled and executed successfully:

- `-DGEN_32BIT -DD4RLING_MLDR_I386_MMAP_DIAG`: one diagnostic line emitted.
- `-DGEN_32BIT`: no diagnostic output.
- `-DD4RLING_MLDR_I386_MMAP_DIAG` without `GEN_32BIT`: no diagnostic output.

Enabled output:

```text
MLDR_I386_MMAP_DIAG branch=file-backed segment=__TEXT requested=0x401000 length=4096 slide=0x400000 vmaddr=0x1000 flags=0x12 errno=13
```

An initial harness-only `-Werror=unused-variable` warning in the disabled configuration was fixed by explicitly using the synthetic segment variable; the three final builds passed.

## Qualification

**PASS (isolated host macro smoke only). NOT QUALIFIED: full `loader.c` compilation, i386 cross-build, runtime Darling guest, or historical AUD-R3 reproduction.** This test does not establish the correctness of the loader's three call sites or address selection.

Next gate: compile actual `src/startup/mldr/loader.c` against its Mach-O headers in an appropriate build, run diagnostic-on/off checks and confirm original failure output remains unchanged. No `vm.mmap_min_addr` change.
