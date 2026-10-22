/* SPDX-License-Identifier: GPL-3.0-or-later
 * Minimal host dependency fixture; NOT Darling's MacTypes or ABI validation.
 */
#ifndef CARBON_ISOLATED_MACTYPES_H
#define CARBON_ISOLATED_MACTYPES_H
#include <stdint.h>
typedef uint32_t UInt32, OSType;
/* The pinned Darling headers use unsigned long for these host types. */
typedef unsigned long ItemCount, ByteCount;
typedef uint16_t UInt16;
typedef int16_t SInt16;
typedef int32_t OSStatus;
typedef uint8_t Boolean;
#endif
