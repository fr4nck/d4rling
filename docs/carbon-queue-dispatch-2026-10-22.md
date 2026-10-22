# Carbon main queue and synchronous application handlers — first bounded lot

Base: `10d0e885ffd8133256d6e657065d35ba64b8deb7` (master, PR #2 merge).
Implementation and host qualification: 2026-10-22, isolated Linux x86_64 container.
No binary/dependency downloads, package installations, Windows access or Logic execution.
The GitHub connector supplied the inspected repository text; this is a sparse
source subset, not a full Darling checkout with initialized dependencies.

## Contract review and resulting behavior

The original Apple [Carbon Event Manager Reference (2007-10-31)](https://leopard-adc.pepas.com/documentation/Carbon/Reference/Carbon_Event_Manager_Ref/Reference/reference.html)
was read for PostEventToQueue, ReceiveNextEvent, InstallEventHandler,
CallNextEventHandler, SendEventToEventTarget, priorities and result codes.
Existing source, public declarations, HIToolbox's CMake source/dependency list,
CarbonEvents.c, Events.cpp, MacApplication.cpp and regression ownership tests
were inspected. No external implementation was copied.

| API or behavior | Implemented scope |
| --- | --- |
| GetMainEventQueue | Stable process-wide opaque queue, mutex-protected membership. |
| PostEventToQueue | Retains once; high/standard/low priorities (2/1/0); FIFO within each priority; duplicate EventRef rejected with eventAlreadyPostedErr. |
| ReceiveNextEvent | No-wait only; exact class/kind lists, or any event with count zero; returns eventLoopTimedOutErr when no match. |
| Peek versus pull | Peek borrows the queue's reference without incrementing it. Pull transfers that reference to the caller, who must release it. |
| GetApplicationEventTarget | Stable application target; its first getter binds the supported handler thread. |
| InstallEventHandler | Copies the type list; stores callback and borrowed userData; overlapping registration of the same callback rejected. A zero-length list registers no types. outRef may be null. |
| SendEventToEventTarget | Synchronous matching handlers, newest installation first. eventNotHandledErr continues; success or another error stops. No match returns eventNotHandledErr. |
| CallNextEventHandler | Valid only in the current callback, for the same event. Continues the saved chain; repeat calls return the cached result without redelivery. |
| RemoveEventHandler | Unlinks immediately; in-flight snapshots retain storage until safe to free. Self-removal and removal of a later callback are supported. |

Queue nodes use the event's original allocator. On post allocation failure,
queue contents and the event's ownership remain unchanged. Allocator callbacks
run outside the queue mutex; a second duplicate check handles reentry/competing
posts. A pulled node is freed before returning to the caller.

Handler storage and dispatch snapshots retain their chosen default allocator
until deallocation. A snapshot retains matching handler records and the event
for callback execution. Newly installed handlers are absent from that snapshot;
removed handlers are skipped. Nested sends have independent snapshots and call
contexts. Allocator reentry during handler-storage allocation returns
eventTargetBusyErr from target mutation/send APIs, protecting the counted list.
Failure to allocate an installation or snapshot returns memFullErr, with no
callback delivery, partially installed handler or leaked ownership.

UserData is borrowed: the caller must keep it alive for callbacks, including
in-flight execution. Handlers must not release references they do not own.
The framework tolerates a callback releasing its caller-owned event reference
because dispatch itself temporarily retains that event. Event payload mutation
still has the original same-event thread-safety limitations.

## Executed qualification

[Observed outputs and tested source hashes](../tests/regressions/carbon-events/qualification-2026-10-22.txt)
are committed with this record. The parent/patched probe source is
`tests/regressions/carbon-events/queue-baseline-probe.c`.

GCC 13.3.0 (Ubuntu 13.3.0-6ubuntu2~24.04), C11, Linux x86_64.
Both configurations compile the **unchanged production source** and the actual
CarbonEventsCore.h. They substitute the explicitly named `isolated/` dependency
headers (CFBase, MacTypes, Menus, MacErrors) and test-only CF allocator adapter.
This is NOT a test with the full real Darling dependency headers or CF runtime.

| Executed check | Result |
| --- | --- |
| GCC C11, -Wall -Wextra -Werror | 54 event + 67 parameter + 125 queue/dispatch assertions = **246 PASS, 0 FAIL**, exit 0. |
| GCC ASan + UBSan, halt on error | Same **246 PASS, 0 FAIL**, exit 0; no sanitizer diagnostics. Leak detection explicitly disabled for this run. |
| GCC -fanalyzer on production source, same dependency fixtures | Exit 0, no diagnostics. This is static analysis, not runtime coverage. |
| Parent/patched queue behavioral probe | Parent: 4 checks, 3 failures, exit 1. Patched: 4 checks, 0 failures, exit 0. |
| git diff --check | Exit 0. |

The two matrix rows total 492 executed assertions; they are repetitions of 246
checks, not 492 distinct behaviors. The old 484-assertion PR #2 qualification is
historical and is not relabelled as a fresh full-runtime test here.

Coverage includes priority/FIFO order, filtering through skipped entries,
repeat borrowed peeks, queue-only lifetime and payload survival, duplicate posts,
post/installation/snapshot allocation failure, copied handler type lists,
handler order and stop/error/fallback results, explicit next-handler chaining,
expired tokens outside callbacks, self/other removal, nested sends, installation
during delivery, cross-thread target rejection and cross-thread queue posting,
allocator reentry and final allocation/free/reference balances.
The existing four-thread event-retain stress remains part of the 54-event checks.
No ThreadSanitizer or proof of race freedom is claimed.

The behavioral probe uses only pre-existing APIs: create an event; verify a
non-null main queue; post and require retain count 2; pull and require the same
event. Baseline compilation initially hit its existing unused-parameter warnings
with -Werror; both comparison builds therefore used -Wno-unused-parameter.
The parent fails by behavior (null queue, missing retain, missing received event),
not by missing new symbols.

Reproduce the executed matrix from the repository root:

```sh
CC=gcc sh tests/regressions/carbon-events/run-isolated.sh
CC=gcc SANITIZE=address,undefined \
  ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 \
  UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
  sh tests/regressions/carbon-events/run-isolated.sh

gcc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror \
  -fanalyzer -pthread -Itests/regressions/carbon-events/isolated \
  -Isrc/frameworks/Carbon/HIToolbox/include \
  -c src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c \
  -o /tmp/carbon-events-analyzer.o
```

### Blocked or unexecuted controls

The ASan+UBSan invocation with `detect_leaks=1` was attempted and exited 1:
LeakSanitizer could not read `/proc/.../task` and reported a fatal container /
ptrace-environment error. It did not produce a usable leak analysis. Allocation /
free and retained-allocator balances pass in the adapter, which supplements but
does not replace a successful LeakSanitizer run.

Clang is unavailable locally and was not downloaded. The existing real-dependency
runner `run.sh` now includes queue-dispatch.c but was NOT executed here: pinned
CoreFoundation and the full Darling headers are unavailable. No C++17 real-header
runner, 32-bit check, full Darling build, Mach-O export check or actual CF runtime
integration was executed. CMake integration was inspected only: CarbonEventsCore.c
is already in HIToolbox's source list and `system` is already a dependency.

## Explicit limits and next qualification

- Only the process main queue exists. ReceiveNextEvent reads it on the calling
  thread; per-thread queues/current event-loop semantics are not implemented.
- All nonzero timeouts, including forever, return unimpErr without consuming
  events. There is no CFRunLoop integration, timer firing, native input pump or
  event-loop wakeup. The no-wait queue implementation does not claim those parts
  of Apple's PostEventToQueue contract.
- A peek is borrowed; synchronize against another thread pulling/releasing it,
  or pull first to obtain ownership. Mutex membership safety alone cannot make
  a borrowed pointer live indefinitely.
- Handler installation/removal/send only support the thread that first obtained
  the application target. Other threads return unimpErr. This binding is a
  temporary implementation restriction, not identification of Darwin's main thread.
- Only exact class/kind matching is qualified; no wildcard matching, standard
  handlers, target hierarchy, window/control/menu targets, dispatcher routing,
  send-to-all options, dynamic event-type editing or target disposal is provided.
- Repeated CallNextEventHandler calls are deliberately cached; replay semantics,
  foreign/expired tokens during another callback and changing the event passed
  to CallNextEventHandler are not supported compatibility claims.
- Invalid EventRef pointers, double releases, stale handler handles after memory
  reuse, unbounded recursive callbacks, nonlocal exits across callbacks and
  application shutdown cleanup are outside this lot. Unremoved handlers and
  unpulled events remain owned by the process-lifetime target/queue.

Next: run the real-header regression matrix with an already available Clang /
Darling checkout, then real CoreFoundation and Mach-O integration. Add per-thread
queues and real CFRunLoop waiting before attempting application event-loop or
window-dispatch qualification. This lot does not validate Darling as a whole,
Logic Studio 8, graphical rendering, audio or MIDI.
