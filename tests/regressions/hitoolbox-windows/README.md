# HIToolbox window stub regression checks

These are the 25 assertions supplied in `darling-hitoolbox-lot1.zip`, using its
minimal stand-in header. They exercise the repository's `MacWindows.cpp` directly.
They do not compile against Darling's real headers and do not validate the Carbon
ABI, a full Darling build, window rendering, event dispatch, or Logic Studio 8.

The source change prevents unimplemented window operations from reporting success.
It implements no graphical backend. Existing void stubs remain unchanged.

## Run

Linux with a C++17 compiler:

```sh
sh tests/regressions/hitoolbox-windows/run.sh
```

Windows, from a Visual Studio x64 Native Tools command prompt:

```bat
tests\regressions\hitoolbox-windows\run-windows.cmd
```

The Windows-only forced include `msvc-attributes.h` neutralizes GNU attributes.
Consequently the source's logging constructor and destructor attributes are not
tested there. No production source or test assertions are modified for MSVC.

## Recorded verification (2026-10-15)

- Base commit: `60ba801decee7a00782f74f6be4c8ffb013f79ff`.
- Original source Git blob: `b328f28495f70dbd6f80120343c6124b87e9a46f`.
- Supplied archive SHA-256:
  `1db07936186425e66ec0fbcde4361e1aecabdc5aaa54391b04c9660bdf408708`.
- Archive baseline matched the pinned GitHub source byte for byte.
- `git -c core.autocrlf=false apply --check` succeeded; applying the supplied
  patch produced its corrected source byte for byte.
- Compiler: MSVC 19.51.36260, x64, C++17, Windows.
- Original source: `Checks: 25 | Failures: 23`, exit 1 (expected).
- Applied source: `Checks: 25 | Failures: 0`, exit 0.
- Both builds emitted the MSVC `getenv` deprecation warning C4996.

The Linux runner and full Darling build have not been executed in this session.
WSL enumeration previously failed with `Wsl/EnumerateDistros/Service/E_ACCESSDENIED`.
Logic has not been installed or run. GUI and audio compatibility remain untested.

## Scope limits

The existing `GetWindowEventTarget` declaration returns `OSStatus`; this change
preserves that declaration and does not establish Apple API compatibility.
The disabled X11 branch is retained but has not been compiled or tested.
`CreateNewWindow` rejects null arguments before clearing the output; the supplied
tests do not assert output clearing for a null rectangle. Broader API contract
changes and an AppKit/Cocotron bridge require separate investigation.
