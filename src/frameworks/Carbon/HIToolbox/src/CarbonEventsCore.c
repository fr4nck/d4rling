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
#include <pthread.h>

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


/* One process queue and application target only. No CFRunLoop/window pump.
 * Queue operations serialize membership; handler operations are confined to
 * their installing thread. Callbacks never run while the queue lock is held.
 */
struct QueueEntry {
    struct QueueEntry* next;
    EventRef event;
    EventPriority priority;
};
struct OpaqueEventQueueRef {
    pthread_mutex_t lock;
    struct QueueEntry* first;
};
static struct OpaqueEventQueueRef mainQueue = { PTHREAD_MUTEX_INITIALIZER, NULL };
static char applicationTarget;

struct Handler {
    struct Handler* next;
    CFAllocatorRef allocator;
    EventHandlerUPP callback;
    void* userData;
    ItemCount count;
    size_t references;
    int removed;
    EventTypeSpec types[];
};
/* Installation/removal/dispatch deliberately support the initial thread only.
 * The first target getter binds it once; other threads return unimpErr from
 * handler APIs. Posting and pulling the main queue are independently locked.
 */
static pthread_once_t targetOnce = PTHREAD_ONCE_INIT;
static pthread_t targetThread;
static struct Handler* handlers;
static int handlerStorageBusy;
static void BindTargetThread(void) { targetThread = pthread_self(); }

static int IsTargetThread(void)
{
    pthread_once(&targetOnce, BindTargetThread);
    return pthread_equal(targetThread, pthread_self());
}

static int Matches(EventRef event, ItemCount count, const EventTypeSpec* types)
{
    for (ItemCount i = 0; i < count; ++i)
        if (types[i].eventClass == event->eventClass &&
            types[i].eventKind == event->eventKind)
            return 1;
    return 0;
}

EventTargetRef GetApplicationEventTarget(void)
{
    pthread_once(&targetOnce, BindTargetThread);
    return &applicationTarget;
}

EventQueueRef GetMainEventQueue(void)
{
    return &mainQueue;
}

OSStatus PostEventToQueue(EventQueueRef queue, EventRef event, EventPriority priority)
{
    if (queue != &mainQueue || !event || priority < kEventPriorityLow ||
        priority > kEventPriorityHigh)
        return paramErr;
    pthread_mutex_lock(&queue->lock);
    for (struct QueueEntry* p = queue->first; p; p = p->next) {
        if (p->event == event) {
            pthread_mutex_unlock(&queue->lock);
            return eventAlreadyPostedErr;
        }
    }
    pthread_mutex_unlock(&queue->lock);
    /* Custom allocator callbacks must not run inside the queue lock. */
    struct QueueEntry* entry = CFAllocatorAllocate(event->allocator, sizeof(*entry), 0);
    if (!entry)
        return memFullErr;
    if (!RetainEvent(event)) {
        CFAllocatorDeallocate(event->allocator, entry);
        return memFullErr;
    }
    pthread_mutex_lock(&queue->lock);
    /* Another poster, or a reentrant allocator, may have posted meanwhile. */
    for (struct QueueEntry* p = queue->first; p; p = p->next) {
        if (p->event == event) {
            pthread_mutex_unlock(&queue->lock);
            CFAllocatorDeallocate(event->allocator, entry);
            ReleaseEvent(event);
            return eventAlreadyPostedErr;
        }
    }
    entry->event = event;
    entry->priority = priority;
    struct QueueEntry** slot = &queue->first;
    while (*slot && (*slot)->priority >= priority)
        slot = &(*slot)->next;
    entry->next = *slot;
    *slot = entry;
    pthread_mutex_unlock(&queue->lock);
    return noErr;
}

OSStatus ReceiveNextEvent(ItemCount count, const EventTypeSpec* types,
                         EventTimeout timeout, Boolean pull, EventRef* out)
{
    if (!out)
        return paramErr;
    *out = NULL;
    if (count && !types)
        return paramErr;
    /* Waiting would require running timers/native sources. Do not fake it. */
    if (timeout != kEventDurationNoWait)
        return unimpErr;
    pthread_mutex_lock(&mainQueue.lock);
    struct QueueEntry** slot = &mainQueue.first;
    while (*slot && count && !Matches((*slot)->event, count, types))
        slot = &(*slot)->next;
    if (!*slot) {
        pthread_mutex_unlock(&mainQueue.lock);
        return eventLoopTimedOutErr;
    }
    struct QueueEntry* entry = *slot;
    *out = entry->event;
    if (pull) {
        *slot = entry->next;
        /* Transfer the queue's reference. A peek is borrowed, not retained. */
    }
    pthread_mutex_unlock(&mainQueue.lock);
    if (pull)
        CFAllocatorDeallocate((*out)->allocator, entry);
    return noErr;
}

EventHandlerUPP NewEventHandlerUPP(EventHandlerProcPtr callback)
{
    return callback;
}

static void ReleaseHandler(struct Handler* handler)
{
    if (--handler->references == 0) {
        CFAllocatorRef allocator = handler->allocator;
        CFAllocatorDeallocate(allocator, handler);
        CFRelease(allocator);
    }
}

