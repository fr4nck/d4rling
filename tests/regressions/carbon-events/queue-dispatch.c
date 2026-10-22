/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <HIToolbox/CarbonEventsCore.h>
#include <CarbonCore/MacErrors.h>
#include "allocator-adapter.h"
#include <pthread.h>
#include <stdio.h>

static unsigned checks, failures;
#define CHECK(x) do { ++checks; if (!(x)) { ++failures; \
    fprintf(stderr, "FAIL %d: %s\n", __LINE__, #x); } } while (0)
#define CLASS_A 0x74657374u
static EventTypeSpec type = { CLASS_A, 1 };
static int trace[64], used;
static EventHandlerRef victim, self;
static EventHandlerCallRef expired;
static EventTargetRef target;

static EventRef Make(UInt32 kind)
{
    EventRef event = NULL;
    CHECK(CreateEvent(NULL, CLASS_A, kind, 1.0, 0, &event) == noErr);
    return event;
}
static OSStatus Bottom(EventHandlerCallRef call, EventRef event, void* data)
{
    (void)call; (void)event;
    trace[used++] = *(int*)data;
    return noErr;
}
static OSStatus Decline(EventHandlerCallRef call, EventRef event, void* data)
{
    (void)call; (void)event;
    trace[used++] = *(int*)data;
    return eventNotHandledErr;
}
static OSStatus Error(EventHandlerCallRef call, EventRef event, void* data)
{
    (void)call; (void)event; (void)data;
    trace[used++] = 8;
    return -12345;
}
static OSStatus Next(EventHandlerCallRef call, EventRef event, void* data)
{
    (void)data;
    expired = call;
    trace[used++] = 3;
    CHECK(CallNextEventHandler(NULL, event) == paramErr);
    CHECK(CallNextEventHandler(call, NULL) == paramErr);
    CHECK(CallNextEventHandler(call, event) == noErr);
    CHECK(CallNextEventHandler(call, event) == noErr); /* no duplicate delivery */
    trace[used++] = 4;
    return noErr;
}
static OSStatus RemoveDuringSend(EventHandlerCallRef call, EventRef event, void* data)
{
    (void)call; (void)event; (void)data;
    trace[used++] = 5;
    CHECK(RemoveEventHandler(victim) == noErr);
    CHECK(RemoveEventHandler(self) == noErr);
    return eventNotHandledErr;
}
static OSStatus ReleaseCaller(EventHandlerCallRef call, EventRef event, void* data)
{
    (void)call; (void)data;
    ReleaseEvent(event); /* Drop caller's ref; dispatch still owns one. */
    CHECK(GetEventKind(event) == 1);
    CHECK(GetEventRetainCount(event) == 1);
    return noErr;
}
static OSStatus Nested(EventHandlerCallRef call, EventRef event, void* data)
{
    int* depth = data;
    trace[used++] = 6;
    if (!*depth) {
        *depth = 1;
        CHECK(SendEventToEventTarget(event, target) == noErr);
        *depth = 0;
    }
    CHECK(CallNextEventHandler(call, event) == noErr);
    return noErr;
}
static OSStatus InstallDuringSend(EventHandlerCallRef call, EventRef event, void* data)
{
    (void)call; (void)event;
    CHECK(InstallEventHandler(target, Bottom, 1, &type, data, &victim) == noErr);
    return eventNotHandledErr;
}
static void ReentrantPost(void* data)
{
    CHECK(PostEventToQueue(GetMainEventQueue(), data, 1) == noErr);
}
static void ReentrantTarget(void* data)
{
    EventHandlerRef ref = (void*)1;
    CHECK(InstallEventHandler(target, Error, 1, &type, NULL, &ref)
          == eventTargetBusyErr && !ref);
    CHECK(RemoveEventHandler(victim) == eventTargetBusyErr);
    CHECK(SendEventToEventTarget(data, target) == eventTargetBusyErr);
}
static void* OtherThread(void* data)
{
    EventRef event = data;
    /* No CHECK here: return a result, checked after join. */
    EventHandlerRef ref = (void*)1;
    if (InstallEventHandler(target, Bottom, 1, &type, NULL, &ref) != unimpErr || ref)
        return (void*)1;
    if (SendEventToEventTarget(event, target) != unimpErr)
        return (void*)2;
    if (RemoveEventHandler(victim) != unimpErr)
        return (void*)3;
    if (PostEventToQueue(GetMainEventQueue(), event, kEventPriorityStandard) != noErr)
        return (void*)4;
    return NULL;
}
int main(void)
{
    CFAllocatorRef allocator = test_default_allocator();
    CFAllocatorRef custom = test_custom_allocator();
    EventQueueRef queue = GetMainEventQueue();
    target = GetApplicationEventTarget();
    CHECK(queue && queue == GetMainEventQueue());
    CHECK(target && target == GetApplicationEventTarget());
    EventRef out = (void*)1;
    CHECK(ReceiveNextEvent(0, NULL, 0, 1, &out) == eventLoopTimedOutErr && !out);
    EventRef a = Make(1), b = Make(2), c = Make(3), d = Make(4);
    CHECK(PostEventToQueue(NULL, a, 1) == paramErr);
    CHECK(PostEventToQueue(queue, NULL, 1) == paramErr);
    CHECK(PostEventToQueue(queue, a, -1) == paramErr);
    CHECK(PostEventToQueue(queue, a, 3) == paramErr);
    test_fail_next_allocation();
    CHECK(PostEventToQueue(queue, a, 1) == memFullErr);
    CHECK(GetEventRetainCount(a) == 1);
    CHECK(PostEventToQueue(queue, a, kEventPriorityStandard) == noErr);
    CHECK(PostEventToQueue(queue, a, kEventPriorityHigh) == eventAlreadyPostedErr);
    CHECK(GetEventRetainCount(a) == 2);
    CHECK(PostEventToQueue(queue, b, kEventPriorityLow) == noErr);
    CHECK(PostEventToQueue(queue, c, kEventPriorityHigh) == noErr);
    CHECK(PostEventToQueue(queue, d, kEventPriorityStandard) == noErr);
    CHECK(ReceiveNextEvent(0, NULL, 0, 0, &out) == noErr && out == c);
    CHECK(GetEventRetainCount(c) == 2); /* borrowed peek */
    CHECK(ReceiveNextEvent(0, NULL, 0, 0, &out) == noErr && out == c);
    CHECK(GetEventRetainCount(c) == 2);
    CHECK(ReceiveNextEvent(1, NULL, 0, 1, &out) == paramErr && !out);
    CHECK(ReceiveNextEvent(0, NULL, 0, 1, NULL) == paramErr);
    CHECK(ReceiveNextEvent(0, NULL, 1, 1, &out) == unimpErr && !out);
    CHECK(ReceiveNextEvent(0, NULL, kEventDurationForever, 1, &out) == unimpErr && !out);
    EventTypeSpec missing = { CLASS_A, 9 };
    CHECK(ReceiveNextEvent(1, &missing, 0, 1, &out) == eventLoopTimedOutErr && !out);
    EventTypeSpec list[] = { {CLASS_A, 8}, {CLASS_A, 2} };
    CHECK(ReceiveNextEvent(2, list, 0, 1, &out) == noErr && out == b);
    CHECK(GetEventRetainCount(b) == 2);
    ReleaseEvent(out);
    CHECK(GetEventRetainCount(b) == 1);
    CHECK(ReceiveNextEvent(0, NULL, 0, 1, &out) == noErr && out == c);
    ReleaseEvent(out);
    CHECK(ReceiveNextEvent(0, NULL, 0, 1, &out) == noErr && out == a);
    ReleaseEvent(out);
    CHECK(ReceiveNextEvent(0, NULL, 0, 1, &out) == noErr && out == d);
    ReleaseEvent(out);
    CHECK(ReceiveNextEvent(0, NULL, 0, 1, &out) == eventLoopTimedOutErr && !out);
    test_set_allocation_hook(ReentrantPost, a);
    CHECK(PostEventToQueue(queue, a, 1) == eventAlreadyPostedErr);
    CHECK(GetEventRetainCount(a) == 2);
    CHECK(ReceiveNextEvent(0, NULL, 0, 1, &out) == noErr && out == a);
    ReleaseEvent(out);
    CHECK(GetEventRetainCount(a) == 1);
    ReleaseEvent(b); ReleaseEvent(c); ReleaseEvent(d);

    EventRef owned = NULL;
    CHECK(CreateEvent(custom, CLASS_A, 1, 2.0, 0, &owned) == noErr);
    int payload = 123, result = 0;
    CHECK(SetEventParameter(owned, 1, 2, sizeof(payload), &payload) == noErr);
    CHECK(PostEventToQueue(queue, owned, 1) == noErr);
    ReleaseEvent(owned); /* Queue is now sole owner. */
    CHECK(ReceiveNextEvent(0, NULL, 0, 1, &out) == noErr);
    CHECK(GetEventRetainCount(out) == 1);
    CHECK(GetEventParameter(out, 1, 2, NULL, sizeof(result), NULL, &result) == noErr);
    CHECK(result == 123);
    ReleaseEvent(out);
    CHECK(test_allocations(custom) == test_frees(custom));
    CHECK(test_references(custom) == 1);

    CHECK(NewEventHandlerUPP(Bottom) == Bottom);
    CHECK(NewEventHandlerUPP(NULL) == NULL);
    CHECK(CallNextEventHandler(NULL, a) == paramErr);
    CHECK(SendEventToEventTarget(a, target) == eventNotHandledErr);
    CHECK(SendEventToEventTarget(NULL, target) == paramErr);
    CHECK(SendEventToEventTarget(a, NULL) == paramErr);
    EventHandlerRef h1 = (void*)1, h2 = NULL, h3 = NULL;
    int one = 1, two = 2;
    CHECK(InstallEventHandler(NULL, Bottom, 1, &type, &one, &h1) == paramErr && !h1);
    CHECK(InstallEventHandler(target, NULL, 1, &type, &one, &h1) == paramErr && !h1);
    CHECK(InstallEventHandler(target, Bottom, 1, NULL, &one, &h1) == paramErr && !h1);
    CHECK(InstallEventHandler(target, Bottom, (ItemCount)-1, &type, &one, &h1)
          == memFullErr && !h1);
    test_fail_next_allocation();
    CHECK(InstallEventHandler(target, Bottom, 1, &type, &one, &h1) == memFullErr && !h1);
    CHECK(test_references(allocator) == 2); /* only a owns allocator */
    EventTypeSpec mutable = type;
    CHECK(InstallEventHandler(target, Bottom, 1, &mutable, &one, &h1) == noErr && h1);
    mutable.eventKind = 77;
    victim = h1;
    test_set_allocation_hook(ReentrantTarget, a);
    CHECK(InstallEventHandler(target, Error, 0, NULL, NULL, &h3) == noErr);
    CHECK(RemoveEventHandler(h3) == noErr);
    test_set_allocation_hook(ReentrantTarget, a);
    used = 0;
    CHECK(SendEventToEventTarget(a, target) == noErr && used == 1);
    CHECK(InstallEventHandler(target, Bottom, 1, &type, &two, &h2)
          == eventHandlerAlreadyInstalledErr && !h2);
    CHECK(InstallEventHandler(target, Decline, 1, &type, &two, &h2) == noErr);
    used = 0;
    CHECK(SendEventToEventTarget(a, target) == noErr);
    CHECK(used == 2 && trace[0] == 2 && trace[1] == 1);
    CHECK(GetEventRetainCount(a) == 1);
    test_fail_next_allocation();
    used = 0;
    CHECK(SendEventToEventTarget(a, target) == memFullErr && used == 0);
    CHECK(GetEventRetainCount(a) == 1);
    CHECK(InstallEventHandler(target, Error, 1, &type, NULL, &h3) == noErr);
    used = 0;
    CHECK(SendEventToEventTarget(a, target) == -12345);
    CHECK(used == 1 && trace[0] == 8);
    CHECK(RemoveEventHandler(h3) == noErr);
    CHECK(RemoveEventHandler(h2) == noErr);
    CHECK(InstallEventHandler(target, Next, 1, &type, NULL, &h2) == noErr);
    used = 0;
    CHECK(SendEventToEventTarget(a, target) == noErr);
    CHECK(used == 3 && trace[0] == 3 && trace[1] == 1 && trace[2] == 4);
    CHECK(CallNextEventHandler(expired, a) == paramErr);
    CHECK(RemoveEventHandler(h2) == noErr);
    victim = h1;
    CHECK(InstallEventHandler(target, RemoveDuringSend, 1, &type, NULL, &self) == noErr);
    used = 0;
    CHECK(SendEventToEventTarget(a, target) == eventNotHandledErr);
    CHECK(used == 1 && trace[0] == 5);
    CHECK(RemoveEventHandler(NULL) == paramErr);
    CHECK(RemoveEventHandler(self) == paramErr); /* token compared, not dereferenced */

    CHECK(InstallEventHandler(target, Bottom, 1, &type, &one, &h1) == noErr);
    int depth = 0;
    CHECK(InstallEventHandler(target, Nested, 1, &type, &depth, &h2) == noErr);
    used = 0;
    CHECK(SendEventToEventTarget(a, target) == noErr);
    CHECK(used == 4 && trace[0] == 6 && trace[1] == 6 && trace[2] == 1 && trace[3] == 1);
    CHECK(RemoveEventHandler(h2) == noErr);
    CHECK(RemoveEventHandler(h1) == noErr);

    CHECK(InstallEventHandler(target, InstallDuringSend, 1, &type, &one, &h1) == noErr);
    used = 0;
    CHECK(SendEventToEventTarget(a, target) == eventNotHandledErr && used == 0);
    CHECK(RemoveEventHandler(h1) == noErr);
    h1 = victim;
    used = 0;
    CHECK(SendEventToEventTarget(a, target) == noErr && used == 1);
    pthread_t thread;
    int started = pthread_create(&thread, NULL, OtherThread, a);
    CHECK(started == 0);
    if (!started) {
        void* status = (void*)1;
        CHECK(pthread_join(thread, &status) == 0 && status == NULL);
        CHECK(ReceiveNextEvent(0, NULL, 0, 1, &out) == noErr && out == a);
        ReleaseEvent(out);
    }
    CHECK(RemoveEventHandler(h1) == noErr);
    CHECK(InstallEventHandler(target, ReleaseCaller, 1, &type, NULL, &h1) == noErr);
    CHECK(SendEventToEventTarget(a, target) == noErr); /* a now destroyed */
    CHECK(RemoveEventHandler(h1) == noErr);
    CHECK(test_allocations(allocator) == test_frees(allocator));
    CHECK(test_references(allocator) == 1);
    CHECK(ReceiveNextEvent(0, NULL, 0, 1, &out) == eventLoopTimedOutErr && !out);
    printf("Carbon queue/dispatch checks: %u | Failures: %u\n", checks, failures);
    return failures ? 1 : 0;
}
