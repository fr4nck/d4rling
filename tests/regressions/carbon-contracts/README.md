# Carbon callback and window-target contract regression

This small correction follows the original
[Carbon Event Manager Reference](https://leopard-adc.pepas.com/documentation/Carbon/Reference/Carbon_Event_Manager_Ref/Reference/reference.html),
an archived mirror of Apple's document. It does not implement event dispatch.

- EventHandlerProcPtr is an OSStatus-returning function pointer taking
  EventHandlerCallRef, EventRef and a user-data pointer.
- EventHandlerUPP aliases that function-pointer type.
- GetWindowEventTarget returns EventTargetRef, not OSStatus. With no window
  backend/target implementation it returns null, not an error integer as a pointer.

Other opaque reference typedefs, unimplemented event APIs, window rendering and
32-bit guest compatibility are outside this change.

## Run

From a checkout with the pinned CoreFoundation submodule initialized and a
working Linux Clang C/C++ toolchain:

```sh
CC=clang CXX=clang++ sh tests/regressions/carbon-contracts/run.sh
sh tests/regressions/hitoolbox-windows/run.sh
```

The first runner compiles the real MacWindows.cpp and CarbonEventsCore.c with the
real public headers. It checks signatures in C11 and C++17, directly invokes a
user-supplied callback through the public UPP type, and checks that the current
window-target stub returns null. A deliberately incompatible callback must fail
compilation in each language. This tests a typed callback call, not installation,
NewEventHandlerUPP or event dispatch. Temporary build output is removed.

## Recorded verification, 2026-10-15

Reference: personal master b932d448bbb317654a45640717925823d2fd3fb0.
Sources were fetched at that commit and the patch was tested in an overlay.
Unmodified dependencies came from the existing checkout; audited Carbon and QD
headers there match the earlier source baseline. CoreFoundation is pinned at
a3640a77410cf1825f7855172b1551ae7917c461, with nested Foundation at
ea1ea0bb416025a8cc5a282df03c2e8f12788e2d.

Actual checks used Debian/WSL x86_64, workspace-local Clang 19.1.7 and GCC 14.2.0.
The runner uses __APPLE_CC__=1, DEPLOYMENT_RUNTIME_SWIFT=1 and a forced include
of real basic-headers/MacTypes.h, as in the earlier host source checks.

- Before: the new contract source failed compilation in C11 and C++17 with the
  old public headers, including signature static-assertion failures.
- After: C11 and C++17 compile, link and execute successfully (exit 0).
- The incompatible callback is rejected in both languages.
- The delivered run.sh was itself executed successfully; it also compiled the
  unchanged CarbonEventsCore.c against the corrected types.
- nm on the rebuilt MacWindows host object shows the plain C GetWindowEventTarget
  symbol.
- The existing standalone window assertions were rebuilt with GCC and the updated
  fixture: 25 checks, 0 failures, exit 0. One expectation changed from an OSStatus
  error to a null EventTargetRef. No other assertion was added or removed.
- The first local invocation had a missing include-search path for Menus.h. The
  harness was corrected before the successful before/after comparison; missing
  headers were not counted as evidence that the old contracts were rejected.

These are host ELF and minimal-fixture checks, not a complete Darling/Mach-O
build or i386 ABI validation. Windows was not retested. No graphical window,
event queue/dispatch, Logic installation, audio or MIDI operation was tested.

## Provenance

Prepared for fr4nck with OpenAI Codex. Existing source authors/notices are
retained; Apple documentation was consulted as an interface reference. No
external implementation or fork patch was copied. New regression files use
GPL-3.0-or-later. See the root CREDITS.md.
