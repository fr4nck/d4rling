/* SPDX-License-Identifier: GPL-3.0-or-later
 * Prepared with OpenAI Codex for fr4nck. No graphical runtime required.
 */
#include <HIToolbox/CarbonEventsCore.h>
#include <CarbonCore/MacErrors.h>
#include "allocator-adapter.h"
#include <pthread.h>
#include <stdio.h>
#include <time.h>

static unsigned checks, failures;
#define CHECK(condition) do { ++checks; if (!(condition)) { ++failures; \
    fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #condition); } } while (0)

static void* retain_worker(void* context)
{
    EventRef event = context;
    for (unsigned i = 0; i < 10000; ++i) {
        if (RetainEvent(event) != event)
            return (void*)1;
        ReleaseEvent(event);
    }
    return NULL;
}

int main(void)
{
    CFAllocatorRef defaults = test_default_allocator();
    CFAllocatorRef custom = test_custom_allocator();
    EventRef event = NULL, other = NULL;
    CHECK(CreateEvent(NULL, 0x74657374u, 0x12345678u, 12.25, 0, NULL) == paramErr);
    CHECK(CreateEvent(NULL, 0x74657374u, 0x12345678u, 12.25, 0, &event) == noErr);
    CHECK(event != NULL);
    if (!event) return 1; /* Baseline stub must fail without dereferencing a sentinel. */
    CHECK(GetEventClass(event) == 0x74657374u);
    CHECK(GetEventKind(event) == 0x12345678u);
    CHECK(GetEventTime(event) == 12.25);
    CHECK(GetEventRetainCount(event) == 1);
    CHECK(test_allocations(defaults) == 1);
    CHECK(test_references(defaults) == 2);

    CHECK(RetainEvent(event) == event);
    CHECK(GetEventRetainCount(event) == 2);
    ReleaseEvent(event);
    CHECK(GetEventRetainCount(event) == 1);
    CHECK(GetEventKind(event) == 0x12345678u);
    CHECK(test_frees(defaults) == 0);

    CHECK(CreateEvent(custom, 0x6f746872u, 9, 88.5, 1, &other) == noErr);
    CHECK(other != NULL && other != event);
    CHECK(GetEventTime(other) == 88.5);
    CHECK(GetEventClass(event) == 0x74657374u);
    CHECK(test_allocations(custom) == 1);
    CHECK(test_references(custom) == 2);
    ReleaseEvent(other);
    CHECK(test_frees(custom) == 1);
    CHECK(test_references(custom) == 1);

    pthread_t threads[4];
    unsigned started = 0;
    for (; started < 4; ++started) {
        int result = pthread_create(&threads[started], NULL, retain_worker, event);
        CHECK(result == 0);
        if (result != 0) break;
    }
    for (unsigned i = 0; i < started; ++i) {
        void* result = (void*)1;
        CHECK(pthread_join(threads[i], &result) == 0);
        CHECK(result == NULL);
    }
    CHECK(GetEventRetainCount(event) == 1);
    CHECK(GetEventTime(event) == 12.25);

    /* Changing the default must not change the allocator of an existing event. */
    test_set_default(custom);
    ReleaseEvent(event);
    CHECK(test_frees(defaults) == 1);
    CHECK(test_references(defaults) == 1);
    CHECK(test_frees(custom) == 1);
    test_set_default(defaults);

    other = NULL;
    EventTime before = GetCurrentEventTime();
    CHECK(CreateEvent(NULL, 1, 2, 0, 0, &other) == noErr);
    EventTime after = GetCurrentEventTime();
    struct timespec native;
    CHECK(clock_gettime(CLOCK_MONOTONIC, &native) == 0);
    EventTime nativeTime = (EventTime)native.tv_sec + native.tv_nsec / 1000000000.0;
    CHECK(before > 0 && before <= after && after <= nativeTime);
    CHECK(GetEventTime(other) >= before && GetEventTime(other) <= after);
    ReleaseEvent(other);
    CHECK(test_allocations(defaults) == test_frees(defaults));

    /* Failure must clear output and balance the temporary allocator retain. */
    other = (EventRef)(void*)&other;
    test_fail_next_allocation();
    CHECK(CreateEvent(custom, 1, 2, 1, 0, &other) == memFullErr);
    CHECK(other == NULL);
    CHECK(test_references(custom) == 1);
    CHECK(test_allocations(custom) == test_frees(custom));

    CHECK(RetainEvent(NULL) == NULL);
    CHECK(GetEventRetainCount(NULL) == 0);
    CHECK(GetEventClass(NULL) == 0);
    CHECK(GetEventKind(NULL) == 0);
    CHECK(GetEventTime(NULL) == 0);
    ReleaseEvent(NULL);
    CHECK(test_references(defaults) == 1 && test_references(custom) == 1);
    printf("Checks: %u | Failures: %u\n", checks, failures);
    return failures ? 1 : 0;
}
