# Carbon event regression runner: post-PR #3 dependency audit

Date: 2026-10-22. Inspected starting point: `master`
`f8e9b62e12247b827273ce42c277fbc4ee5b927c` (PR #3 merge).

**No production Carbon implementation change in this follow-up.** This work
only improves the host regression runner's preflight and sanitizer selection.
No repository, binary or dependency was downloaded into the qualification
container, and no package was installed. The container has no Darling source
checkout, so the real-header Carbon suite was **NOT RUN**.

## Dependencies required by `tests/regressions/carbon-events/run.sh`

- A source checkout with `basic-headers/MacTypes.h`, the HIToolbox public
  headers and `CarbonEventsCore.c`, CoreServices' `CoreServices/MacTypes.h` and
  `CarbonCore/MacErrors.h`, plus the three tests and CF test-only allocator.
- The `src/external/corefoundation` Git submodule, pinned by master to
  `a3640a77410cf1825f7855172b1551ae7917c461`.
- Its `include/CoreFoundation/CFBase.h` is a symbolic link to
  `../../submodules/swift-corelibs-foundation/CoreFoundation/Base.subproj/CFBase.h`.
  That nested submodule is pinned to
  `ea1ea0bb416025a8cc5a282df03c2e8f12788e2d`.
- A C11 compiler and linker, with pthreads and (only for sanitizer runs) a
  compatible sanitizer runtime. Clang is the runner's default compiler.

These dependencies are declared in the repository and confirmed by inspection
of the pinned public Git trees. The preflight checks existence of primary
inputs; it is not a substitute for preprocessing all transitive includes.
Even a successful `run.sh` run still links `allocator-adapter.c` instead of
Darling's production CoreFoundation library. It would qualify **real headers
with a fake CF runtime**, not full CF runtime compatibility.

## Observed host checks (new session)

Host: Linux x86_64; Clang 17.0.0; GCC 14.2.0.

| Check | Observed result | Meaning |
| --- | --- | --- |
| Clang C11 empty host program with `-Wall -Wextra -Werror` | PASS, exit 0 | Toolchain works for a trivial C11 program only |
| Clang `-m32` compile of trivial translation unit | PASS, exit 0; ELF i386 relocatable | Compiler can emit i386 objects only |
| Clang `-m32` link of same object | BLOCKED / exit nonzero | Missing 32-bit start objects and C libraries (`Scrt1.o`, `crti.o`, `-lgcc`, `-lc`...) |
| `sh -n` on revised runner and preflight | PASS (2/2) | Shell syntax only |
| Preflight on sparse mock checkout missing real inputs | PASS: correctly refuses, exit 2 | Real-header run not attempted |
| Preflight on fake tree with broken pinned CFBase symlink | PASS: correctly detects nested-submodule case, exit 2 | No real headers compiled |
| Preflight on fake tree with empty placeholder files | PASS, exit 0 | Only path-checking logic tested; not a build |
| Mock compiler with `SANITIZE=address,undefined` | PASS: sanitizer propagated to 5 mocked compilations and 3 mocked links (8/8) | Argument forwarding only; no Carbon executable |
| Mock compiler with `SANITIZE=address` and `SANITIZE=undefined` | PASS: each forwarded to 8/8 calls | Argument forwarding only |
| Mock compiler without `SANITIZE` | PASS: no sanitizer flag forwarded | Argument forwarding only |
| `SANITIZE=unknown` | PASS: rejected with exit 2 | No longer silently ignored |
| Nonexistent `CC` | PASS: preflight rejects with exit 2 | No compiler launched |
| Real-header `run.sh` | NOT RUN (missing checkout, pinned and nested CF dependencies) | No runtime or SDK qualification |

The fake test files and mock compiler were created temporarily for testing
runner control flow. They are not production dependencies or an alternative
Carbon implementation. All mock results are explicitly **infrastructure-only**.

## Change and risk

The original `run.sh` used `SANITIZE=address` alone; values such as
`SANITIZE=address,undefined` were silently ignored. The revised runner accepts
`address`, `undefined`, and `address,undefined`, forwards the selected sanitizer
to every C compilation and every link, and rejects unsupported values.
It preserves the existing three executable regression targets and test-only
allocator adapter. A new `check-real-deps.sh` refuses absent primary inputs
before creating a build directory and explains broken CFBase symlinks.
Neither script initializes submodules or installs anything.

The 246 PASS / 0 FAIL C11 and 246 PASS / 0 FAIL ASan+UBSan figures in
`docs/carbon-queue-dispatch-2026-10-22.md` are historical **isolated-header**
qualifications from PR #3, not fresh results here. No LeakSanitizer, real CF,
Darling Mach-O exports, full build, graphical event pump, or Logic Studio 8
functional test was executed in this follow-up.

## Next environment-gated steps (not performed)

1. Provide an authorized local checkout with the pinned CoreFoundation and
   nested Foundation submodules already initialized, plus the required system
   toolchain. Verify `check-real-deps.sh` and then run `run.sh` using real headers.
2. Run unsanitized C11 and available sanitizer variants, recording exact
   compiler versions, assertion counts, exits, and log extracts.
3. Separately link against the actual CoreFoundation runtime, verify generated
   Mach-O exports and i386 toolchain/runtime, then consider CFRunLoop and
   application-level event-loop testing.

No interpretation of the first step as a validation of Logic Studio 8 is
warranted: event wait, per-thread queues, CFRunLoop integration and graphical
or audio functionality remain unimplemented or unqualified.
