/*
This file is part of Darling.

Copyright (C) 2020 Lubos Dolezel

Darling is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Darling is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with Darling.  If not, see <http://www.gnu.org/licenses/>.
*/

#include <CarbonCore/MacMemory.h>
#include <CarbonCore/MacErrors.h>
#include <climits>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <malloc/malloc.h>

// Carbon's MemError is per-thread on Mac OS X 10.3 and later. The allocation
// records preserve logical sizes: malloc_size() reports capacity, not Size.
static thread_local OSErr g_memoryError = noErr;
struct PtrRecord { Ptr ptr; size_t size; PtrRecord* next; };
struct HandleRecord { Handle handle; bool locked; HandleRecord* next; };
static std::mutex g_recordsLock;
static PtrRecord* g_pointers = nullptr;
static HandleRecord* g_handles = nullptr;

static PtrRecord* findPtr(Ptr ptr)
{
    for (PtrRecord* r = g_pointers; r; r = r->next)
        if (r->ptr == ptr) return r;
    return nullptr;
}

static HandleRecord* findHandle(Handle handle)
{
    for (HandleRecord* r = g_handles; r; r = r->next)
        if (r->handle == handle) return r;
    return nullptr;
}

static Ptr allocatePtr(size_t size, bool clear)
{
    void* data = clear ? std::calloc(1, size ? size : 1) : std::malloc(size ? size : 1);
    if (!data) { g_memoryError = memFullErr; return nullptr; }
    auto* record = static_cast<PtrRecord*>(std::malloc(sizeof(PtrRecord)));
    if (!record) {
        std::free(data);
        g_memoryError = memFullErr;
        return nullptr;
    }
    record->ptr = static_cast<Ptr>(data);
    record->size = size;
    {
        std::lock_guard<std::mutex> guard(g_recordsLock);
        record->next = g_pointers;
        g_pointers = record;
    }
    g_memoryError = noErr;
    return record->ptr;
}

OSErr MemError(void) { return g_memoryError; }

void BlockMove(const void* src, void* dst, size_t count) { std::memmove(dst, src, count); }
void BlockMoveData(const void* src, void* dst, size_t count) { std::memmove(dst, src, count); }
void BlockMoveUncached(const void* src, void* dst, size_t count) { std::memmove(dst, src, count); }
void BlockMoveDataUncached(const void* src, void* dst, size_t count) { std::memmove(dst, src, count); }
void BlockZero(void* dst, size_t count) { std::memset(dst, 0, count); }
void BlockZeroUncached(void* dst, size_t count) { std::memset(dst, 0, count); }

Ptr NewPtr(long len)
{
    if (len < 0) { g_memoryError = memFullErr; return nullptr; }
    return allocatePtr(static_cast<size_t>(len), false);
}

Ptr NewPtrClear(long len)
{
    if (len < 0) { g_memoryError = memFullErr; return nullptr; }
    return allocatePtr(static_cast<size_t>(len), true);
}

void DisposePtr(Ptr ptr)
{
    if (!ptr) { g_memoryError = noErr; return; }
    {
        std::lock_guard<std::mutex> guard(g_recordsLock);
        PtrRecord** slot = &g_pointers;
        while (*slot && (*slot)->ptr != ptr) slot = &(*slot)->next;
        if (!*slot) { g_memoryError = memAdrErr; return; }
        PtrRecord* old = *slot;
        *slot = old->next;
        std::free(old);
    }
    std::free(ptr);
    g_memoryError = noErr;
}

long GetPtrSize(Ptr ptr)
{
    if (!ptr) { g_memoryError = memAdrErr; return 0; }
    std::lock_guard<std::mutex> guard(g_recordsLock);
    const PtrRecord* record = findPtr(ptr);
    if (!record) { g_memoryError = memAdrErr; return 0; }
    const size_t size = record->size;
    if (size > LONG_MAX) { g_memoryError = memFullErr; return 0; }
    g_memoryError = noErr;
    return static_cast<long>(size);
}

void SetPtrSize(Ptr ptr, long newSize)
{
    if (!ptr) { g_memoryError = memAdrErr; return; }
    if (newSize < 0) { g_memoryError = memFullErr; return; }
    std::lock_guard<std::mutex> guard(g_recordsLock);
    PtrRecord* record = findPtr(ptr);
    // Nonrelocatable pointers cannot be updated in the caller. Shrinking
    // changes only their logical size; in-place growth is bounded by capacity.
    if (!record) { g_memoryError = memAdrErr; return; }
    if (static_cast<size_t>(newSize) > malloc_size(ptr)) {
        g_memoryError = memFullErr;
        return;
    }
    record->size = static_cast<size_t>(newSize);
    g_memoryError = noErr;
}

