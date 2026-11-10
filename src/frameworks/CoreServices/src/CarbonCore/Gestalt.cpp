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
#include <cstdio>
#include <sys/sysctl.h>
#include <CarbonCore/Gestalt.h>

// KERN_OSRELEASE is a dotted Darwin kernel release, not a macOS version.
// Parse each component without scanf integer overflow or accepting suffixes.
static bool parseReleaseNumber(const char*& cursor, int& result)
{
    if (*cursor < '0' || *cursor > '9')
        return false;

    int value = 0;
    do {
        const int digit = *cursor - '0';
        if (value > (INT_MAX - digit) / 10)
            return false;
        value = value * 10 + digit;
        ++cursor;
    } while (*cursor >= '0' && *cursor <= '9');

    result = value;
    return true;
}

OSStatus Gestalt(uint32_t type, int* value)
{
	if (value == nullptr)
		return paramErr;

	switch (type)
	{
	case gestaltSystemVersion:
	case gestaltSystemVersionMajor:
	case gestaltSystemVersionMinor:
	case gestaltSystemVersionPatch:
	{
		// We may be mixing the Darwin and OS version, but this API is deprecated anyway
		int name[2] = { CTL_KERN, KERN_OSRELEASE };
		char version[32] = {};
		size_t version_len = sizeof(version) - 1;
		int maj = 0, min = 0, patch = 0;

		if (sysctl(name, 2, version, &version_len, nullptr, 0) != 0 ||
			version_len == 0 || version_len > sizeof(version) - 1) {
			*value = 0;
			return unimpErr;
		}
		version[version_len] = '\0';
		const char* cursor = version;
		if (!parseReleaseNumber(cursor, maj) || *cursor != '.' ||
			!parseReleaseNumber(++cursor, min) || *cursor != '.' ||
			!parseReleaseNumber(++cursor, patch) || *cursor != '\0') {
			*value = 0;
			return unimpErr;
		}

		// Preserve the legacy encoding for now, but never overflow its int result.
		if (type == gestaltSystemVersion && 0x100LL * maj + 0x10LL * min > INT_MAX) {
			*value = 0;
			return unimpErr;
		}

		if (type == gestaltSystemVersion)
			*value = static_cast<int>(0x100LL * maj + 0x10LL * min);
		else if (type == gestaltSystemVersionMajor)
			*value = maj;
		else if (type == gestaltSystemVersionMinor)
			*value = min;
		else if (type == gestaltSystemVersionPatch)
			*value = patch;
		break;
	}
	case gestaltSysArchitecture:
#ifdef __powerpc__
		*value = gestaltPowerPC;
#elif defined(__x86_64__) || defined(__i386__)
		*value = gestaltIntel;
#endif
		break;
	default:
		*value = 0;
		return unimpErr;
	}
	return 0;
}
