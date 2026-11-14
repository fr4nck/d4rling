// SPDX-License-Identifier: GPL-3.0-or-later
// Only non-Carbon file-reference functions/types are host-adapted.
#pragma once
#include <CoreServices/MacTypes.h>
#include <cstddef>
struct FSRef { char path[1024]; };
struct HFSUniStr255 { UInt16 length; UniChar unicode[255]; };
struct FSSpec { char unused[70]; };
using FSSpecPtr = FSSpec*;
using FSCatalogInfoBitmap = uint32_t;
struct FSCatalogInfo { struct { UInt16 mode; } permissions; };
extern "C" OSErr FSRefMakePath(const FSRef*, UInt8*, UInt32);

// Real FileManager transitively exposes CarbonCore error constants.
#include <CarbonCore/MacErrors.h>

// Upstream Darling (2026-11) FSCreateResFile: link-only adaptations, never
// called by the I2-C contract (which does not create resource files).
enum : FSCatalogInfoBitmap { kFSCatInfoPermissions = 0x00000400 };
extern "C" inline OSErr FSPathMakeRef(const UInt8*, FSRef*, Boolean*) { return -50; }
