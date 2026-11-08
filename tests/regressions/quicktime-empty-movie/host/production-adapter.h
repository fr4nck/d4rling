/* SPDX-License-Identifier: GPL-3.0-or-later
 * MSVC-only host substitutions. No production logic is replaced.
 * The original constructor only initializes STUB_VERBOSE; it is omitted.
 */
#include <stdlib.h>
#include "../allocator-api.h"
#define __attribute__(x)
#define malloc d4rl_test_malloc
#define free d4rl_test_free