OSStatus InstallEventHandler(EventTargetRef target, EventHandlerUPP callback,
                            ItemCount count, const EventTypeSpec* types,
                            void* userData, EventHandlerRef* out)
{
    if (out)
        *out = NULL;
    if (target != &applicationTarget || !callback || (count && !types))
        return paramErr;
    if (!IsTargetThread())
        return unimpErr;
    if (handlerStorageBusy)
        return eventTargetBusyErr;
    size_t typeBytes = (size_t)count * sizeof(EventTypeSpec);
    if (typeBytes / sizeof(EventTypeSpec) != count ||
        typeBytes > (size_t)PTRDIFF_MAX - sizeof(struct Handler))
        return memFullErr;
    for (struct Handler* h = handlers; h; h = h->next) {
        if (h->callback != callback)
            continue;
        for (ItemCount i = 0; i < count; ++i)
            for (ItemCount j = 0; j < h->count; ++j)
                if (types[i].eventClass == h->types[j].eventClass &&
                    types[i].eventKind == h->types[j].eventKind)
                    return eventHandlerAlreadyInstalledErr;
    }
    handlerStorageBusy = 1;
    CFAllocatorRef allocator = CFAllocatorGetDefault();
    CFRetain(allocator);
    struct Handler* h = CFAllocatorAllocate(allocator,
        sizeof(*h) + typeBytes, 0);
    if (!h) {
        CFRelease(allocator);
        handlerStorageBusy = 0;
        return memFullErr;
    }
    h->allocator = allocator;
    h->callback = callback;
    h->userData = userData;
    h->count = count;
    h->references = 1;
    h->removed = 0;
    if (count)
        memcpy(h->types, types, (size_t)count * sizeof(EventTypeSpec));
    h->next = handlers;
    handlers = h;
    handlerStorageBusy = 0;
    if (out)
        *out = h;
    return noErr;
}

OSStatus RemoveEventHandler(EventHandlerRef ref)
{
    if (!ref)
        return paramErr;
    if (!IsTargetThread())
        return unimpErr;
    if (handlerStorageBusy)
        return eventTargetBusyErr;
    struct Handler** slot = &handlers;
    while (*slot && *slot != ref)
        slot = &(*slot)->next;
    if (!*slot)
        return paramErr;
    struct Handler* h = *slot;
    *slot = h->next;
    h->removed = 1;
    ReleaseHandler(h); /* A dispatch snapshot may still own it. */
    return noErr;
}

struct HandlerCall {
    struct HandlerCall* previous;
    struct Handler** snapshot;
    size_t count, next;
    EventRef event;
    int calledNext;
    OSStatus nextResult;
};
static _Thread_local struct HandlerCall* currentCall;
static OSStatus InvokeHandlers(struct Handler** snapshot, size_t count,
                               size_t start, EventRef event)
{
    for (size_t i = start; i < count; ++i) {
        struct Handler* h = snapshot[i];
        if (h->removed)
            continue;
        struct HandlerCall call = { currentCall, snapshot, count, i + 1,
                                    event, 0, eventNotHandledErr };
        currentCall = &call;
        OSStatus result = h->callback(&call, event, h->userData);
        currentCall = call.previous;
        if (result != eventNotHandledErr || call.calledNext)
            return result;
    }
    return eventNotHandledErr;
}

OSStatus CallNextEventHandler(EventHandlerCallRef ref, EventRef event)
{
    /* Never dereference an arbitrary or expired call token. */
    if (!currentCall || ref != currentCall || event != currentCall->event)
        return paramErr;
    if (!currentCall->calledNext) {
        currentCall->calledNext = 1;
        currentCall->nextResult = InvokeHandlers(currentCall->snapshot,
            currentCall->count, currentCall->next, event);
    }
    return currentCall->nextResult;
}

OSStatus SendEventToEventTarget(EventRef event, EventTargetRef target)
{
    if (!event || target != &applicationTarget)
        return paramErr;
    if (!IsTargetThread())
        return unimpErr;
    if (handlerStorageBusy)
        return eventTargetBusyErr;
    size_t count = 0;
    for (struct Handler* h = handlers; h; h = h->next)
        if (Matches(event, h->count, h->types))
            ++count;
    if (!count)
        return eventNotHandledErr;
    if (count > (size_t)PTRDIFF_MAX / sizeof(struct Handler*))
        return memFullErr;
    /* Keep allocator reentry from changing the counted handler list. */
    handlerStorageBusy = 1;
    CFAllocatorRef allocator = CFAllocatorGetDefault();
    CFRetain(allocator);
    struct Handler** snapshot = CFAllocatorAllocate(allocator,
        count * sizeof(*snapshot), 0);
    if (!snapshot) {
        CFRelease(allocator);
        handlerStorageBusy = 0;
        return memFullErr;
    }
    size_t index = 0;
    for (struct Handler* h = handlers; h; h = h->next) {
        if (Matches(event, h->count, h->types)) {
            ++h->references;
            snapshot[index++] = h;
        }
    }
    handlerStorageBusy = 0;
    OSStatus result = memFullErr;
    if (RetainEvent(event)) {
        result = InvokeHandlers(snapshot, count, 0, event);
        ReleaseEvent(event);
    }
    for (size_t i = 0; i < count; ++i)
        ReleaseHandler(snapshot[i]);
    CFAllocatorDeallocate(allocator, snapshot);
    CFRelease(allocator);
    return result;
}
