/*
This file is part of Darling.

Copyright (C) 2012-2013 Lubos Dolezel

Darling is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Darling is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Darling.  If not, see <http://www.gnu.org/licenses/>.
*/

#include <CarbonCore/MacErrors.h>
#include <cstring>
#include <climits>
#include <sys/sysctl.h>
#include <CarbonCore/Gestalt.h>

// Decimal components must be complete, unsigned and representable as int.
// Keep the checked parser introduced in G3; a Darwin release must never be
// converted into a macOS product version by arithmetic on its components.
static bool parseReleaseNumber(const char*& cursor, int& result)
{
    if (*cursor < '0' || *cursor > '9')
        return false;

    int number = 0;
    do {
        const int digit = *cursor - '0';
        if (number > (INT_MAX - digit) / 10)
            return false;
        number = number * 10 + digit;
        ++cursor;
    } while (*cursor >= '0' && *cursor <= '9');

    result = number;
    return true;
}

// ProductVersion can contain two or three decimal components (e.g. 10.16
// and 11.7.4 in the prefix's compatibility and primary plists).
static bool parseProductVersion(const char* version, int& major, int& minor, int& patch)
{
    const char* cursor = version;
    if (!parseReleaseNumber(cursor, major) || major == 0 || *cursor != '.' ||
        !parseReleaseNumber(++cursor, minor))
        return false;

    patch = 0;
    if (*cursor == '.') {
        if (!parseReleaseNumber(++cursor, patch))
            return false;
    }
    return *cursor == '\0';
}

static bool readProductVersion(int& major, int& minor, int& patch)
{
    // Darling's pinned XNU provides this string via kern.osproductversion.
    // It agrees with the primary SystemVersion.plist, unlike KERN_OSRELEASE.
    char version[64] = {};
    size_t length = sizeof(version);
    if (sysctlbyname("kern.osproductversion", version, &length, nullptr, 0) != 0 ||
        length == 0 || length > sizeof(version) ||
        std::memchr(version, '\0', length) != version + length - 1)
        return false;

    return parseProductVersion(version, major, minor, patch);
}

static bool encodeLegacySystemVersion(int major, int minor, int patch, int& value)
{
    // Gestalt's four BCD-like digits: 10.4.0 -> 0x1040 and 10.3.15 ->
    // 0x1039. Minor and bug-fix are saturated at 9 (Apple contract).
    // The legacy representation cannot encode a three-digit major version.
    //
    // QUIRK (from darlinghq/darling a4008ba7b/4bc556030): for macOS 11 and
    // later the packed value keeps the same layout, with the major version
    // as two BCD digits in the high byte; macOS 27.0.1 returns 0x2701 with
    // noErr. Not documented. Evidence: black-box observation on macOS 27.0.1
    // arm64, native, under Rosetta, with an SDK 10.15 binary and with
    // SYSTEM_VERSION_COMPAT=1, all identical (tier 2). Saturating minor and
    // bug-fix at 9 for these majors is carried over from the 10.x rule by
    // inference. Tests: tests/gestalt-system-version.rb,
    // tests/src/gestalt_version.c and
    // reproduction/fixtures/carboncore/check_gestalt_selectors.py.
    if (major < 1 || major > 99)
        return false;
    const int minorDigit = minor > 9 ? 9 : minor;
    const int patchDigit = patch > 9 ? 9 : patch;
    value = ((major / 10) << 12) | ((major % 10) << 8) |
            (minorDigit << 4) | patchDigit;
    return true;
}

OSStatus Gestalt(uint32_t type, int* value)
{
    if (value == nullptr)
        return paramErr;

    switch (type) {
    case gestaltSystemVersion:
    case gestaltSystemVersionMajor:
    case gestaltSystemVersionMinor:
    case gestaltSystemVersionPatch:
    {
        int major = 0, minor = 0, patch = 0;
        if (!readProductVersion(major, minor, patch)) {
            *value = 0;
            return gestaltUnknownErr;
        }

        if (type == gestaltSystemVersion) {
            if (!encodeLegacySystemVersion(major, minor, patch, *value)) {
                *value = 0;
                return gestaltUnknownErr;
            }
        } else if (type == gestaltSystemVersionMajor) {
            *value = major;
        } else if (type == gestaltSystemVersionMinor) {
            *value = minor;
        } else {
            *value = patch;
        }
        break; // G1: do not fall through to gestaltSysArchitecture.
    }
    case gestaltSysArchitecture:
#if defined(__powerpc__)
        *value = gestaltPowerPC;
#elif defined(__x86_64__) || defined(__i386__)
        *value = gestaltIntel;
#else
        *value = 0;
        return gestaltUnknownErr;
#endif
        break;
    case gestaltCarbonVersion:
        // CarbonCore/HIToolbox currently cover only part of Carbon. No
        // defensible Carbon API release number is established by that subset.
        *value = 0;
        return gestaltUndefSelectorErr;
    default:
        *value = 0;
        return gestaltUndefSelectorErr;
    }
    return 0;
}
