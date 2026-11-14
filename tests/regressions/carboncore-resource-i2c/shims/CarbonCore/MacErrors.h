// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <CarbonCore/Resources.h>
constexpr OSErr noErr = 0;
constexpr OSErr fnfErr = -43;
constexpr OSErr eofErr = -39;
constexpr OSErr wPrErr = -44;
constexpr OSErr ioErr = -36;
constexpr OSErr dskFulErr = -34;
constexpr OSErr mapReadErr = -199;
constexpr OSErr resNotFound = -192;
constexpr OSErr resFNotFound = -193;
constexpr OSErr rmvResFailed = -196;
constexpr OSErr addResFailed = -194;
constexpr OSErr inputOutOfBounds = -190;
constexpr OSErr memFullErr = -108;
constexpr OSErr nilHandleErr = -109;
constexpr OSErr memAdrErr = -110;
constexpr OSErr memWZErr = -111;
constexpr OSErr memPurErr = -112;
constexpr OSErr memLockedErr = -117;
constexpr OSErr paramErr = -50;
// Upstream Darling (2026-11) FSCreateResFile error results.
constexpr OSErr bdNamErr = -37;
constexpr OSErr dupFNErr = -48;
constexpr OSErr permErr = -54;
constexpr OSErr dirNFErr = -120;
constexpr OSErr errFSBadForkName = -1413;
constexpr OSErr unimpErr = -4;
