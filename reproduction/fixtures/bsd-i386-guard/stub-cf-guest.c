/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Mach-O i386 guest witness: assembled conversion mirror, not XNU cerror. */
struct outcome { unsigned eax; unsigned carry; };
extern void guard_stub_capture(unsigned raw, struct outcome *out);
extern int printf(const char *fmt, ...);

struct testcase {
    unsigned raw;
    unsigned eax;
    unsigned carry;
};

static const struct testcase cases[] = {
    {0x00000000u, 0x00000000u, 0},
    {0x00000001u, 0x00000001u, 0},
    {0x0000007bu, 0x0000007bu, 0},
    {0x7fffffffu, 0x7fffffffu, 0},
    {0x80000000u, 0x80000000u, 0},
    {0xffffefffu, 0xffffefffu, 0},
    {0xfffff000u, 0xfffff000u, 0},
    {0xfffff001u, 0x00000fffu, 1},
    {0xffffffb2u, 0x0000004eu, 1},
    {0xfffffffeu, 0x00000002u, 1},
    {0xffffffffu, 0x00000001u, 1},
};

int main(void)
{
    unsigned errors = 0;
    unsigned checks = 0;
    printf("STUB_CF_GUEST_BEGIN\n");
    for (unsigned i = 0; i < sizeof cases / sizeof cases[0]; ++i) {
        struct outcome result = {0};
        guard_stub_capture(cases[i].raw, &result);
        ++checks;
        if (result.eax != cases[i].eax || result.carry != cases[i].carry) {
            ++errors;
            printf("STUB_CF_GUEST_CASE=%u FAIL raw=%u eax=%u cf=%u\n",
                   i, cases[i].raw, result.eax, result.carry);
        }
    }
    ++checks;
    if (sizeof(void *) != 4) ++errors;
    printf("STUB_CF_GUEST_CHECKS=%u FAILURES=%u\n", checks, errors);
    printf("STUB_CF_GUEST_FINISHED\n");
    return errors ? 10 : 0;
}
