# Carbon event metadata and lifetime

This batch implements event creation, immutable class/kind/time metadata and
retain/release ownership. It does not implement an event queue or dispatch.

## Behavior

- CreateEvent allocates a real opaque event, initially owned once by the caller.
  A null destination is rejected; failures leave a null output.
- Explicit timestamps are preserved. Zero uses GetCurrentEventTime, backed by
  CLOCK_MONOTONIC in seconds. Clock failure returns zero from that getter and
  causes zero-time creation to fail with unimpErr.
- The requested CF allocator is retained, used for allocation and final
  deallocation, and then released. A null allocator resolves the current default
  once, so later default changes cannot redirect deallocation.
- GetEventClass, GetEventKind and GetEventTime return stored values.
- RetainEvent, ReleaseEvent and GetEventRetainCount manage an atomic ItemCount.
  RetainEvent returns the same object; final release destroys it. Counter overflow
  is rejected with a null return.
- Null-event getters return zero, null retain returns null and null release is a
  no-op. These are defensive choices, not claims about undocumented Apple cases.
  Invalid pointers, double release and retaining an already destroyed event are
  unsupported.

The attributes input is stored for future work. Parameter get/set, event copies,
queue ownership and handler APIs are outside this batch and remain incomplete.
In particular, existing queue/handler/parameter stubs must not be mistaken for
functional implementations.

## Reproduce the host checks

Use a Linux Clang C toolchain and a checkout with the pinned CoreFoundation
submodule initialized. Select the actual installed Clang path through CC.

```sh
CC=clang-19 sh tests/regressions/carbon-events/run.sh
CC=clang-19 CXX=clang++-19 sh tests/regressions/carbon-contracts/run.sh
```

The new runner compiles the production CarbonEventsCore.c and real public
headers. It links a **test-only CF allocator adapter**, not CoreFoundation itself.
The adapter supplies CFRetain/CFRelease and the three allocator entry points
used by production code, tracks allocator ownership, and can fail an allocation.
It is deliberately limited to this host test. No replacement CF headers are used.

For a compatible installed AddressSanitizer runtime, optional invocation:

```sh
CC=clang-19 LINKER=gcc SANITIZE=address ASAN_OPTIONS=detect_leaks=1 \
  sh tests/regressions/carbon-events/run.sh
```

The existing contract runner now also links that adapter because the production
event source has real CF dependencies. The adapter is never part of HIToolbox's
production build; its existing CoreFoundation dependency supplies these symbols.

## Verification on 2026-10-15

Parent: c003abfdad4adebc327d8c5c1875d9761ef5b4d2, work/carbon-event-contracts.
Debian/WSL x86_64; workspace-local Clang 19.1.7, GCC 14.2.0 linker/runtime.
Headers use __APPLE_CC__=1, DEPLOYMENT_RUNTIME_SWIFT=1, POSIX feature declarations
and a forced include of the real basic-headers/MacTypes.h.

- A small creation probe returns exit 1 on the parent source: CreateEvent reports
  success but leaves the event null. On the patched source it creates an object
  preserving class/kind/time and exits 0. The probe uses only APIs present before
  this batch; missing new symbols were not counted as a behavioral regression.
- Delivered event runner: 54 checks, 0 failures, exit 0.
- Coverage: metadata, initial reference count, retained lifetime, final release,
  independent events, default/custom allocation, default-allocator change,
  allocation failure, zero-time monotonic bounds, and null-input behavior.
- Four threads each perform 10,000 balanced retain/release pairs while the main
  thread retains the original ownership. This is a stress check, not a proof of
  race freedom or a ThreadSanitizer run.
- AddressSanitizer with leak detection: the same 54 checks pass, exit 0, no
  reported memory errors. Compilation used local Clang; linking used the
  installed GCC AddressSanitizer runtime.
- Previous C11/C++17 signature runner passes, including wrong-callback rejection.
- nm on the host probe shows plain C names for CreateEvent, RetainEvent,
  ReleaseEvent, GetEventRetainCount, GetEventClass, GetEventKind, GetEventTime and
  GetCurrentEventTime.
- No new Windows or standalone-window test run is claimed for this batch.

CoreFoundation header pin: a3640a77410cf1825f7855172b1551ae7917c461; nested
Foundation: ea1ea0bb416025a8cc5a282df03c2e8f12788e2d.
The pinned Libc header at 5a38c8dabf9e76b39407c24bc13134e33e5594e6 declares
CLOCK_MONOTONIC and clock_gettime. Host clock checks use Linux's real clock.

Remaining blockers: real CoreFoundation allocator integration, full Darling
build and exported Mach-O libraries, i386 guest ABI and graphical/runtime
validation. Clock-failure and counter-overflow branches were not injected in
these tests. No Logic installation/execution, audio or MIDI validation occurred.

## Sources and credits

Prepared for fr4nck with OpenAI Codex. Existing Lubos Dolezel/Darling source
notices and history are retained; new regression files use GPL-3.0-or-later.
No external implementation was copied.

- [Apple Carbon Event Manager Reference, archived mirror](https://leopard-adc.pepas.com/documentation/Carbon/Reference/Carbon_Event_Manager_Ref/Reference/reference.html):
  API signatures, zero-time behavior and ownership contracts.
- [Pinned Darling Libc time.h](https://github.com/darlinghq/darling-Libc/blob/5a38c8dabf9e76b39407c24bc13134e33e5594e6/include/time.h):
  clock declarations available in the dependency.
- See root CREDITS.md and docs/logic8-progress.md for earlier work.
