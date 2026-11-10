# BSD i386 R4-E — CMake option and isolated target smoke

Date: 2026-11-10. Commit introducing option: `a7308c49335da7a9f1b9d42bb1f2d0c97aa7b01b`. Master checked: `a7308c49335da7a9f1b9d42bb1f2d0c97aa7b01b`.

## Change

`src/startup/mldr/CMakeLists.txt` now declares `option(D4RLING_MLDR_I386_MMAP_DIAG ... OFF)`. Within `if (BUILD_TARGET_32BIT)`, only target `mldr32` receives `target_compile_definitions(mldr32 PRIVATE D4RLING_MLDR_I386_MMAP_DIAG)` when enabled. The `mldr` target does not receive this definition. The real `mldr.c` includes `loader.c` twice on x86_64, with `GEN_64BIT` then `GEN_32BIT`; the loader's own `GEN_32BIT && D4RLING_MLDR_I386_MMAP_DIAG` guard is necessary.

## Local isolated CMake test

A minimal temporary CMake project (CMake 3.31.6) built two synthetic executables named `mldr` and `mldr32` from the canonical R4-D smoke fixture. Its option/target-scoping pattern mirrors the change above; it is **not the full Darling CMake project**. The harness explicitly defines `GEN_32BIT` for its synthetic `mldr32` because it does not include Darling's real `mldr.c`.

- `-DD4RLING_MLDR_I386_MMAP_DIAG=ON`: configure/build PASS, synthetic `mldr32` emits expected diagnostic, synthetic `mldr` emits nothing.
- `-DD4RLING_MLDR_I386_MMAP_DIAG=OFF`: configure/build PASS, synthetic `mldr32` emits nothing.

**PASS:** isolated CMake option behavior. **NOT TESTED:** complete Darling configuration, compilation/link of actual `mldr32`, real i386 Mach-O loading, or historical R3 guest tests. No change to `vm.mmap_min_addr`.

## Next gate

Configure a current-master Darling build with `-DBUILD_TARGET_32BIT=ON -DD4RLING_MLDR_I386_MMAP_DIAG=ON`, build `mldr32`, verify compile command contains the diagnostic definition and `mldr` does not. Preserve existing private builds; use a new isolated build directory and keep the opt-in off for production.
