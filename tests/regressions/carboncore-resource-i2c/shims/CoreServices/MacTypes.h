// SPDX-License-Identifier: GPL-3.0-or-later
// ABI host type adaptation; real public CarbonCore/Resources.h stays included.
#pragma once
#include <cstdint>
using UInt8 = uint8_t;
using SInt8 = int8_t;
using UInt16 = uint16_t;
using SInt16 = int16_t;
using UInt32 = uint32_t;
using SInt32 = int32_t;
using UniChar = uint16_t;
using UniCharCount = unsigned long;
using ResType = uint32_t;
using OSErr = int16_t;
using OSStatus = int32_t;
using Ptr = char*;
using Handle = Ptr*;
using Size = long;
using Boolean = uint8_t;
using Str255 = UInt8[256];
using ConstStr255Param = const UInt8*;
// Upstream Darling (2026-11) Resources.h SPI declarations need these types.
using UInt64 = uint64_t;
using StringPtr = UInt8*;
