/* SPDX-License-Identifier: GPL-3.0-or-later
 * Minimal host dependency fixture. NOT CoreFoundation or a guest ABI check.
 */
#ifndef CARBON_ISOLATED_CFBASE_H
#define CARBON_ISOLATED_CFBASE_H
#include <stddef.h>
typedef const void* CFTypeRef;
typedef const struct __CFAllocator* CFAllocatorRef;
typedef ptrdiff_t CFIndex;
typedef unsigned long CFOptionFlags;
CFAllocatorRef CFAllocatorGetDefault(void);
CFTypeRef CFRetain(CFTypeRef);
void CFRelease(CFTypeRef);
void* CFAllocatorAllocate(CFAllocatorRef, CFIndex, CFOptionFlags);
void CFAllocatorDeallocate(CFAllocatorRef, void*);
#endif
