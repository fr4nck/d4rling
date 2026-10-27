# Carbon/HIToolbox duplicate-symbol regression

The fork's Debian package CI on 2026-10-27 failed when compiling
`src/frameworks/Carbon/src/Carbon.c`:

```text
src/frameworks/Carbon/src/Carbon.c:149:10:
error: conflicting types for 'SetEventParameter'
```

The umbrella Carbon source still defined `SetEventParameter` with a `UInt32`
size parameter. The public `CarbonEventsCore.h` declares `ByteCount`,
and `HIToolbox/src/CarbonEventsCore.c` implements actual parameter storage.
Changing only the stub's argument type would leave an incorrect
false-success implementation shadowing HIToolbox.

`Carbon.c` also returned null from a legacy `GetApplicationEventTarget`
stub, while HIToolbox now has its own non-null application target.

**Correction:** drop both obsolete umbrella definitions. The Carbon
CMakeLists already includes `reexport(Carbon HIToolbox ...)`; the
HIToolbox framework builds `CarbonEventsCore.c`. The existing authoritative
implementations remain unchanged.

## Independent host check

```sh
sh tests/regressions/carbon-reexports/run.sh
```

The runner requires only Python 3 and tracked source files. It never starts
Darling, initializes submodules, downloads dependencies, or needs root.
It runs regression cases against the real source and deliberately corrupted
temporary copies, then prints `SOURCE_ABI_CONTRACT=PASS` if the source-level
relations are intact.

Covered regressions:

- Two obsolete Carbon definitions must not reappear, including duplicates.
- The HIToolbox setter declaration and implementation use `ByteCount`.
- The HIToolbox setter must retain its allocation path.
- The application target implementation must not regress to null.
- Carbon must reexport HIToolbox and HIToolbox must build its event core.
- Incomplete files and existing JSON report destinations cause an error.

The dedicated GitHub Actions workflow is lightweight and does not build
Darling. A successful `SOURCE_ABI_CONTRACT` is **not** a proof of a complete
Mach-O build, dynamic reexport resolution, guest runtime compatibility, GUI
rendering or Logic Studio 8 support. The existing Debian package workflow
serves as a separate integration gate and must be evaluated independently.

This correction is intended only for `fr4nck/d4rling` until the user
explicitly authorizes any upstream contribution. No upstream PR is created.
