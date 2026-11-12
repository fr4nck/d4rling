# Darling Security — i386 64BIT_ONLY CMake object wiring (upstream proposal)

**Date:** 2026-11-12  
**Status:** `DRAFT_FOR_UPSTREAM` — research note, **not a tested patch or merged change**.  
**Source of observations:** operator-provided 5700X Debian WSL2 shell logs and published D4rling checkpoints. The GitHub-connected agent has not executed a local compiler or recovered the exact two uncommitted source diffs. Do not cherry-pick this note as code.

## Upstream destination and submission state

- Intended destination for code: [`darlinghq/darling-security`](https://github.com/darlinghq/darling-security), `master@75effd7ee2e75217b8de030f92443cb3cfba0298` checked on 2026-11-12.
- The security repository reports `has_issues=false`, and the active GitHub integration has **read-only** permissions on upstream. A request to create an issue on [`darlinghq/darling`](https://github.com/darlinghq/darling) failed with GitHub `403 Resource not accessible by integration`. **No upstream issue or PR has been created.**
- Our fork's shared reference: `fr4nck/d4rling`, single branch `master`; do not open a second development branch in that superproject merely for this note. A code PR in the dedicated Security repository will require a writable fork or maintainer-provided route and a tested candidate.
- The source and build trees on 5700X must not be reset, cleaned, merged, or overwritten as part of submission preparation.

## Confirmed target code (upstream, not a conjectured diff)

| File in darling-security | Current architecture-specific construction | Problem for i386-only build |
| --- | --- | --- |
| [`OSX/sec/Security/CMakeLists.txt`](https://github.com/darlinghq/darling-security/blob/master/OSX/sec/Security/CMakeLists.txt) | `add_darling_object_library(SecItemShimOSX_64bit_only 64BIT_ONLY SecItemRateLimit.m)`, with unconditional `$<TARGET_OBJECTS:SecItemShimOSX_64bit_only>` in `add_lib_ios_shim(SecItemShimOSX SOURCES ...)` | 64-bit-only object set pulled into a generic source list |
| [`OSX/utilities/CMakeLists.txt`](https://github.com/darlinghq/darling-security/blob/master/OSX/utilities/CMakeLists.txt) | `add_darling_object_library(utilities_x86_64 64BIT_ONLY SecTapToRadar.m)`, with unconditional `$<TARGET_OBJECTS:utilities_x86_64>` in `add_security_library(utilities FAT SOURCES ...)` | 64-bit-only object set pulled into a FAT static library's generic sources |

Current upstream file blob SHAs: Security CMake `af5d4907d39cf064b3fb0ce5ed6063c2c693ce77`; utilities CMake `f34d7f7d2a4f155fab60ad5fe1baf06f422069b5`. These blobs also match those in the historical submodule at `3cfffcf2c5b5900169c964facdf42cc05c23005c`.

The helper [`darling/cmake/security_lib.cmake`](https://github.com/darlinghq/darling-security/blob/master/darling/cmake/security_lib.cmake) declares that `FAT` builds for both x86_64 and i386 and passes `SOURCES` to `add_darling_static_library`. The impact on mixed-target construction requires a dedicated test.

## Candidate change — implementation *direction*, not a verified local diff

For each CMake file, make the declaration of the respective `64BIT_ONLY` object library and its `$<TARGET_OBJECTS:...>` expansion conditional on `BUILD_TARGET_64BIT`; do not remove the objects from x86_64 builds. Example idea (must be adjusted to real CMake code and tested):

```cmake
set(secitemshim_64bit_objects)
if (BUILD_TARGET_64BIT)
    add_darling_object_library(SecItemShimOSX_64bit_only
        64BIT_ONLY
        SecItemRateLimit.m
    )
    list(APPEND secitemshim_64bit_objects
        $<TARGET_OBJECTS:SecItemShimOSX_64bit_only>
    )
endif()
# In SecItemShimOSX SOURCES: ${secitemshim_64bit_objects}
```

Apply the analogous pattern to `utilities_x86_64` and `SecTapToRadar.m`, using a separately scoped `utilities_64bit_objects` variable. **This is illustrative code; it is not the exact uncommitted patch which produced the tests below**, and its behavior in mixed architectures has not been qualified.

## Bounded 5700X results (reported, not independently replayed)

Historical checkout `fr4nck/d4rling@5b521087d79d4348ebe312e622a05f1f8b55c110`; Security submodule `3cfffcf2c5b5900169c964facdf42cc05c23005c`; `TARGET_i386=ON`, `TARGET_x86_64=OFF`.

- Local, **uncommitted** `OSX/sec/Security/CMakeLists.txt` SHA-256 `a0091142a3ed61e876c1f28ade0c53597516dccf565fa4e22c2738ecdbf18bff`.
- Local, **uncommitted** `OSX/utilities/CMakeLists.txt` SHA-256 `a59b12d5eae516d69aea1f80dba71cf8f6a0cea45c12711d5db1ac0941bc906e`.
- CFNetwork i386: 105/105 Ninja actions, RC 0; final Security i386: 232/232 Ninja actions, RC 0; `LC_ID_DYLIB` matched Security.framework.
- Static closure Security and CFNetwork: 61 Mach-O images, none missing after 14 candidates added to the private prefix.
- Darwin i386 guest `reproduction/fixtures/carbon-event.c`: **3 independent runs** across 3 guest prefixes, runner RC 0, exit code 0, marker `D4RLING-CARBON-EVENT-I386-OK`.
- The fixture specifically tests `CreateEvent`, `SetEventParameter`, `GetEventParameter`, `ReleaseEvent`, not the full EventLoop or GUI.

Evidence:
- [HIT-23R — private installation and first real guest PASS](../evidence/hitoolbox-hit23r-guest-i386-2026-11-12.md)
- [HIT-24R — two repeat guest PASSes, source-level fixture contract](../evidence/hitoolbox-hit24r-repeatability-2026-11-12.md)

## Required qualification before a code PR

1. Recover the **actual local diff** with read-only Git operations from the protected 5700X Security checkout. Record both diff and SHA-256; compare against the proposal rather than reconstructing the patch solely from hashes.
2. Test `TARGET_i386=ON`, `TARGET_x86_64=OFF` in an isolated build; demonstrate no reference to unsupported 64-bit-only objects in the i386 build, and successful link of `Security_i386`.
3. Test `TARGET_i386=OFF`, `TARGET_x86_64=ON` and **both ON**, preserving `SecItemRateLimit.m` and `SecTapToRadar.m` in the expected 64-bit artifact(s). Capture compile commands, links, architecture slices and exported symbols.
4. Run the i386 Carbon fixture again under an isolated private prefix and relevant negative controls. Retain pre/post integrity checks; do not install to system paths, change the historical prefix, or assume a successful static link proves runtime.
5. Publish the code via the permitted Security upstream workflow after source/diff review; link the qualified evidence. **No claim of Logic Pro 8 compatibility.**

## Upstream issue draft (English)

**Title:** Security.framework i386 build: 64BIT_ONLY object libraries referenced unconditionally

The `darling-security` CMake build appears to include `$<TARGET_OBJECTS:SecItemShimOSX_64bit_only>` and `$<TARGET_OBJECTS:utilities_x86_64>` unconditionally in the consumer source lists, even when only `TARGET_i386` is enabled. Both object libraries are explicitly marked `64BIT_ONLY` and contain `SecItemRateLimit.m` / `SecTapToRadar.m` respectively. Two local CMake corrections excluding those 64-bit-only inputs from the i386 case allowed the operator to link Security i386 and run a bounded Carbon-event fixture three times under Darling; see the linked HIT-23R and HIT-24R reports. The exact local diff and 64-bit non-regression are not yet published/tested, so this is a request for review of the architecture guards, **not a claim of a PR-ready fix**. Please advise the preferred Security-submodule contribution route; its issue tracker is disabled.

---

**Status:** `UPSTREAM_SUBMISSION_BLOCKED_BY_GITHUB_PERMISSIONS`, `DRAFT_DOCUMENTED`, `CODE_PR_NOT_CREATED`.
