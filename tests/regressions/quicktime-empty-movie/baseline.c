/* SPDX-License-Identifier: GPL-3.0-or-later
 * Baseline-only observation with the original untyped header, not a typed
 * cross-translation-unit call into an incompatible old declaration.
 */
#include <QuickTime/QuickTime.h>
int main(void) { return NewMovie() == 0 ? 1 : 0; }
