/* SPDX-License-Identifier: GPL-3.0-or-later
 * Runtime smoke check for a REAL CoreFoundation library loaded by Darling.
 * This test deliberately uses Apple's published CoreFoundation API.
 * A host ELF run or a test allocator does NOT qualify as a Mach-O PASS.
 */
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <string.h>

static unsigned checks = 0;
static unsigned failures = 0;

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

    /* Exercise the real CFRetain/CFRelease with a CFAllocator object. */
    CFTypeRef retained = CFRetain(allocator);
    CHECK(retained == allocator);
    CFRelease(allocator);

    /* Allocate/write/read/release using the real CoreFoundation allocator. */
    static const CFIndex sizes[] = { 1, 7, 64, 4096 };
    for (unsigned i = 0; i < sizeof(sizes) / sizeof(sizes[0]); ++i) {
        unsigned char *memory = CFAllocatorAllocate(allocator, sizes[i], 0);
        CHECK(memory != NULL);
        if (!memory)
            continue;
        memset(memory, 0xa5, (size_t)sizes[i]);
        CHECK(memory[0] == 0xa5);
        CHECK(memory[sizes[i] - 1] == 0xa5);
        CFAllocatorDeallocate(allocator, memory);
    }

    /* A Create API returns caller-owned CoreFoundation memory. */
    CFStringRef string = CFStringCreateWithCString(
        allocator, "d4rling real CoreFoundation runtime smoke: 2026", kCFStringEncodingUTF8);
    CHECK(string != NULL);
    if (string) {
        CFIndex before = CFGetRetainCount(string);
        CHECK(before >= 1);
        CFTypeRef again = CFRetain(string);
        CHECK(again == string);
        CFIndex after = CFGetRetainCount(string);
        CHECK(after >= before);
        CFRelease(string);
        CFRelease(string);
    }

    printf("CoreFoundation Mach-O runtime checks: %u | Failures: %u\n", checks, failures);
    return failures ? 1 : 0;
}
