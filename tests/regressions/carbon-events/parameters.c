/* SPDX-License-Identifier: GPL-3.0-or-later
 * Host-only tests using real CarbonEventsCore.c and the identified test CF adapter.
 */
#include <HIToolbox/CarbonEventsCore.h>
#include <CarbonCore/MacErrors.h>
#include "allocator-adapter.h"
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#define NAME_A 0x70617261u
#define NAME_B 0x70617262u
#define NAME_EMPTY 0x656d7074u
#define TYPE_A 0x72617731u
#define TYPE_B 0x72617732u
#define WILDCARD 0x2a2a2a2au

static unsigned checks, failures;
#define CHECK(condition) do { ++checks; if (!(condition)) { ++failures; \
    fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #condition); } } while (0)

int main(void)
{
    CFAllocatorRef def = test_default_allocator(), custom = test_custom_allocator();
    EventRef event = NULL, copy = NULL;
    unsigned char data[] = {0, 0xfe, 3, 0, 0x7f};
    unsigned char out[sizeof(data)] = {0};
    ByteCount size = 42;
    EventParamType type = TYPE_B;

    CHECK(CreateEvent(NULL, 0x74657374u, 17, 42.5, 3, &event) == noErr);
    CHECK(event != NULL);
    if (!event) return 1;

    CHECK(GetEventParameter(event, NAME_A, TYPE_A, &type, 0, &size, NULL)
          == eventParameterNotFoundErr);
    CHECK(type == 0 && size == 0);
    CHECK(SetEventParameter(NULL, NAME_A, TYPE_A, sizeof(data), data) == paramErr);
    CHECK(SetEventParameter(event, NAME_A, TYPE_A, sizeof(data), NULL) == paramErr);
    CHECK(GetEventParameter(NULL, NAME_A, TYPE_A, NULL, 0, NULL, NULL) == paramErr);
    CHECK(GetEventParameter(event, NAME_A, TYPE_A, NULL, sizeof(out), NULL, NULL) == paramErr);
    CHECK(RemoveEventParameter(NULL, NAME_A) == paramErr);
    CHECK(RemoveEventParameter(event, NAME_A) == eventParameterNotFoundErr);
    CHECK(CopyEvent(NULL) == NULL);

    CHECK(SetEventParameter(event, NAME_A, TYPE_A, sizeof(data), data) == noErr);
    data[0] = 0xaa; /* Caller may overwrite its buffer immediately. */
    CHECK(GetEventParameter(event, NAME_A, TYPE_A, &type, 0, &size, NULL) == noErr);
    CHECK(type == TYPE_A && size == sizeof(data));
    CHECK(GetEventParameter(event, NAME_A, WILDCARD, &type, sizeof(out), &size, out) == noErr);
    CHECK(type == TYPE_A && size == sizeof(out));
    CHECK(out[0] == 0 && out[1] == 0xfe && out[2] == 3 && out[3] == 0 && out[4] == 0x7f);

    unsigned char tiny[2] = {0x7c, 0x7d};
    CHECK(GetEventParameter(event, NAME_A, TYPE_A, &type, sizeof(tiny), &size, tiny)
          == errAEBufferTooSmall);
    CHECK(size == sizeof(out) && type == TYPE_A);
    CHECK(tiny[0] == 0x7c && tiny[1] == 0x7d);
    CHECK(GetEventParameter(event, NAME_A, TYPE_B, &type, sizeof(out), &size, out)
          == errAECoercionFail);
    CHECK(type == TYPE_A && size == sizeof(out));

    uint32_t number = 0xfeed1234u, gotNumber = 0;
    CHECK(SetEventParameter(event, NAME_B, TYPE_B, sizeof(number), &number) == noErr);
    CHECK(GetEventParameter(event, NAME_B, TYPE_B, NULL, sizeof(gotNumber), NULL, &gotNumber)
          == noErr);
    CHECK(gotNumber == number);
    CHECK(SetEventParameter(event, NAME_EMPTY, TYPE_A, 0, NULL) == noErr);
    size = 99;
    CHECK(GetEventParameter(event, NAME_EMPTY, TYPE_A, NULL, 0, &size, NULL) == noErr);
    CHECK(size == 0);
    CHECK(GetEventParameter(event, NAME_EMPTY, TYPE_A, NULL, 0, NULL, out) == noErr);

    copy = CopyEvent(event);
    CHECK(copy != NULL && copy != event);
    if (!copy) { ReleaseEvent(event); return 1; }
    CHECK(GetEventClass(copy) == GetEventClass(event));
    CHECK(GetEventKind(copy) == GetEventKind(event));
    CHECK(GetEventTime(copy) == GetEventTime(event));
    CHECK(GetEventRetainCount(copy) == 1 && GetEventRetainCount(event) == 1);
    CHECK(test_references(def) == 3);

    unsigned char replacement[] = {7, 8, 9};
    CHECK(SetEventParameter(event, NAME_A, TYPE_B, sizeof(replacement), replacement) == noErr);
    CHECK(GetEventParameter(event, NAME_A, TYPE_B, &type, sizeof(out), &size, out) == noErr);
    CHECK(type == TYPE_B && size == sizeof(replacement) && out[0] == 7 && out[2] == 9);
    CHECK(GetEventParameter(copy, NAME_A, TYPE_A, &type, sizeof(out), &size, out) == noErr);
    CHECK(type == TYPE_A && size == sizeof(data) && out[0] == 0 && out[1] == 0xfe);
    CHECK(RemoveEventParameter(event, NAME_B) == noErr);
    CHECK(GetEventParameter(event, NAME_B, TYPE_B, NULL, 0, NULL, NULL)
          == eventParameterNotFoundErr);
    CHECK(GetEventParameter(copy, NAME_B, TYPE_B, NULL, sizeof(gotNumber), NULL, &gotNumber)
          == noErr && gotNumber == number);

    test_fail_next_allocation();
    CHECK(SetEventParameter(copy, NAME_A, TYPE_A, sizeof(replacement), replacement)
          == memFullErr);
    CHECK(GetEventParameter(copy, NAME_A, TYPE_A, NULL, sizeof(out), NULL, out) == noErr);
    CHECK(out[0] == 0 && out[1] == 0xfe && out[4] == 0x7f);

    unsigned a0 = test_allocations(def), f0 = test_frees(def);
    test_fail_allocation_after(1);
    CHECK(CopyEvent(copy) == NULL);
    CHECK(test_allocations(def) == a0 + 1 && test_frees(def) == f0 + 1);
    CHECK(test_references(def) == 3);
    test_fail_next_allocation();
    CHECK(CopyEvent(copy) == NULL);
    CHECK(test_references(def) == 3);

    if ((uintmax_t)(ByteCount)-1 > (uintmax_t)PTRDIFF_MAX - 64u)
        CHECK(SetEventParameter(copy, NAME_A, TYPE_A, (ByteCount)-1, replacement)
              == memFullErr);

    CHECK(RemoveEventParameter(copy, NAME_EMPTY) == noErr);
    CHECK(RemoveEventParameter(copy, NAME_EMPTY) == eventParameterNotFoundErr);
    ReleaseEvent(event);
    CHECK(GetEventParameter(copy, NAME_A, TYPE_A, NULL, sizeof(out), NULL, out) == noErr);
    CHECK(out[0] == 0 && out[1] == 0xfe);
    CHECK(test_references(def) == 2);
    ReleaseEvent(copy);
    CHECK(test_references(def) == 1);
    CHECK(test_allocations(def) == test_frees(def));

    EventRef customEvent = NULL, customCopy = NULL;
    CHECK(CreateEvent(custom, 0x6f746872u, 8, 12.0, 0, &customEvent) == noErr);
    if (!customEvent) return 1;
    CHECK(SetEventParameter(customEvent, NAME_B, TYPE_B, sizeof(number), &number) == noErr);
    test_set_default(def);
    customCopy = CopyEvent(customEvent);
    CHECK(customCopy != NULL);
    if (!customCopy) { ReleaseEvent(customEvent); return 1; }
    CHECK(test_references(custom) == 3);
    ReleaseEvent(customEvent);
    gotNumber = 0;
    CHECK(GetEventParameter(customCopy, NAME_B, TYPE_B, NULL,
                            sizeof(gotNumber), NULL, &gotNumber) == noErr);
    CHECK(gotNumber == number);
    ReleaseEvent(customCopy);
    CHECK(test_allocations(custom) == test_frees(custom));
    CHECK(test_references(custom) == 1);

    printf("Carbon parameters checks: %u | Failures: %u\n", checks, failures);
    return failures ? 1 : 0;
}
