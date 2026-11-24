
/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Private compatibility helpers, not QuickTime public API. */

typedef unsigned long long U64;

static U64 divide(U64 n, U64 d, U64 *remainder)
{
    U64 q = 0;

    if (!d)
        __builtin_trap();

    for (int i = 63; i >= 0; --i) {
        if ((n >> i) >= d) {
            n -= d << i;
            q |= 1ULL << i;
        }
    }

    if (remainder)
        *remainder = n;

    return q;
}

__attribute__((visibility("hidden")))
U64 __udivdi3(U64 n, U64 d)
{
    return divide(n, d, (void *)0);
}

__attribute__((visibility("hidden")))
U64 __umoddi3(U64 n, U64 d)
{
    U64 r;
    divide(n, d, &r);
    return r;
}
