// SPDX-License-Identifier: GPL-3.0-or-later
// Link-only host adaptation for upstream Darling (2026-11) FSCreateResFile;
// the I2-C contract never creates resource files, so these are not exercised.
#pragma once
#include <CoreServices/MacTypes.h>
using CFStringRef = const struct __CFString*;
using CFAllocatorRef = const struct __CFAllocator*;
using CFIndex = long;
extern "C" inline CFStringRef CFStringCreateWithCharacters(CFAllocatorRef, const UniChar*, CFIndex) { return nullptr; }
extern "C" inline Boolean CFStringGetFileSystemRepresentation(CFStringRef, char*, CFIndex) { return 0; }
extern "C" inline void CFRelease(const void*) {}
