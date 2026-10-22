/* SPDX-License-Identifier: GPL-3.0-or-later
 * Minimal host fixture; production uses Darling's MacErrors.h.
 */
#ifndef CARBON_ISOLATED_MACERRORS_H
#define CARBON_ISOLATED_MACERRORS_H
enum { noErr = 0, paramErr = -50, memFullErr = -108, unimpErr = -4,
       errAECoercionFail = -1700, errAEBufferTooSmall = -1741 };
#endif
