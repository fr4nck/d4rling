# SoundHack SH05 — executable host witness for the pre-MainLoop Gestalt gate

**Date:** 10 November 2026. **Scope:** SoundHack-specific independent fixture and reproducible diagnosis. **No modification to D4rling CarbonCore production**, QuickTime, BSD, dyld, audio, build or CI. The SoundHack application milestones remain blocked.

## Primary source and exact fingerprints

- Tom Erbe, `tomerbe/SoundHack@df6f0bc89243b93573b391afa5ab371cce56ac95`, `ToolBox/SoundHack.c` (`634ba7a49132b4643d3a3dc8de2da2e1c91209b7`), lines **109–136** and **154–233**: `main` initializes Toolbox, menus/dialogs and globals, then calls `CapabilityCheck()` before `EnterMovies` and `MainLoop`. The check calls `Gestalt(gestaltCarbonVersion, &response)` and rejects `response <= 0x100`. It also requires `Gestalt(gestaltSystemVersion, &response) == noErr` and `response >= 0x0860`. The application's Carbon gate does not check the first `Gestalt` status separately; a returned zero response still rejects startup.
- D4rling `src/frameworks/CoreServices/src/CarbonCore/Gestalt.cpp` Git blob **`dffdd4cb26c7f191c6e2b5fc97298c79a8d75dff`** (read on `master` 10 Nov): only implements the system-version family and architecture selector. Unknown `gestaltCarbonVersion` (`'cbon'`) goes to `default`: writes `0` and returns `unimpErr` (`-4`). The `gestaltSystemVersion` case **falls through** into `gestaltSysArchitecture` because of a missing `break`, overwriting the previously calculated value.
- Apple Carbon Gestalt API/selector: https://developer.apple.com/fr/documentation/coreservices/1471624-gestalt and historical `gestaltCarbonVersion = 'cbon'`, `gestaltSystemVersion = 'sysv'` constants. These source references are consulted; no proprietary headers copied into the fixture.
- D4rling `src/frameworks/CoreServices/include/CarbonCore/MacErrors.h` Git blob **`fef87e7c791c880a51a7a304c0c5c7d9e455141d`**, `unimpErr = -4`.

## Witness mechanism

`gestalt_startup_gate.py` reads **only** the supplied real `Gestalt.cpp` as bytes, optionally checks its Git blob hash, extracts the one `Gestalt(uint32_t,int*)` function without changing it, compiles that exact function with **test-only mock sysctl and selector constants** into a temporary host C++ program, then executes and emits JSON. It does not substitute fake success into D4rling or change the production source. Host compiler C++17 is required but never installed or downloaded. No guest i386 binary is built or started. Both Carbon gate values are compared to SoundHack's actual `CapabilityCheck()` thresholds. The host's mocked Darwin release `20.4.0` is only a deterministic input, not a validated OS mapping.

From the D4rling checkout root:

```sh
python3 reproduction/fixtures/soundhack-i386/gestalt_startup_gate.py \
  --gestalt-source src/frameworks/CoreServices/src/CarbonCore/Gestalt.cpp \
  --expected-blob dffdd4cb26c7f191c6e2b5fc97298c79a8d75dff
```

**Expected return `2` on the pinned source** (`HOST_STARTUP_GATE_BLOCKED`, not a test runner error). `0` means only that the two *host-mocked* selector gates satisfy the checked thresholds. `3` means malformed/unavailable source, compiler failure, blob mismatch or another inconclusive condition. Always inspect the JSON. Never convert any of these codes into a real app GUI/runtime success.

## Observed and negative controls

- Exact upstream fork `Gestalt.cpp` was transferred to a **private temporary file** and independently verified by `git hash-object` equal to the pinned Git blob. That file is **not committed** to this SoundHack fixture.
- Executed on Linux x86_64 host, Python 3.13.5 and existing `c++` (GCC 14.2): `gestalt_startup_gate.py` on that exact file returned **exit 2**, `HOST_STARTUP_GATE_BLOCKED`:
  - `'cbon'` Carbon: error **`-4`**, response **`0`**, SoundHack gate rejects.
  - `'sysv'` System: error **`0`**, response **`10`** rather than the mock's calculated `0x1440`, SoundHack gate rejects. This reflects the observed fallthrough to Intel architecture response.
  - `'sysa'` architecture: error **`0`**, response **`10`**.
- `python3 -m unittest discover -s reproduction/fixtures/soundhack-i386 -p 'test_*.py' -q`: **48 cases, 47 PASS, 1 SKIP** in the temporary fixture-only test directory (canonical project source not mounted under its expected repository path). The exact-production source probe above was executed independently and is not that skipped test.
- New tests: host-positive Carbon/System selectors, Carbon negative, System negative, mismatched source pin, malformed/duplicate source, C++ compile negative, missing compiler, input preservation, optional pinned production witness. The last test runs automatically when the full repository source exists at the documented path and has the pinned blob.
- No GitHub Actions/paid CI, full D4rling guest, SoundHack app, audio output, ABI integration or real graphical startup verified.

## Disposition / owner handoff

**Potential launch blocker**: `Gestalt('cbon')` is unsupported by the *inspected source*, and `Gestalt('sysv')` currently overwrites the computed version. These are stronger pre-MainLoop candidates than the conditional QuickTime *playback* stubs; other initialization steps may still fail earlier at runtime. This observation is not a claim of a guest crash.

The CarbonCore owner should first reproduce the host witness against current source and confirm semantics / existing tests before proposing any **typed** production patch. Do **not** simply change `unimpErr` to `noErr`, or manufacture an arbitrary Carbon version, or edit SoundHack to bypass checks. Any correction requires the subsystem owner, ABI/behavior tests, negative controls and a separate qualified commit. SoundHack here remains test/fixture-only.
