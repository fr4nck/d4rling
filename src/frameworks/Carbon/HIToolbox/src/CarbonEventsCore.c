/*
 This file is part of Darling.

 Copyright (C) 2025 Lubos Dolezel

 Darling is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 Darling is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with Darling.  If not, see <http://www.gnu.org/licenses/>.
*/

#include <HIToolbox/CarbonEventsCore.h>
#include <CarbonCore/MacErrors.h>

#include <stdatomic.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

#include <stdlib.h>
#include <stdio.h>

/* The event owns every parameter allocation. Carbon does not promise that
 * simultaneous mutation of the same EventRef is thread-safe.
 */
struct EventParameter {
    struct EventParameter* next;
    EventParamName name;
    EventParamType type;
    ByteCount size;
    unsigned char data[];
};

struct OpaqueEventRef {
    CFAllocatorRef allocator;
    _Atomic(ItemCount) retainCount;
    OSType eventClass;
    UInt32 eventKind;
    EventTime time;
    EventAttributes attributes;
    struct EventParameter* parameters;
};

static int verbose = 0;

__attribute__((constructor))
static void initme(void) {
    verbose = getenv("STUB_VERBOSE") != NULL;
}

OSStatus CallNextEventHandler(EventHandlerCallRef a, EventRef b)
{
    if (verbose) puts("STUB: CallNextEventHandler called");
	return 0;
}

OSStatus CreateEvent(CFAllocatorRef inAllocator, OSType inClassID, UInt32 kind,
                     EventTime when, EventAttributes flags, EventRef* outEvent)
{
    if (!outEvent)
        return paramErr;
    *outEvent = NULL;

    if (when == 0) {
        when = GetCurrentEventTime();
        if (when == 0)
            return unimpErr;
    }

    CFAllocatorRef allocator = inAllocator ? inAllocator : CFAllocatorGetDefault();
    CFRetain(allocator);
    EventRef event = CFAllocatorAllocate(allocator, sizeof(*event), 0);
    if (!event) {
        CFRelease(allocator);
        return memFullErr;
    }

    event->allocator = allocator;
    atomic_init(&event->retainCount, 1);
    event->eventClass = inClassID;
    event->eventKind = kind;
    event->time = when;
    event->attributes = flags;
    event->parameters = NULL;
    *outEvent = event;
    return noErr;
}

OSType GetEventClass(EventRef a)
{
    return a ? a->eventClass : 0;
}

UInt32 GetEventKind(EventRef a)
{
    return a ? a->eventKind : 0;
}

/* OSType '****', as declared for the Carbon Event Manager wildcard. */
#define CARBON_TYPE_WILDCARD ((EventParamType)0x2a2a2a2au)

static OSStatus AllocateParameter(EventRef event, EventParamName name,
                                  EventParamType type, ByteCount size,
                                  const void* bytes, struct EventParameter** out)
{
    *out = NULL;
    if (size != 0 && !bytes)
        return paramErr;

    /* sizeof includes any trailing structure padding. A zero-byte payload
     * must still allocate a complete EventParameter object.
     */
    const size_t baseSize = sizeof(struct EventParameter);
    /* CFAllocatorAllocate receives a signed CFIndex. Do not wrap that size. */
    if ((uintmax_t)size > (uintmax_t)PTRDIFF_MAX - baseSize)
        return memFullErr;

    struct EventParameter* param =
        CFAllocatorAllocate(event->allocator, (CFIndex)(baseSize + (size_t)size), 0);
    if (!param)
        return memFullErr;
    param->next = NULL;
    param->name = name;
    param->type = type;
    param->size = size;
    if (size != 0)
        memcpy(param->data, bytes, (size_t)size);
    *out = param;
    return noErr;
}

OSStatus SetEventParameter(EventRef inEvent, EventParamName inName,
                           EventParamType inType, ByteCount inSize, const void* inDataPtr)
{
    if (!inEvent || (inSize != 0 && !inDataPtr))
        return paramErr;

    struct EventParameter* replacement = NULL;
    OSStatus status = AllocateParameter(inEvent, inName, inType,
                                        inSize, inDataPtr, &replacement);
    if (status != noErr)
        return status; /* An allocation failure cannot corrupt old data. */

    struct EventParameter** slot = &inEvent->parameters;
    while (*slot && (*slot)->name != inName)
        slot = &(*slot)->next;
    if (*slot) {
        struct EventParameter* old = *slot;
        replacement->next = old->next;
        *slot = replacement;
        CFAllocatorDeallocate(inEvent->allocator, old);
    } else {
        *slot = replacement;
    }
    return noErr;
}

