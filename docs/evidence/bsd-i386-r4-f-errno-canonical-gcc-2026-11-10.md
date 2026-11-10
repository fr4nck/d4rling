# BSD i386 R4-F — canonical errno-preserving diagnostic GCC qualification

Date: 2026-11-10. GitHub master checked: `6b58dc0ac16ec6d1cb982c1fc95a39a6b44e657f`.

## Source identity

`reproduction/fixtures/bsd-i386-r4-d-mmap-diag-smoke.c` at GitHub blob SHA-1 `482779e2d063a673ba9c956518ef05ca6fb0616c`.
The file reconstructed in an isolated Linux container has exactly the same `git hash-object` SHA-1, confirming byte identity.

## Actual execution

Compiled exact file using `gcc -std=c11 -Wall -Wextra -Werror`, executed each resulting host ELF:

| Defines | Compile | Exit | stderr bytes |
| --- | --- | --- | --- |
| `GEN_32BIT`, `D4RLING_MLDR_I386_MMAP_DIAG` | PASS | 0 | 134 |
| `GEN_32BIT` only | PASS | 0 | 0 |
| `D4RLING_MLDR_I386_MMAP_DIAG` only | PASS | 0 | 0 |

Enabled stderr:

```text
MLDR_I386_MMAP_DIAG branch=file-backed segment=__TEXT requested=0x401000 length=4096 slide=0x400000 vmaddr=0x1000 flags=0x12 errno=13
```

The fixture returns nonzero if `errno != 13` after the diagnostic; exit 0 demonstrates preservation in this synthetic execution.

## Boundaries

**PASS** exact current fixture with host GCC. **NOT TESTED** full Darling `loader.c`, `mldr32` build, guest execution, historical 5700X AUD-R3 failures. This container's `gcc -m32` link probe fails because `Scrt1.o`, `crti.o`, and i386 `libgcc` are missing; do not interpret host `GEN_32BIT` as a 32-bit ELF qualification. No host sysctl changes.
