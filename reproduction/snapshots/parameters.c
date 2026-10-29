/* SPDX-License-Identifier: GPL-3.0-or-later
 * Carbon parameter regression candidates, prepared with ChatGPT GPT-6.
 * PROPOSED, NOT EXECUTED; test-only CoreFoundation allocator adapter.
 */
#include <HIToolbox/CarbonEventsCore.h>
#include <CarbonCore/MacErrors.h>
#include "allocator-adapter.h"
#include <limits.h>
#include <stdio.h>
#include <string.h>

static unsigned checks, failures;
#define CHECK(c) do { ++checks; if (!(c)) { ++failures; \
    fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #c); } } while (0)

int main(void)
{
    CFAllocatorRef allocator = test_custom_allocator();
    CFAllocatorRef defaults = test_default_allocator();
    const EventParamName bytesName = 0x70303031u; /* custom 'p001' */
    const EventParamName cfName = 0x70303032u;    /* custom 'p002' */
    const EventParamName refName = 0x70303033u;   /* custom 'p003' */
    const EventParamName menuName = 0x70303034u;  /* custom 'p004' */
    const EventParamName shapeName = 0x70303035u; /* custom 'p005' */
    const EventParamType bytesType = 0x54455854u; /* Apple typeChar */
    const EventParamType cfType = 0x63667374u;    /* Apple typeCFStringRef */
    const EventParamType eventType = 0x65767266u; /* Apple typeEventRef */
    const EventParamType menuType = 0x6d656e75u;  /* Apple typeMenuRef */
    const EventParamType shapeType = 0x73686170u; /* Apple typeHIShapeRef */
    const EventParamType wildcard = 0x2a2a2a2au; /* Apple typeWildCard */
    const unsigned char first[] = {1, 2, 3};
    const unsigned char replacement[] = {9, 8, 7, 6};
    unsigned char out[5] = {0xa5, 0xa5, 0xa5, 0xa5, 0xa5};
    EventParamType actualType = 0;
    ByteCount size = 0;
    EventRef event = NULL, child = NULL, duplicate = NULL;
    CFTypeRef cf = test_cf_object();

    CHECK(CopyEvent(NULL) == NULL);
    CHECK(SetEventParameter(NULL, bytesName, bytesType, 0, NULL) == paramErr);
    CHECK(RemoveEventParameter(NULL, bytesName) == paramErr);
    CHECK(GetEventParameter(NULL, bytesName, wildcard, NULL, 0, NULL, NULL) == paramErr);
    CHECK(CreateEvent(allocator, 0x74657374u, 7, 41.5, 1, &event) == noErr);
    CHECK(event != NULL);
    if (!event)
        return 1;

    CHECK(GetEventParameter(event, bytesName, wildcard, NULL, 0, NULL, NULL)
          == eventParameterNotFoundErr);
    CHECK(RemoveEventParameter(event, bytesName) == eventParameterNotFoundErr);
    CHECK(SetEventParameter(event, bytesName, bytesType, sizeof(first), first) == noErr);
    CHECK(GetEventParameter(event, bytesName, wildcard, &actualType, 0, &size, NULL) == noErr);
    CHECK(actualType == bytesType && size == sizeof(first));
    CHECK(GetEventParameter(event, bytesName, bytesType, NULL, 0, NULL, NULL) == noErr);
    CHECK(GetEventParameter(event, bytesName, bytesType, NULL, 2, &size, out)
          == errAEBufferTooSmall);
    CHECK(size == sizeof(first));
    CHECK(out[0] == 0xa5 && out[1] == 0xa5 && out[2] == 0xa5);
    CHECK(GetEventParameter(event, bytesName, bytesType, NULL, 3, &size, out) == noErr);
    CHECK(memcmp(out, first, sizeof(first)) == 0 && out[3] == 0xa5);
    CHECK(GetEventParameter(event, bytesName, cfType, NULL, 0, &size, NULL)
          == errAECoercionFail); /* Coercion unsupported in this batch. */
    CHECK(GetEventParameter(event, bytesName, bytesType, NULL, 1, NULL, NULL) == paramErr);
    CHECK(SetEventParameter(event, bytesName, bytesType, 1, NULL) == paramErr);
    CHECK(SetEventParameter(event, bytesName, bytesType, (ByteCount)LONG_MAX, first)
          == memFullErr);

    CHECK(SetEventParameter(event, bytesName, bytesType, 0, NULL) == noErr);
    CHECK(GetEventParameter(event, bytesName, bytesType, NULL, 0, &size, NULL) == noErr);
    CHECK(size == 0);
    CHECK(SetEventParameter(event, bytesName, bytesType, sizeof(first), first) == noErr);
    test_fail_next_allocation();
    CHECK(SetEventParameter(event, bytesName, bytesType,
                            sizeof(replacement), replacement) == memFullErr);
    CHECK(GetEventParameter(event, bytesName, bytesType, NULL, 3, &size, out) == noErr);
    CHECK(size == sizeof(first) && memcmp(out, first, sizeof(first)) == 0);
    CHECK(SetEventParameter(event, bytesName, bytesType,
                            sizeof(replacement), replacement) == noErr);
    CHECK(GetEventParameter(event, bytesName, wildcard, &actualType, 4, &size, out) == noErr);
    CHECK(size == sizeof(replacement) && memcmp(out, replacement, size) == 0);

    CHECK(test_cf_references() == 1);
    CHECK(SetEventParameter(event, cfName, cfType, sizeof(cf), &cf) == noErr);
    CHECK(test_cf_references() == 2);
    /* Same reference: retain new ownership before releasing the old one. */
    CHECK(SetEventParameter(event, cfName, cfType, sizeof(cf), &cf) == noErr);
    CHECK(test_cf_references() == 2);
    CHECK(SetEventParameter(event, cfName, cfType, sizeof(cf) - 1, &cf) == paramErr);
    CHECK(test_cf_references() == 2);
    /* These use the test CF reference, not real MenuRef/HIShapeRef objects. */
    CHECK(SetEventParameter(event, menuName, menuType, sizeof(cf), &cf) == noErr);
    CHECK(test_cf_references() == 3);
    CHECK(SetEventParameter(event, shapeName, shapeType, sizeof(cf), &cf) == noErr);
    CHECK(test_cf_references() == 4);
    CHECK(RemoveEventParameter(event, menuName) == noErr);
    CHECK(RemoveEventParameter(event, shapeName) == noErr);
    CHECK(test_cf_references() == 2);
    CHECK(CreateEvent(allocator, 0x6368696cu, 1, 22, 0, &child) == noErr);
    CHECK(child != NULL);
    if (!child) {
        ReleaseEvent(event);
        return 1;
    }
    CHECK(SetEventParameter(event, refName, eventType, sizeof(child), &child) == noErr);
    CHECK(GetEventRetainCount(child) == 2);

    const unsigned alive = test_allocations(allocator) - test_frees(allocator);
    test_fail_next_allocation();
    CHECK(CopyEvent(event) == NULL); /* Failed event-object allocation. */
    CHECK(test_allocations(allocator) - test_frees(allocator) == alive);
    test_fail_allocation_after(1);
    CHECK(CopyEvent(event) == NULL); /* Failed first parameter allocation. */
    CHECK(test_allocations(allocator) - test_frees(allocator) == alive);
    test_fail_allocation_after(2);
    CHECK(CopyEvent(event) == NULL); /* Failed second parameter allocation. */
    CHECK(test_allocations(allocator) - test_frees(allocator) == alive);
    test_fail_allocation_after(3);
    CHECK(CopyEvent(event) == NULL); /* Failed third parameter allocation. */
    CHECK(test_allocations(allocator) - test_frees(allocator) == alive);
    CHECK(test_cf_references() == 2);
    CHECK(GetEventRetainCount(child) == 2);

    duplicate = CopyEvent(event);
    CHECK(duplicate != NULL && duplicate != event);
    if (duplicate) {
        CHECK(GetEventRetainCount(duplicate) == 1);
        CHECK(GetEventClass(duplicate) == GetEventClass(event));
        CHECK(GetEventKind(duplicate) == GetEventKind(event));
        CHECK(GetEventTime(duplicate) == GetEventTime(event));
        CHECK(test_cf_references() == 3);
        CHECK(GetEventRetainCount(child) == 3);
        CHECK(GetEventParameter(duplicate, bytesName, wildcard, &actualType,
                                sizeof(out), &size, out) == noErr);
        CHECK(actualType == bytesType && size == sizeof(replacement));
        CHECK(memcmp(out, replacement, sizeof(replacement)) == 0);
        CHECK(RemoveEventParameter(duplicate, bytesName) == noErr);
        CHECK(GetEventParameter(event, bytesName, wildcard, NULL, 0, &size, NULL)
              == noErr && size == sizeof(replacement));
        CHECK(RemoveEventParameter(duplicate, cfName) == noErr);
        CHECK(test_cf_references() == 2);
        CHECK(RemoveEventParameter(duplicate, cfName) == eventParameterNotFoundErr);
    }

    CHECK(RemoveEventParameter(event, cfName) == noErr);
    CHECK(test_cf_references() == 1);
    CHECK(RemoveEventParameter(event, cfName) == eventParameterNotFoundErr);
    test_set_default(defaults); /* Original allocator must still own every node. */
    if (duplicate)
        ReleaseEvent(duplicate);
    ReleaseEvent(event);
    CHECK(GetEventRetainCount(child) == 1);
    ReleaseEvent(child);
    CHECK(test_allocations(allocator) == test_frees(allocator));
    CHECK(test_references(allocator) == 1);
    CHECK(test_cf_references() == 1);
    printf("Proposed parameter checks: %u | failures: %u\n", checks, failures);
    return failures ? 1 : 0;
}