OSStatus GetEventParameter(EventRef inEvent, EventParamName inName,
                           EventParamType inDesiredType, EventParamType* outActualType,
                           ByteCount inBufferSize, ByteCount* outActualSize, void* outData)
{
    if (outActualType)
        *outActualType = 0;
    if (outActualSize)
        *outActualSize = 0;
    if (!inEvent || (!outData && inBufferSize != 0))
        return paramErr;

    const struct EventParameter* param = inEvent->parameters;
    while (param && param->name != inName)
        param = param->next;
    if (!param)
        return eventParameterNotFoundErr;

    if (outActualType)
        *outActualType = param->type;
    if (outActualSize)
        *outActualSize = param->size;

    /* Apple can invoke AppleEvent coercion handlers; these are not yet
     * available here. Never return success for a mismatched requested type.
     */
    if (inDesiredType != param->type && inDesiredType != CARBON_TYPE_WILDCARD)
        return errAECoercionFail;
    if (!outData)
        return noErr; /* NULL output is legal for a zero-buffer size query. */
    if (inBufferSize < param->size)
        return errAEBufferTooSmall;
    if (param->size != 0)
        memcpy(outData, param->data, (size_t)param->size);
    return noErr;
}

OSStatus RemoveEventParameter(EventRef inEvent, EventParamName inName)
{
    if (!inEvent)
        return paramErr;
    struct EventParameter** slot = &inEvent->parameters;
    while (*slot && (*slot)->name != inName)
        slot = &(*slot)->next;
    if (!*slot)
        return eventParameterNotFoundErr;
    struct EventParameter* removed = *slot;
    *slot = removed->next;
    CFAllocatorDeallocate(inEvent->allocator, removed);
    return noErr;
}

EventRef CopyEvent(EventRef inOther)
{
    if (!inOther)
        return NULL;
    EventRef copy = NULL;
    if (CreateEvent(inOther->allocator, inOther->eventClass, inOther->eventKind,
                    inOther->time, inOther->attributes, &copy) != noErr)
        return NULL;
    for (const struct EventParameter* param = inOther->parameters; param; param = param->next) {
        if (SetEventParameter(copy, param->name, param->type,
                              param->size, param->data) != noErr) {
            ReleaseEvent(copy); /* Releases the partially populated event. */
            return NULL;
        }
    }
    return copy;
}

EventQueueRef GetMainEventQueue()
{
    if (verbose) puts("STUB: GetMainEventQueue called");
	return 0;
}

OSStatus InstallEventHandler(EventTargetRef a, EventHandlerUPP b, ItemCount c, const EventTypeSpec* d, void* e, EventHandlerRef* f)
{
    if (verbose) puts("STUB: InstallEventHandler called");
	return 0;
}

EventHandlerUPP NewEventHandlerUPP(EventHandlerProcPtr a)
{
    if (verbose) puts("STUB: NewEventHandlerUPP called");
	return (EventHandlerUPP)0;
}

OSStatus PostEventToQueue(EventQueueRef a, EventRef b, EventPriority c)
{
    if (verbose) puts("STUB: PostEventToQueue called");
	return 0;
}

OSStatus ReceiveNextEvent(ItemCount a, const EventTypeSpec* b, EventTimeout c, Boolean d, EventRef* e)
{
    if (verbose) puts("STUB: ReceiveNextEvent called");
	return 0;
}

EventRef RetainEvent(EventRef inEvent)
{
    if (!inEvent)
        return NULL;
    ItemCount count = atomic_load_explicit(&inEvent->retainCount, memory_order_relaxed);
    do {
        if (count == (ItemCount)-1)
            return NULL;
    } while (!atomic_compare_exchange_weak_explicit(&inEvent->retainCount, &count,
              count + 1, memory_order_relaxed, memory_order_relaxed));
    return inEvent;
}

ItemCount GetEventRetainCount(EventRef inEvent)
{
    return inEvent ? atomic_load_explicit(&inEvent->retainCount, memory_order_relaxed) : 0;
}

void ReleaseEvent(EventRef inEvent)
{
    if (!inEvent)
        return;
    if (atomic_fetch_sub_explicit(&inEvent->retainCount, 1, memory_order_acq_rel) == 1) {
        CFAllocatorRef allocator = inEvent->allocator;
        struct EventParameter* param = inEvent->parameters;
        while (param) {
            struct EventParameter* next = param->next;
            CFAllocatorDeallocate(allocator, param);
            param = next;
        }
        CFAllocatorDeallocate(allocator, inEvent);
        CFRelease(allocator);
    }
}

OSStatus RemoveEventHandler(EventHandlerRef a)
{
    if (verbose) puts("STUB: RemoveEventHandler called");
	return 0;
}

OSStatus SendEventToEventTarget(EventRef a, EventTargetRef b)
{
    if (verbose) puts("STUB: SendEventToEventTarget called");
	return 0;
}

UInt32 GetCurrentKeyModifiers()
{
    if (verbose) puts("STUB: GetCurrentKeyModifiers called");
    return (UInt32) 0;
}

EventTime GetEventTime(EventRef inEvent)
{
    return inEvent ? inEvent->time : 0;
}

EventTime GetCurrentEventTime(void)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0)
        return 0;
    return (EventTime)now.tv_sec + (EventTime)now.tv_nsec / 1000000000.0;
}
