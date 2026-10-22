# Carbon event objects, metadata, lifetime and parameters

The original 2026-10-15 batch implemented event creation, immutable
class/kind/time metadata and retain/release ownership. The subsequent
2026-10-18 parameter/copy extension is documented below. Neither batch
implements an event queue or dispatch.

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

The original 2026-10-15 batch stored attributes but did not yet implement event
parameters or copies. The later parameter/copy extension is described below;
queue ownership and event handler APIs remain incomplete. Existing queue and
handler stubs must not be mistaken for working implementations.

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


## Typed parameters and event copies (2026-10-18, GitHub-only)

The second lot replaces the false-success GetEventParameter stub, implements
SetEventParameter, RemoveEventParameter and CopyEvent, and declares the historical
functions in CarbonEventsCore.h. The redundant SetEventParameter declaration in
Events.h has been removed. Carbon's missing-parameter error is -9870.

An event owns all parameter storage, including independent copies of binary
bytes. Each allocation reserves at least sizeof(struct EventParameter), including
potential tail padding even for zero-length values. Replacement allocates
before dropping old data, preserving the old value
on out-of-memory errors. Zero-length values, multiple names, deletion and
size/type query (NULL buffer only with zero buffer size) are implemented.
GetEventParameter supports exact type and OSType wildcard '****'. It rejects
undersized buffers without partial copying and reports a nonzero error on
incompatible types. AppleEvent type coercion handlers are NOT implemented.
The error mappings for failed coercion (errAECoercionFail) and small buffers
(errAEBufferTooSmall) are provisional pending comparison with real macOS.

CopyEvent uses the original allocator and creates an independent event and
parameter records with initial retain count 1. Copy failure releases all
partially copied records. Final ReleaseEvent frees every parameter before its
event. Pointer-valued payloads are copied as raw bytes; objects they point to
are not deep-copied. Apple's contract does not make concurrent mutation of
the *same* event thread-safe. The existing atomic event retain/release semantics
are not changed. Invalid/dangling EventRef addresses cannot be safely checked.

Host reproduction, with pinned real Darling headers and the test-only
CoreFoundation allocator adapter (NOT the real CF runtime):

    CC=clang-19 sh tests/regressions/carbon-events/run.sh

The runner now includes an independent parameters.c test executable covering
binary data, replacement, wrong type, removal, zero data, size queries,
insufficient buffers, allocator failure injection, copy independence and cleanup.
Optional ASan invocation above also applies to both executables.

NEW VERIFICATION STATUS: NON EXÉCUTÉ. This GitHub-only session cannot compile
or run the submitted tests. Earlier 54 successful checks and ASan results
belong to 2026-10-15; they are not newly claimed. Full Darling/Mach-O builds,
actual CoreFoundation integration, 32-bit ABI, event dispatch and Logic Studio 8
remain out of scope.

Sources: Apple MacOSX10.6.sdk CarbonEventsCore.h (as preserved by
phracker/MacOSX-SDKs), and the archived Apple Carbon Event Manager Reference
linked above. Licences and original source notices are preserved.


## Main queue and bounded synchronous dispatch (2026-10-22)

The post-PR #2 lot adds a prioritized process queue, no-wait receive (borrowed
peek / owned pull), and synchronous application-target handlers. This supersedes
the earlier description of these APIs as success-returning stubs, within the
explicit scope of the [qualification record](../../../docs/carbon-queue-dispatch-2026-10-22.md).

Executed here: GCC C11 **246 PASS / 0 FAIL**; GCC ASan+UBSan **246 PASS / 0 FAIL**
with leak detection disabled. Each row comprises 54 original event checks,
67 parameter checks and 125 queue/dispatch checks. Production source and the
real CarbonEventsCore.h are compiled, but this new isolated runner substitutes
small dependency headers and the test-only CF adapter. It does not establish
SDK/ABI or real CF compatibility. LeakSanitizer was attempted but blocked by the
container. Clang and the full real-dependency runner were not executed here.

    CC=gcc sh tests/regressions/carbon-events/run-isolated.sh

The existing `run.sh` includes the new executable for future qualification with
the real pinned dependencies. The isolated fixture headers are never included
by the production CMake build or the real-dependency runner. The dated 2026-10-18
NON EXÉCUTÉ section above records the original submission session; it is not the
current result of this isolated follow-up.
