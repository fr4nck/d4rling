# Carbon UI: source audit and first milestone

Source inspection on 2026-10-15. This is an implementation proposal, not a
working backend or a report of GUI tests.

## Pinned references

- Personal integration baseline: `e9d08af00e6f3d0c7e89eb3fe2c97131c112e787`.
- Darling upstream baseline: `60ba801decee7a00782f74f6be4c8ffb013f79ff`.
- Cocotron submodule: `c8d38d16a9f613d300157bebbab2b9501bc0c274`.
- Previous real checks and limitations: [logic8-progress.md](logic8-progress.md).
- Imported work and attribution: [../CREDITS.md](../CREDITS.md).

The local source checkout was at `1cf634b46d1c6eed55547862e4ed3739edc91559`;
the later integration changes concern documentation and submodule URLs, not the
audited implementation. Cocotron was inspected at its exact recorded gitlink.

## What is actually present

| Layer | Source entry point | Observed state |
| --- | --- | --- |
| Carbon windows | HIToolbox `src/MacWindows.cpp` | `NO_X11` is defined. The imported correction reports unsupported window creation instead of false success; it implements no window backend. |
| Carbon events | HIToolbox `src/CarbonEventsCore.c` | Event creation, queue reception and handler installation are stubs, including success returns without producing the requested objects. |
| Carbon application loop | Carbon `src/Carbon.c` | `GetApplicationEventTarget` returns null and `RunApplicationEventLoop` is a stub. |
| Carbon interface loading | HIToolbox `src/IBCarbonRuntime.c` | Nib/window construction remains stubbed; a native window alone will not load a complete interface. |
| CoreGraphics window API | Cocotron `CoreGraphics/CGS.m` | Connection/window identifiers and `CGSNewWindow`, release and ordering entry points exist. These delegate to backend objects. |
| CoreGraphics X11 backend | `CoreGraphics/X11.backend/CGSConnectionX11.m` | X connection and CFRunLoop socket source exist, but `newWindow:` has an empty body. Keyboard, mouse, expose and configuration cases mostly do nothing; close handling is a comment. |
| CoreGraphics X11 window | `CoreGraphics/X11.backend/CGSWindowX11.m` | Copyright/license header and import only; no implementation. |
| AppKit X11 backend | `AppKit/X11.backend/X11Display.m` and `X11Window.m` | Considerably more implementation: native window creation, run-loop source and NSEvent posting. Runtime behavior has not been tested here. |

HIToolbox currently links CoreFoundation, Foundation and system. CoreGraphics
also links Foundation but not AppKit. AppKit reexports ApplicationServices.
The AppKit X11 window expects an NSWindow delegate and uses NSApp; it cannot
simply be given a WindowRef. Its CGWindow base is distinct from CGSWindow.

## Proposed boundary

Use a lower-level native window/event service in CoreGraphics, with a Carbon
adapter for opaque WindowRef objects, event targets and EventRef delivery.
AppKit can keep its existing route initially. Sharing selected native operations
later is preferable to rewriting AppKit as a prerequisite.