Handle NewEmptyHandle(void)
{
    Handle handle = static_cast<Handle>(std::malloc(sizeof(*handle)));
    if (!handle) { g_memoryError = memFullErr; return nullptr; }
    HandleRecord* record = static_cast<HandleRecord*>(std::malloc(sizeof(HandleRecord)));
    if (!record) { std::free(handle); g_memoryError = memFullErr; return nullptr; }
    *handle = nullptr;
    record->handle = handle;
    record->locked = false;
    {
        std::lock_guard<std::mutex> guard(g_recordsLock);
        record->next = g_handles;
        g_handles = record;
    }
    g_memoryError = noErr;
    return handle;
}

Handle NewHandle(long size)
{
    if (size < 0) { g_memoryError = memFullErr; return nullptr; }
    Handle handle = NewEmptyHandle();
    if (!handle) return nullptr;
    SetHandleSize(handle, size);
    if (MemError() == noErr) return handle;
    OSErr error = MemError();
    DisposeHandle(handle);
    g_memoryError = error;
    return nullptr;
}

Handle NewHandleClear(long size)
{
    Handle handle = NewHandle(size);
    if (handle && size) std::memset(*handle, 0, static_cast<size_t>(size));
    return handle;
}

void DisposeHandle(Handle handle)
{
    if (!handle) { g_memoryError = nilHandleErr; return; }
    {
        std::lock_guard<std::mutex> guard(g_recordsLock);
        HandleRecord** slot = &g_handles;
        while (*slot && (*slot)->handle != handle) slot = &(*slot)->next;
        if (!*slot) { g_memoryError = memWZErr; return; }
        HandleRecord* old = *slot;
        *slot = old->next;
        std::free(old);
    }
    if (*handle) DisposePtr(*handle);
    std::free(handle);
    g_memoryError = noErr;
}

void EmptyHandle(Handle handle)
{
    if (!handle) { g_memoryError = nilHandleErr; return; }
    {
        std::lock_guard<std::mutex> guard(g_recordsLock);
        if (!findHandle(handle)) { g_memoryError = memWZErr; return; }
    }
    if (*handle) DisposePtr(*handle);
    *handle = nullptr;
    {
        std::lock_guard<std::mutex> guard(g_recordsLock);
        HandleRecord* record = findHandle(handle);
        if (record) record->locked = false;
    }
    g_memoryError = noErr;
}

Size GetHandleSize(Handle handle)
{
    if (!handle) { g_memoryError = nilHandleErr; return 0; }
    {
        std::lock_guard<std::mutex> guard(g_recordsLock);
        if (!findHandle(handle)) { g_memoryError = memWZErr; return 0; }
    }
    if (!*handle) { g_memoryError = nilHandleErr; return 0; }
    return GetPtrSize(*handle);
}

void SetHandleSize(Handle handle, long newSize)
{
    if (!handle) { g_memoryError = nilHandleErr; return; }
    {
        std::lock_guard<std::mutex> guard(g_recordsLock);
        if (!findHandle(handle)) { g_memoryError = memWZErr; return; }
    }
    if (newSize < 0) { g_memoryError = memFullErr; return; }
    if (!*handle) {
        Ptr fresh = NewPtr(newSize);
        if (fresh) *handle = fresh;
        return;
    }
    std::lock_guard<std::mutex> guard(g_recordsLock);
    PtrRecord* record = findPtr(*handle);
    HandleRecord* state = findHandle(handle);
    if (!record || !state) { g_memoryError = memWZErr; return; }
    const size_t desired = static_cast<size_t>(newSize);
    // A logical shrink or expansion within existing capacity never moves data.
    if (desired <= malloc_size(*handle)) {
        record->size = desired;
        g_memoryError = noErr;
        return;
    }
    if (state->locked) { g_memoryError = memLockedErr; return; }
    void* resized = std::realloc(*handle, desired);
    if (!resized) { g_memoryError = memFullErr; return; }
    *handle = static_cast<Ptr>(resized);
    record->ptr = *handle;
    record->size = desired;
    g_memoryError = noErr;
}

void ReallocateHandle(Handle handle, Size byteCount)
{
    if (!handle) { g_memoryError = nilHandleErr; return; }
    {
        std::lock_guard<std::mutex> guard(g_recordsLock);
        if (!findHandle(handle)) { g_memoryError = memWZErr; return; }
    }
    if (byteCount < 0) { g_memoryError = memFullErr; return; }
    Ptr fresh = NewPtr(byteCount);
    if (!fresh) return; // macOS preserves the original allocation on failure.
    Ptr old = *handle;
    *handle = fresh;
    if (old) DisposePtr(old);
    {
        std::lock_guard<std::mutex> guard(g_recordsLock);
        HandleRecord* state = findHandle(handle);
        if (state) state->locked = false;
    }
    g_memoryError = noErr;
}

