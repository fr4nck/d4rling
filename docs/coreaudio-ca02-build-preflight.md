# CA-02 — CoreAudio Mach-O build preflight (offline, read-only)

Status: **source/CMake review complete; local preflight and build NOT RUN**.
Reviewed branch: `work/core-audio`, baseline `604b5ec16570469e4dca3ed21ebad8fb8247ca66`.
This document is not a Mach-O qualification result.

## Source-level dependencies and target discovery

- `src/CMakeLists.txt` adds `CoreAudio` **only inside**
  `if (COMPONENT_gui)`. A build configured without the GUI component will
  not expose the CoreAudio target. Check the cache and generated targets
  before attempting a build.
- `src/CoreAudio/CoreAudio/CMakeLists.txt` declares
  `add_framework(CoreAudio FAT CURRENT_VERSION VERSION "A" ...)`,
  compiling `AudioHardware.cpp`, `AudioHardwareImpl.cpp`, `HostTime.mm`
  and the `pulse/` backend. Its dependencies include `system`,
  `cxx`, `CoreFoundation` and the `pulse` wrapper.
- `src/CoreAudio/CMakeLists.txt` requires FFmpeg and PulseAudio via
  `find_package(FFmpeg REQUIRED)` and `find_package(PulseAudio REQUIRED)`,
  and wraps `libpulse.so` plus FFmpeg libraries. These dependencies may
  prevent **CMake configuration**, before any compile.
- A previous `darling` / `mldr` build from the Carbon tree does **not**
  prove that CoreAudio was configured or compiled. Do not contaminate the
  Carbon or MIDI qualification build trees.

## First action on 5700X: read-only environment inventory

Run this in **Debian 13 / WSL2**, not PowerShell. No network access,
installations, checkout updates, or compilation are performed.

```sh
cd "$HOME" || exit 1
printf '%s\n' '=== CA02 ENVIRONMENT (READ ONLY) ==='
uname -a
for tool in git cmake ninja clang clang++ llvm-nm-19 llvm-nm file pkg-config; do
    if command -v "$tool" >/dev/null 2>&1; then
        printf 'TOOL_PASS: %s -> %s\n' "$tool" "$(command -v "$tool")"
    else
        printf 'TOOL_MISSING: %s\n' "$tool"
    fi
done
printf '%s\n' '=== SOURCE CHECKOUTS ==='
for src in "$HOME/d4rling-carbon-qualif" "$HOME/d4rling-midi-qualif" "$HOME/d4rling"; do
    if test -d "$src/.git" || test -f "$src/.git"; then
        printf 'SOURCE: %s\n' "$src"
        git -C "$src" status -sb
        git -C "$src" rev-parse HEAD
        if test -f "$src/src/CoreAudio/CoreAudio/CMakeLists.txt"; then
            printf '%s\n' 'COREAUDIO_SOURCE_PRESENT'
        else
            printf '%s\n' 'COREAUDIO_SOURCE_MISSING_OR_SPARSE'
        fi
    fi
done
printf '%s\n' '=== EXISTING BUILD TREES ==='
for build in "$HOME/d4rling-build-carbon" "$HOME/d4rling-build-audio" "$HOME/d4rling-build"; do
    if test -f "$build/CMakeCache.txt"; then
        printf 'BUILD: %s\n' "$build"
        grep -E '^(CMAKE_HOME_DIRECTORY|CMAKE_GENERATOR|COMPONENTS):' "$build/CMakeCache.txt" || true
        if test -f "$build/build.ninja"; then
            if grep -q 'CoreAudio/CoreAudio' "$build/build.ninja"; then
                printf '%s\n' 'COREAUDIO_NINJA_REFERENCES_PRESENT'
            else
                printf '%s\n' 'COREAUDIO_NINJA_REFERENCES_ABSENT'
            fi
        fi
    fi
done
printf '%s\n' '=== DEVELOPMENT LIBRARY METADATA ==='
if command -v pkg-config >/dev/null 2>&1; then
    for lib in libpulse libavcodec libavformat libavutil libswresample; do
        if pkg-config --exists "$lib"; then
            printf 'PKG_PASS: %s %s\n' "$lib" "$(pkg-config --modversion "$lib")"
        else
            printf 'PKG_MISSING: %s\n' "$lib"
        fi
    done
fi
printf '%s\n' 'CA02_PREFLIGHT_DONE (no build performed)'
```

**Interpretation:** `COREAUDIO_NINJA_REFERENCES_PRESENT` is a *textual
indicator*, not proof that the exact `CoreAudio` target exists. The
`COMPONENTS` cache value may not itself tell which component variables were
enabled; verify target listing after preflight.

## Conditional next action (not authorized by the preflight)

Only after the output is reviewed, choose a **separate audio build tree**
and confirm a source checkout with `src/CoreAudio` present. Check whether
the selected configuration enables `COMPONENT_gui`, and whether its
configuration can run fully offline. Never run `git submodule update`,
`apt install`, `cmake --fresh`, or any network-capable step without
explicit authorization.

If an existing **audio** build tree is already configured with the correct
sources and target, a subsequent targeted compile may use:

```sh
cd "$HOME/d4rling-build-audio" || exit 1
cmake --build . --target CoreAudio --parallel 4
```

This command is an **example only**, not yet executed; first confirm
`CoreAudio` is a generated target and the build cannot trigger unapproved
downloads. CMake can invoke dependency steps, so an offline preflight is
required even for an apparently local build.

## Qualification gates after a successful compile

1. Find the *actual* framework output from the build log and inspect with
   `file -L`. Do not assume the output path.
2. Verify `file` reports a Mach-O image, **not ELF**. Inspect architecture
   and exports with the installed Mach-O-aware `llvm-nm`.
3. Required candidate exports: `_AudioObjectGetPropertyData`,
   `_AudioObjectGetPropertyDataSize`, `_AudioDeviceCreateIOProcID`,
   `_AudioDeviceStart`, `_AudioDeviceStop`,
   `_AudioGetCurrentHostTime`.
4. Record missing exports as FAIL; a symbol's presence is **not** evidence
   its behavior works (the host-time function currently returns zero).
5. Only then build/run a minimal Mach-O client with the actual Darling
   loader and check the default output device and PCM ASBD.
6. Record separate verdicts for configuration, compilation, Mach-O format,
   exports, loader, API behavior and actual audio output. Missing host
   prerequisites are SKIP, not PASS.

## Current ledger

| Gate | Result |
| --- | --- |
| CMake source mapping | PASS (review only) |
| GUI component gating identified | PASS (review only) |
| Offline local preflight | NOT RUN |
| Targeted CoreAudio compilation | NOT RUN |
| Mach-O image inspection | NOT RUN |
| Mach-O export inspection | NOT RUN |
| Darling loader test | NOT RUN |
| Audio output | NOT RUN |

No test counts, audio claims, or compatibility percentages are inferred.
