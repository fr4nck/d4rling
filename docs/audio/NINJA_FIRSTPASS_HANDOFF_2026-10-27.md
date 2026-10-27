# D4rling — handoff Carbon/Ninja ↔ CoreAudio/JACK

**Date:** 2026-10-27  
**Status:** SOURCE/GRAPH QUALIFIED; BUILD/INSTALLED I386 DYLIBS NOT YET QUALIFIED  
**Owner boundary:** The CoreAudio/JACK PR only audits and documents. The concurrently active Carbon/Ninja maintainer owns any CMake reconfiguration, Ninja invocation, installation or Darling runtime execution.

## Reproducible evidence and source identity

The 5700X user's final read-only audit (`JACK-01E11O`) used:

- **Build tree:** `/home/Deniel/d4rling-core/d4rling-build-i386`
- **CMake source tree:** `/home/Deniel/d4rling-ui/d4rling-carbon-qualif`
- **`CMAKE_HOME_DIRECTORY`:** points to the Carbon source tree above; this mismatch with the *location* of the build tree is real but not proof of a CMake bug
- **CMake config:** `CMAKE_BUILD_TYPE=Debug`, `COMPONENTS=core`, `TARGET_i386=ON`
- **Source HEAD:** `b7d0cb6a79fe196657deb9711647f8486bcc5e5e` (`HIToolbox: implement event metadata and retained lifetime`), verified as a genuine [`fr4nck/d4rling` commit](https://github.com/fr4nck/d4rling/commit/b7d0cb6a79fe196657deb9711647f8486bcc5e5e)
- **Git top-level:** `SOURCE_GIT_ROOT=NOT_AVAILABLE`; `git -C <source> rev-parse --show-toplevel` failed in the user's script while `rev-parse HEAD` succeeded; stderr was not retained, so **cause unknown**
- **Local report only:** `/home/Deniel/d4rling-audio/qualif/jack01e11o-N8M32Z6f`. Do not claim this raw report was separately uploaded or available to GitHub

**GitHub ancestry verified 2026-10-27:** `work/carbon-event-contracts` currently points to `8744f2deba4ae053f4a27fb07bdb975791344ab8`, **6 commits ahead of `b7d0cb6` and 0 behind**. Those six commits change Carbon HIToolbox and its tests/docs; they do **not** alter `cmake/darling_lib.cmake` or `cmake/architecture.cmake` in the returned comparison. `work/core-audio` points to `e05f18ab851fe676039903c66a26a4c3f137317e` and **diverges** from `b7d0cb6` (23 commits ahead, 2 behind) and current Carbon (23 ahead, 8 behind), relative to their respective merge bases. **Do not switch the existing build's source tree or merge/cherry-pick these branches to 'fix' the mismatch automatically.**

## Why there are many `*_firstpass.dylib` targets

At **the exact pinned source commit `b7d0cb6`**, [`cmake/darling_lib.cmake`](https://github.com/fr4nck/d4rling/blob/b7d0cb6a79fe196657deb9711647f8486bcc5e5e/cmake/darling_lib.cmake) defines `add_circular(name ...)` to handle circular dependencies in `/usr/lib/system`. It first creates a `${name}_firstpass` library with `-flat_namespace -undefined,suppress`, then creates the final `${name}` linking against selected sibling firstpass libraries and their declared dependencies. When `FAT` is requested it calls `make_fat` on the relevant stages. This is **intentional two-stage linking**, not an unexplained linker anomaly. [`cmake/architecture.cmake`](https://github.com/fr4nck/d4rling/blob/b7d0cb6a79fe196657deb9711647f8486bcc5e5e/cmake/architecture.cmake) derives `BUILD_TARGET_32BIT=TRUE` when `TARGET_i386=ON`; this derived variable need not appear in the CMake cache.

**Do not bypass the firstpass stage by invoking just an isolated final ld64 command.** Its Ninja producer rules exist; availability of their transitive inputs and actual successful 32-bit links has not been established.

## Observed target readiness on the user's 5700X

| Target in i386 build.ninja | Direct `.o` prerequisites present | Missing implicit non-object outputs | Missing order-only non-object outputs | Direct output |
| --- | ---: | ---: | ---: | --- |
| `src/external/libc/libsystem_c.dylib` | **677/677** | **15/18 absent; 15/15 absent have producer rules** | **59/64 absent; 59/59 absent have producer rules** | absent |
| `src/external/libsystem/libSystem.B.dylib` | **17/20** | **1/1 absent, producer rule exists** | **35/38 absent; 35/35 absent have producer rules** | absent |

The three missing `system_obj` objects for the umbrella library are `init.c.o`, `darling/src/dummy.c.o` and `CompatibilityHacks.c.o` in `src/external/libsystem/CMakeFiles/system_obj.dir/`. All three have **C compiler producer rules**, and their referenced source paths in `d4rling-ui/d4rling-carbon-qualif` exist. Missing output counts refer to the observed filesystem snapshot; duplicates between implicit and order-only categories must not be counted twice.

All 15 missing implicit non-object `libsystem_c` prerequisites are `*_firstpass.dylib`; sample producers include `system_kernel_firstpass`, `system_malloc_firstpass`, `system_pthread_firstpass`, `system_blocks_firstpass`, `system_m_firstpass`, `launch_firstpass`, `system_notify_firstpass`, and `libdispatch_shared_firstpass`. The sole missing implicit `libSystem.B` dependency is `libsystem_malloc_firstpass.dylib`. **Producer edges exist; this does not establish that their own prerequisites exist or that the links will succeed.**

An existing FAT output at `d4rling-build-i386/src/external/xnu/darling/src/libsystem_kernel/libsystem_kernel.dylib` has `x86_64` and **i386** slices; `llvm-nm-19 --arch=i386 -g --defined-only` confirmed global definitions of `_socket`, `_connect`, `_recvmsg`, `_mmap`, `_munmap`, and `_close`. In contrast, three tested guest system dylibs under `/opt/d4rling-qt-i386/libexec/darling/usr/lib` are **thin x86_64**, despite the install prefix's name; no i386 runtime linkage in that prefix is proven.

## Completed IPC qualifications — do not repeat

- JACK-01E7H: Linux x86_64 parent/child shared anonymous `mmap` IPC, 50,000 ordered stereo frames **PASS on 5700X**
- JACK-01E8H: independent Linux x86_64 processes, `memfd_create` + Unix `SCM_RIGHTS`, 50,000 ordered stereo frames **PASS on 5700X**
- JACK-01E9: genuine Linux static ELF32 i386 native `exit(0)` **PASS on 5700X**
- JACK-01E10H: genuine Linux ELF32 client ↔ Linux ELF64 server, `memfd` + `SCM_RIGHTS`, 50,000 ordered stereo frames **PASS on 5700X**
- JACK-01E11H: Darwin i386 Mach-O **object** built with six *undefined imports* for the above functions **PASS**; **no guest link/execution**
- JACK-01E11K: all six matching *defined i386 exports* found in existing FAT `libsystem_kernel.dylib` **PASS**

**Non-qualified:** an installed coherent i386 `libSystem` stack, dynamic Mach-O linking, Darling CA-12 Mach RPC (`-111`), guest-to-Linux fd passing/mmap, real JACK callbacks, ALSA/Logic Studio 8 audio.

## Owner's next bounded decision (do not run from this document)

1. Verify that the **Carbon source checkout at `b7d0cb6`** is intentionally the source for `d4rling-build-i386`, and obtain the actual `git --show-toplevel` failure diagnostic without modifying the checkout. Do not assume the more recent Carbon branch or the divergent CoreAudio branch is interchangeable.
2. Verify exclusive ownership/idle state of the **specific build tree** and the exact transitive firstpass dependency graph; a single `pgrep` snapshot with `NINJA_PROCESS=NOT_DETECTED` is not evidence of exclusive ownership.
3. Only after owner coordination and a separate explicit go-ahead, consider a **targeted graph-respecting** build for `system_c` then `system`/their required firstpass prerequisites. Save full command line, exact source/ref, output SHA-256/architectures, linker logs, and test results. Handle failures by dependency group; do not overwrite a known-good output.
4. Keep the build outputs separate from the installed `/opt/d4rling-qt-i386` prefix until the entire i386 system-library set and a minimal Mach-O guest link have been qualified. CA-12 RPC needs an independent recovery plan.

## Hard constraints

No `ninja` (even dry-run), `cmake --build`, source reconfiguration, installing packages, changing `AGENTS.md`, copying files into `/opt`, restarting Darling, starting JACK, or touching current prefix/build trees in the **GitHub-only handoff phase**. User's sole qualification output directory remains `/home/Deniel/d4rling-audio/qualif`. The local report's full raw bytes remain on the 5700X; this handoff was reconstructed from pasted stdout only. Do not mark the PR mergeable or CI validated on this basis.

**Tracking:** [PR #5](https://github.com/fr4nck/d4rling/pull/5), branch `work/coreaudio-ninja-convergence` → `work/core-audio`, remains a draft. Detailed chronological evidence is in `docs/audio/COREAUDIO_JACK_CONVERGENCE.md` §§35–51.
