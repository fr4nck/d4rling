// SPDX-License-Identifier: GPL-3.0-or-later
// Link-time stand-ins for the host ELF checks of MacWindows.cpp. These tests exercise
// argument checking and the path without a window backend (no X11 on the host:
// /usr/lib/native/libX11.dylib cannot be loaded), where neither CoreFoundation strings
// nor the Resource Manager are reached. Any call fails the test loudly.
#include <stdio.h>
#include <stdlib.h>
#include <CoreFoundation/CFString.h>
#include <CarbonCore/MacMemory.h>
#include <CarbonCore/Resources.h>

static void unexpected(const char* name)
{
	fprintf(stderr, "FAIL: host shim %s reached (not expected without a window backend)\n", name);
	exit(70);
}

const CFAllocatorRef kCFAllocatorDefault = NULL;
CFIndex CFStringGetLength(CFStringRef s) { (void) s; unexpected("CFStringGetLength"); return 0; }
CFIndex CFStringGetMaximumSizeForEncoding(CFIndex l, CFStringEncoding e) { (void) l; (void) e; unexpected("CFStringGetMaximumSizeForEncoding"); return 0; }
Boolean CFStringGetCString(CFStringRef s, char* b, CFIndex n, CFStringEncoding e) { (void) s; (void) b; (void) n; (void) e; unexpected("CFStringGetCString"); return 0; }
Boolean CFStringGetPascalString(CFStringRef s, StringPtr b, CFIndex n, CFStringEncoding e) { (void) s; (void) b; (void) n; (void) e; unexpected("CFStringGetPascalString"); return 0; }
CFStringRef CFStringCreateWithPascalString(CFAllocatorRef a, ConstStr255Param p, CFStringEncoding e) { (void) a; (void) p; (void) e; unexpected("CFStringCreateWithPascalString"); return NULL; }
CFStringRef CFStringCreateCopy(CFAllocatorRef a, CFStringRef s) { (void) a; (void) s; unexpected("CFStringCreateCopy"); return NULL; }
Handle GetResource(ResType t, ResID i) { (void) t; (void) i; unexpected("GetResource"); return NULL; }
Size GetHandleSize(Handle h) { (void) h; unexpected("GetHandleSize"); return 0; }
