/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Host CPU witness for the i386 Darwin syscall-result conversion sequence.
 * Replicates the five instructions in upstream darling-xnu SYS.h (DARLING).
 * Does not run i386 stubs inside Darling or implement cerror/TLS.
 */
#include <stdint.h>
#include <stdio.h>

#if !defined(__i386__) && !defined(__x86_64__)
#error Requires an x86 CPU for x86 flags semantics
#endif

struct outcome { uint32_t eax; unsigned carry; };

static struct outcome to_cf(uint32_t raw)
{
    unsigned char carry;
    __asm__ volatile (
        "cmpl $-4095, %[value]\n\t"
        "cmc\n\t"
        "jnc 9f\n\t"
        "negl %[value]\n\t"
        "9:\n\t"
        "setc %[carry]"
        : [value] "+r" (raw), [carry] "=qm" (carry)
        :
        : "cc"
    );
    struct outcome out = {raw, carry};
    return out;
}

/* Deliberately wrong: omitting cmc must be detected by this witness. */
static struct outcome mutant_without_cmc(uint32_t raw)
{
    unsigned char carry;
    __asm__ volatile (
        "cmpl $-4095, %[value]\n\t"
        "jnc 9f\n\t"
        "negl %[value]\n\t"
        "9:\n\t"
        "setc %[carry]"
        : [value] "+r" (raw), [carry] "=qm" (carry)
        :
        : "cc"
    );
    struct outcome out = {raw, carry};
    return out;
}

struct testcase {
    uint32_t raw;
    uint32_t eax;
    unsigned carry;
    const char *name;
};

static const struct testcase cases[] = {
    {0x00000000u, 0x00000000u, 0, "zero"},
    {0x00000001u, 0x00000001u, 0, "one"},
    {0x0000007bu, 0x0000007bu, 0, "positive"},
    {0x7fffffffu, 0x7fffffffu, 0, "int_max"},
    {0x80000000u, 0x80000000u, 0, "int_min_success"},
    {0xffffefffu, 0xffffefffu, 0, "below_errno_range"},
    {0xfffff000u, 0xfffff000u, 0, "minus_4096_success"},
    {0xfffff001u, 0x00000fffu, 1, "minus_4095_error"},
    {0xffffffb2u, 0x0000004eu, 1, "minus_78_enosys"},
    {0xfffffffeu, 0x00000002u, 1, "minus_2_error"},
    {0xffffffffu, 0x00000001u, 1, "minus_1_error"},
};

int main(void)
{
    unsigned errors = 0;
    unsigned checks = 0;
    for (unsigned i = 0; i < sizeof cases / sizeof cases[0]; ++i) {
        struct outcome got = to_cf(cases[i].raw);
        ++checks;
        if (got.eax != cases[i].eax || got.carry != cases[i].carry) {
            ++errors;
            fprintf(stderr,
                "STUB_CF_CASE=%s FAIL raw=0x%08x eax=0x%08x carry=%u"
                " expected_eax=0x%08x expected_carry=%u\n",
                cases[i].name, cases[i].raw, got.eax, got.carry,
                cases[i].eax, cases[i].carry);
        }
    }
    unsigned detected = 0;
    for (unsigned i = 0; i < sizeof cases / sizeof cases[0]; ++i) {
        struct outcome got = mutant_without_cmc(cases[i].raw);
        if (got.eax != cases[i].eax || got.carry != cases[i].carry)
            ++detected;
    }
    ++checks;
    if (!detected) ++errors;
    printf("STUB_CF_MUTANT_DETECTED=%s CASES=%u\n",
           detected ? "PASS" : "FAIL", detected);
    printf("STUB_CF_HOST_CHECKS=%u FAILURES=%u\n", checks, errors);
    puts("STUB_CF_GUEST_I386=OPEN");
    return errors ? 10 : 0;
}
