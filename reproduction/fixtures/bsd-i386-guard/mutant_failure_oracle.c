/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Independently execute the deliberately broken no-cmc i386 CF conversion.
 * This is an x86 host CPU witness, NOT a Darling guest or a real XNU stub.
 * The 71 failures correspond exactly to the fixed inputs in probe-cf.c.
 */
#include <stdint.h>
#include <stdio.h>

#if !defined(__i386__) && !defined(__x86_64__)
#error "This witness needs an x86 CPU to execute carry flag instructions"
#endif

struct outcome { uint32_t eax, errno_value; unsigned cf; };
static struct outcome no_cmc(uint32_t raw) {
    uint32_t eax = raw, errno_value = 77;
    unsigned char carry;
    __asm__ volatile (
        "cmpl $-4095, %[eax]\n\t"
        "jnc 9f\n\t"
        "negl %[eax]\n\t"
        "movl %[eax], %[errno_value]\n\t"
        "movl $-1, %[eax]\n\t"
        "9:\n\t"
        "setc %[carry]"
        : [eax] "+r" (eax), [errno_value] "+m" (errno_value),
          [carry] "=qm" (carry)
        :
        : "cc", "memory"
    );
    return (struct outcome){eax, errno_value, carry};
}

/* The first five values are successful raw results, the next four errors.
 * The list is in the exact order of known_case() calls in probe-cf.c. */
static const uint32_t known[9] = {
    0u, 0x12345678u, 0xfffff000u, 0x80000000u, 0xffffefffu,
    0xfffff001u, 0xffffffb2u, 0xfffffffeu, 0xffffffffu
};

int main(void) {
    unsigned known_failures = 0, unknown_failures = 0;
    for (unsigned i = 0; i < 9; i++) {
        for (unsigned repeat = 0; repeat < 2; repeat++) {
            uint32_t raw = known[i];
            int success = (i < 5);
            struct outcome got = no_cmc(raw);
            uint32_t expected_errno = success ? 77u : (uint32_t)(0u - raw);
            known_failures += (got.eax != (success ? raw : 0xffffffffu));
            known_failures += (got.cf != (success ? 0u : 1u));
            known_failures += (got.errno_value != expected_errno);
        }
    }
    for (unsigned i = 0; i < 7; i++) {
        struct outcome got = no_cmc((uint32_t)-78);
        unknown_failures += (got.eax != 0xffffffffu);
        unknown_failures += (got.cf != 1u);
        unknown_failures += (got.errno_value != 78u);
    }
    printf("I1_MUTANT_KNOWN_FAILURES=%u\n", known_failures);
    printf("I1_MUTANT_UNKNOWN_FAILURES=%u\n", unknown_failures);
    printf("I1_MUTANT_FAILURES=%u\n", known_failures + unknown_failures);
    printf("I1_MUTANT_EXPECTED_CHECKS=222\n");
    return (known_failures == 50 && unknown_failures == 21) ? 0 : 10;
}
