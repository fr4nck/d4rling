/* SPDX-License-Identifier: GPL-3.0-or-later
 * Real Mach-O HIToolbox -> CoreFoundation integration smoke.
 * Only a verified Darling runtime invocation can qualify this test.
 */
#include <CoreFoundation/CoreFoundation.h>
#include <HIToolbox/CarbonEventsCore.h>
#include <CarbonCore/MacErrors.h>
#include <stdio.h>
#include <string.h>

static unsigned checks, failures;
#define CHECK(condition) do { \
    ++checks; \
    if (!(condition)) { \
        ++failures; \
        fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #condition); \
    } \
} while (0)

int main(void)
{
    CFAllocatorRef allocator = CFAllocatorGetDefault();
    CHECK(allocator != NULL);
    if (!allocator)
        return 1;

    EventRef event = NULL;
    const OSType eventClass = 0x736d6f6bu;
    const UInt32 eventKind = 0x12345678u;
    const EventTime when = 9.5;
    CHECK(CreateEvent(allocator, eventClass, eventKind, when, 0, &event) == noErr);
    CHECK(event != NULL);
    if (!event)
        return 1;

    CHECK(GetEventClass(event) == eventClass);
    CHECK(GetEventKind(event) == eventKind);
    CHECK(GetEventTime(event) == when);
    CHECK(GetEventRetainCount(event) == 1);

    const EventParamName name = 0x64617461u;
    const EventParamType type = 0x72617731u;
    unsigned char input[] = { 0, 0xfe, 4, 0, 0x7f };
    unsigned char result[sizeof(input)] = { 0 };
    EventParamType actualType = 0;
    ByteCount actualSize = 0;

    CHECK(SetEventParameter(event, name, type, sizeof(input), input) == noErr);
    input[0] = 0xa5; /* The event must own a copy, not caller bytes. */
    CHECK(GetEventParameter(event, name, type, &actualType,
                            sizeof(result), &actualSize, result) == noErr);
    CHECK(actualType == type);
    CHECK(actualSize == sizeof(input));
    CHECK(result[0] == 0 && result[1] == 0xfe && result[4] == 0x7f);

    EventRef copy = CopyEvent(event);
    CHECK(copy != NULL && copy != event);
    if (!copy) {
        ReleaseEvent(event);
        return 1;
    }
    CHECK(GetEventRetainCount(copy) == 1);
    CHECK(RemoveEventParameter(event, name) == noErr);
    CHECK(GetEventParameter(event, name, type, NULL, 0, NULL, NULL)
          == eventParameterNotFoundErr);
    ReleaseEvent(event);

    memset(result, 0, sizeof(result));
    CHECK(GetEventParameter(copy, name, type, NULL,
                            sizeof(result), NULL, result) == noErr);
    CHECK(result[0] == 0 && result[1] == 0xfe && result[4] == 0x7f);
    ReleaseEvent(copy);

    printf("Carbon HIToolbox/CoreFoundation integration checks: %u | Failures: %u\n",
           checks, failures);
    return failures ? 1 : 0;
}