This is a proposed implementation direction, consistent with the discussion in
[Darling issue 937](https://github.com/darlinghq/darling/issues/937), not evidence
that a complete common service exists today.

The CoreGraphics CGS path is a skeleton, not a ready bridge. Its
`CGEventCreateWithEventRecord` conversion function exists, but does not replace
native window creation or delivery of native events to Carbon. Existing AppKit
X11 code is a source for carefully extracted operations, not a drop-in backend.

## First implementation batch: event contracts before graphics

1. Audit public prototypes, callback types, constants, layouts and ownership
   against the original Carbon API before introducing dispatch. In particular,
   `GetWindowEventTarget` currently returns OSStatus in both declaration and
   definition, while the documented API returns EventTargetRef.
   `EventHandlerProcPtr` is currently void*, rather than a typed callback.
2. Implement the minimal event object, parameters, lifetime and queue operations.
   Filtered receives must preserve unmatched events; define peek/removal,
   priorities and timeout behavior from the reference API.
3. Add typed handlers, removal and dispatch, including next-handler propagation
   and an unhandled result. Then implement the application target and run loop,
   with a wakeable quit path and no polling loop.

This batch can be checked independently of a display. The next tests must use
real public headers and sources. The supplied synthetic window-test header is
insufficient for validating the public ABI.

## Following batch: one real Carbon window

For the first graphical experiment, target X11. Implement creation, visibility,
ordering and destruction in the lower-level backend; map native identifiers to
Carbon window objects and their event targets. Define focus, coordinate
conversion and native event translation explicitly.

Acceptance criteria, all still pending:

- A small Carbon program creates and displays one window, with deterministic
  background presentation and repaint after expose.
- Mouse click and keyboard events arrive at the intended registered handler.
- Closing delivers a close request; the program can dispose the window and quit
  cleanly. Closing a window must not unconditionally terminate an application.
- Without a display, creation returns a real error and no usable WindowRef.
- Repeated create/close leaves no registered native window, queued dangling
  reference or live handler attached to destroyed state.
- Validate the guest-facing 32-bit ABI and symbols separately from host checks.

Apple's historical documentation excludes the Carbon Window Manager and other
UI managers from its 64-bit API. Therefore an x86_64 Linux stub test is not a
substitute for i386 guest validation. The actual Logic binaries and their
architectures have not been inspected.

Nib loading, menus, HIView/control drawing, QuickDraw/Quartz integration,
text input, accessibility and Carbon/Cocoa interoperability need subsequent
work. A blank native window does not validate those features. Audio/MIDI remain
a separate prerequisite for Logic; neither subsystem is validated by this audit.

## Source references and credits

No external implementation was copied or imported by this documentation change.
Future code extraction must retain each file's author and license notices and
record exact source and adaptation in CREDITS.md.

- Darling/HIToolbox contributors, existing history and GPL notices:
  [MacWindows.cpp](https://github.com/fr4nck/d4rling/blob/e9d08af00e6f3d0c7e89eb3fe2c97131c112e787/src/frameworks/Carbon/HIToolbox/src/MacWindows.cpp),
  [CarbonEventsCore.c](https://github.com/fr4nck/d4rling/blob/e9d08af00e6f3d0c7e89eb3fe2c97131c112e787/src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c).
- Lubos Dolezel, 2020 GPL-3.0-or-later notices in the CGS sources:
  [CGSConnectionX11.m](https://github.com/darlinghq/cocotron/blob/c8d38d16a9f613d300157bebbab2b9501bc0c274/CoreGraphics/X11.backend/CGSConnectionX11.m),
  [CGSWindowX11.m](https://github.com/darlinghq/cocotron/blob/c8d38d16a9f613d300157bebbab2b9501bc0c274/CoreGraphics/X11.backend/CGSWindowX11.m).
- Johannes Fortmann, 2008 MIT notice in
  [X11Window.m](https://github.com/darlinghq/cocotron/blob/c8d38d16a9f613d300157bebbab2b9501bc0c274/AppKit/X11.backend/X11Window.m);
  Christopher J. W. Lloyd, 2006-2007 MIT notice in
  [CGWindow.h](https://github.com/darlinghq/cocotron/blob/c8d38d16a9f613d300157bebbab2b9501bc0c274/CoreGraphics/include/CoreGraphics/CGWindow.h).
  These notices identify consulted files, not an exhaustive list of contributors.
- Apple,
  [Carbon Event Manager Reference, archived mirror of Apple's document](https://leopard-adc.pepas.com/documentation/Carbon/Reference/Carbon_Event_Manager_Ref/Reference/reference.html):
  callback signature, target return type and event behavior.
- Apple,
  [64-Bit Guide for Carbon Developers](https://developer.apple.com/library/archive/documentation/Carbon/Conceptual/Carbon64BitGuide/PortingTo64Bit/PortingTo64Bit.html):
  historical architecture/API availability.
- [Carbon event-loop PR 1780](https://github.com/darlinghq/darling/pull/1780)
  remains a research reference; its WIP was not imported.
- Audit and implementation proposal prepared with OpenAI Codex for fr4nck.

## Verification and open blockers

This change records source inspection only. No new test suite was executed;
the previously recorded 25 isolated checks and three C-symbol object checks
remain the only successful checks claimed. No full Darling build, graphical
session, Logic installation, audio output or MIDI operation has been performed.

The missing native CGS window/event implementation and stubbed Carbon event
core are immediate code blockers. Full runtime/guest validation also requires
the appropriate Darling build environment and a display. Compatibility work
must record the actual commands, pinned revisions, logs and failures when those
checks become possible.
