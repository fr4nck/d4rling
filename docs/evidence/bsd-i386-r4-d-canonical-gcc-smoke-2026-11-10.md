# BSD i386 R4-D — canonical GitHub source, GCC smoke qualification

Date: 2026-11-10. GitHub master checked: `13b28f0a35dcd773b93acab17277c602cc77a8c4`.

## Identity and environment

File: `reproduction/fixtures/bsd-i386-r4-d-mmap-diag-smoke.c`.
GitHub Git blob SHA-1: `b5456b413454edceb4803af14fe326bb5737cd9d`.
Locally reconstructed file `git hash-object`: `b5456b413454edceb4803af14fe326bb5737cd9d` — **byte-identical to the repository file**.

Executed in an isolated Linux container with GCC, not on 5700X or 10400.

## Commands and observed results

For each configuration, `gcc -std=c11 -Wall -Wextra -Werror` compiled the **canonical** source, and the resulting executable exited 0:

| Defines | GCC | Run | stderr |
| --- | --- | --- | --- |
| `GEN_32BIT`, `D4RLING_MLDR_I386_MMAP_DIAG` | PASS | PASS | 134 bytes |
| `GEN_32BIT` only | PASS | PASS | 0 bytes |
| `D4RLING_MLDR_I386_MMAP_DIAG` only | PASS | PASS | 0 bytes |

Enabled stderr:

```text
MLDR_I386_MMAP_DIAG branch=file-backed segment=__TEXT requested=0x401000 length=4096 slide=0x400000 vmaddr=0x1000 flags=0x12 errno=13
```

## Qualification boundary

**PASS:** exact GitHub C fixture, three host GCC builds and three runs, no warnings under `-Werror`. **NOT TESTED:** actual `src/startup/mldr/loader.c` compilation, `mldr32` linkage, runtime i386 Mach-O loading, historical AUD-R3 failures, or 5700X. The source's `GEN_32BIT` macro in this host smoke does not imply a 32-bit ELF binary.

A separate 10400 WSL2 historical core-i386 build was reported in `docs/qualification/10400-wsl2-core-i386-2026-11-10.md`, but it does not include this current-master R4-D instrumentation.

Next gate: build the actual current-master mldr32 and run opt-in diagnostics without relaxing host memory protections.