void HLock(Handle handle)
{
    std::lock_guard<std::mutex> guard(g_recordsLock);
    HandleRecord* state = findHandle(handle);
    if (!state || !*handle) { g_memoryError = nilHandleErr; return; }
    state->locked = true;
    g_memoryError = noErr;
}
void HLockHi(Handle handle) { HLock(handle); }
void HUnlock(Handle handle)
{
    std::lock_guard<std::mutex> guard(g_recordsLock);
    HandleRecord* state = findHandle(handle);
    if (!state || !*handle) { g_memoryError = nilHandleErr; return; }
    state->locked = false;
    g_memoryError = noErr;
}

OSErr PtrToHand(const void* srcPtr, Handle* dstHndl, long size)
{
    if (!dstHndl || size < 0 || (size && !srcPtr)) return g_memoryError = paramErr;
    Handle handle = NewHandle(size);
    if (!handle) return MemError();
    if (size) std::memcpy(*handle, srcPtr, static_cast<size_t>(size));
    *dstHndl = handle;
    return g_memoryError = noErr;
}

OSErr PtrToXHand(const void* srcPtr, Handle handle, long size)
{
    if (!handle || size < 0 || (size && !srcPtr)) return g_memoryError = paramErr;
    // The source may reside in the destination block and be moved by resize.
    void* copy = nullptr;
    if (size) {
        copy = std::malloc(static_cast<size_t>(size));
        if (!copy) return g_memoryError = memFullErr;
        std::memcpy(copy, srcPtr, static_cast<size_t>(size));
    }
    SetHandleSize(handle, size);
    OSErr error = MemError();
    if (error == noErr && size) std::memcpy(*handle, copy, static_cast<size_t>(size));
    std::free(copy);
    return g_memoryError = error;
}

OSErr HandToHand(Handle* handle)
{
    if (!handle || !*handle) return g_memoryError = paramErr;
    {
        std::lock_guard<std::mutex> guard(g_recordsLock);
        if (!findHandle(*handle)) return g_memoryError = memWZErr;
    }
    Handle copy = nullptr;
    if (!**handle) {
        copy = NewEmptyHandle();
    } else {
        const Size size = GetHandleSize(*handle);
        if (MemError() != noErr) return MemError();
        copy = NewHandle(size);
        if (copy && size) std::memcpy(*copy, **handle, static_cast<size_t>(size));
    }
    if (!copy) return MemError();
    *handle = copy;
    return g_memoryError = noErr;
}

OSErr HandAndHand(Handle first, Handle second)
{
    if (!first || !second || !*first || !*second) return g_memoryError = paramErr;
    const Size firstSize = GetHandleSize(first);
    if (MemError() != noErr) return MemError();
    const Size secondSize = GetHandleSize(second);
    if (MemError() != noErr) return MemError();
    if (firstSize > LONG_MAX - secondSize) return g_memoryError = memFullErr;
    // Snapshot first: its allocation could be the destination itself.
    void* data = nullptr;
    if (firstSize) {
        data = std::malloc(static_cast<size_t>(firstSize));
        if (!data) return g_memoryError = memFullErr;
        std::memcpy(data, *first, static_cast<size_t>(firstSize));
    }
    SetHandleSize(second, secondSize + firstSize);
    OSErr error = MemError();
    if (error == noErr && firstSize) std::memcpy(*second + secondSize, data, static_cast<size_t>(firstSize));
    std::free(data);
    return g_memoryError = error;
}

OSErr PtrAndHand(const void* srcPtr, Handle handle, long size)
{
    if (!handle || size < 0 || (size && !srcPtr)) return g_memoryError = paramErr;
    if (!*handle) return g_memoryError = nilHandleErr;
    const Size previous = GetHandleSize(handle);
    if (MemError() != noErr) return MemError();
    if (size > LONG_MAX - previous) return g_memoryError = memFullErr;
    void* copy = nullptr;
    if (size) {
        copy = std::malloc(static_cast<size_t>(size));
        if (!copy) return g_memoryError = memFullErr;
        std::memcpy(copy, srcPtr, static_cast<size_t>(size));
    }
    SetHandleSize(handle, previous + size);
    OSErr error = MemError();
    if (error == noErr && size) std::memcpy(*handle + previous, copy, static_cast<size_t>(size));
    std::free(copy);
    return g_memoryError = error;
}
