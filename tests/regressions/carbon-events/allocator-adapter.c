/* SPDX-License-Identifier: GPL-3.0-or-later
 * Test-only allocator adapter: these are not the CoreFoundation runtime.
 * Implements only the CF entry points used by Carbon event storage.
 */
#include "allocator-adapter.h"
#include <assert.h>
#include <stdlib.h>

struct TestAllocator {
    unsigned references, allocations, frees;
};
static struct TestAllocator defaultAllocator = {1, 0, 0};
static struct TestAllocator customAllocator = {1, 0, 0};
static struct TestAllocator* currentDefault = &defaultAllocator;
static int failNext;

static struct TestAllocator* checked(const void* allocator)
{
    assert(allocator == &defaultAllocator || allocator == &customAllocator);
    return (struct TestAllocator*)allocator;
}

CFAllocatorRef test_default_allocator(void) { return (CFAllocatorRef)&defaultAllocator; }
CFAllocatorRef test_custom_allocator(void) { return (CFAllocatorRef)&customAllocator; }
void test_set_default(CFAllocatorRef allocator) { currentDefault = checked(allocator); }
void test_fail_next_allocation(void) { failNext = 1; }
unsigned test_allocations(CFAllocatorRef allocator) { return checked(allocator)->allocations; }
unsigned test_frees(CFAllocatorRef allocator) { return checked(allocator)->frees; }
unsigned test_references(CFAllocatorRef allocator) { return checked(allocator)->references; }

CFAllocatorRef CFAllocatorGetDefault(void) { return (CFAllocatorRef)currentDefault; }
CFTypeRef CFRetain(CFTypeRef value)
{
    ++checked(value)->references;
    return value;
}
void CFRelease(CFTypeRef value)
{
    struct TestAllocator* allocator = checked(value);
    assert(allocator->references > 1);
    --allocator->references;
}
void* CFAllocatorAllocate(CFAllocatorRef value, CFIndex size, CFOptionFlags hint)
{
    (void)hint;
    struct TestAllocator* allocator = checked(value);
    if (failNext) { failNext = 0; return NULL; }
    void* allocation = malloc((size_t)size);
    if (allocation) ++allocator->allocations;
    return allocation;
}
void CFAllocatorDeallocate(CFAllocatorRef value, void* pointer)
{
    ++checked(value)->frees;
    free(pointer);
}
