#pragma once
#include <MacTypes.h>
#include <cstdint>
using SInt8 = int8_t;
using ResID = int16_t;
using ResType = uint32_t;
using ResAttributes = int16_t;
using ResFileAttributes = int16_t;
constexpr OSErr noErr = 0;
constexpr OSErr fnfErr = -43;
constexpr OSErr eofErr = -39;
constexpr OSErr fsRdPerm = 1;
constexpr OSErr fsWrPerm = 2;
constexpr OSErr fsRdWrPerm = 3;
constexpr OSErr wPrErr = -44;
constexpr OSErr ioErr = -36;
constexpr OSErr dskFulErr = -34;
constexpr OSErr mapReadErr = -199;
constexpr OSErr resNotFound = -192;
