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
#include <time.h>

#include <stdlib.h>
#include <stdio.h>

/* Event metadata is immutable; only ownership changes after creation. */
struct OpaqueEventRef {
    CFAllocatorRef allocator;
    _Atomic(ItemCount) retainCount;
    OSType eventClass;
    UInt32 eventKind;
    EventTime time;
    EventAttributes attributes;
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

OSStatus GetEventParameter(EventRef a, EventParamName b, EventParamType c, EventParamType* d, ByteCount e, ByteCount* f, void* g)
{
    if (verbose) puts("STUB: GetEventParameter called");
	return 0;
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
