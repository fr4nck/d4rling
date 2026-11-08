/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>

struct input { uint32_t nr, wrapper, args[14]; };
struct output { uint32_t eax, edx, cf, stack_delta; };
extern void fixture_invoke(const struct input *, struct output *);
extern void fixture_observer(void), fixture_returner(void);
void *__fixture_bsd_table[600];
uint32_t fixture_errno, observed_args[14], observed_alignment;
uint32_t unknown_number, unknown_calls;
static unsigned checks, errors;

static void expect(int condition, const char *name)
{
    ++checks;
    if (!condition) {
        if (errors < 20) printf("FAIL %s check=%u\n", name, checks);
        ++errors;
    }
}

static struct input input(uint32_t nr, uint32_t low, uint32_t high, int carry)
{
    struct input in = {0};
    unsigned i;
    in.nr = nr;
    in.args[0] = low;
    in.args[1] = high;
    in.args[2] = carry;
    for (i = 3; i < 14; ++i) in.args[i] = 0x10203040u + i * 0x01010101u;
    return in;
}

static void check_value(uint32_t nr, uint32_t low, uint32_t high,
                        int incoming_carry, int error)
{
    struct input in = input(nr, low, high, incoming_carry);
    struct output out;
    fixture_invoke(&in, &out);
    expect(out.eax == (error ? 0u - low : low), "raw EAX");
    expect(out.edx == high, "raw EDX preserved");
    expect(out.cf == (uint32_t)error, "raw CF");
    expect(out.stack_delta == 0, "stack restored");
    expect(observed_alignment == 0, "handler C call alignment");
    expect(memcmp(observed_args, in.args, sizeof(in.args)) == 0, "14 arguments forwarded");
    in.wrapper = 1;
    fixture_errno = 77;
    fixture_invoke(&in, &out);
    expect(out.eax == (error ? UINT32_MAX : low), "stub result");
    expect(out.edx == (error ? UINT32_MAX : high), "stub high word");
    expect(fixture_errno == (error ? 0u - low : 77u), "stub errno");
    expect(out.stack_delta == 0, "stub stack restored");
}

static void check_unknown(uint32_t nr)
{
    struct input in = input(nr, 0, 0, 0);
    struct output out;
    unsigned calls = unknown_calls;
    fixture_invoke(&in, &out);
    expect(unknown_calls == calls + 1, "unknown handler called");
    expect(unknown_number == (nr & 0xffff), "unknown receives masked number");
    expect(observed_alignment == 0, "unknown C call alignment");
    expect(out.eax == 78 && out.cf == 1, "unknown ENOSYS protocol");
    expect(out.stack_delta == 0, "unknown stack restored");
    in.wrapper = 1;
    fixture_errno = 77;
    fixture_invoke(&in, &out);
    expect(out.eax == UINT32_MAX && fixture_errno == 78, "unknown stub errno");
}

static void *stress(void *arg)
{
    uint32_t seed = (uint32_t)(uintptr_t)arg;
    unsigned i, failed = 0;
    for (i = 0; i < 2000; ++i) {
        uint32_t low = 0x80000000u + seed * 4096 + i;
        struct input in = input(34, low, 0x12345678u + seed, i & 1);
        struct output out;
        fixture_invoke(&in, &out);
        if (out.eax != low || out.edx != in.args[1] || out.cf || out.stack_delta) ++failed;
    }
    return (void *)(uintptr_t)failed;
}

int main(int argc, char **argv)
{
    static const uint32_t successes[] = {
        0, 1, 42, 4095, 0x7fffffff, 0x80000000, 0xefffffff,
        0xffffefff, 0xfffff000
    };
    static const uint32_t highs[] = {0, 1, 0x7fffffff, 0x80000000, UINT32_MAX};
    unsigned i, j, n;
    int baseline = argc > 1 && strcmp(argv[1], "--baseline") == 0;
    pthread_t threads[4];
    int created[4];
    printf("FIXTURE_STARTED POINTER_SIZE=%u BASELINE=%d\n", (unsigned)sizeof(void *), baseline);
    expect(sizeof(void *) == 4, "i386 pointers");
    __fixture_bsd_table[33] = fixture_observer;
    __fixture_bsd_table[34] = fixture_returner;
    __fixture_bsd_table[199] = fixture_observer;
    for (i = 0; i < sizeof(successes) / sizeof(successes[0]); ++i)
        for (j = 0; j < 2; ++j)
            check_value(33 | (20u << 16), successes[i], 0xa5a5a5a5, j, 0);
    for (n = 1; n <= 4095; ++n) {
        /* Scalar errors must ignore arbitrary EDX left by a 32-bit C callee. */
        check_value(33, 0u - n, n * 12345u, n & 1, 1);
        /* A real 64-bit negative error is sign-extended in EDX:EAX. */
        check_value(199, 0u - n, UINT32_MAX, n & 1, 1);
    }
    for (i = 0; i < sizeof(highs) / sizeof(highs[0]); ++i) {
        for (j = 0; j < sizeof(successes) / sizeof(successes[0]); ++j)
            check_value(199, successes[j], highs[i], 1, 0);
        if (highs[i] != UINT32_MAX) {
            check_value(199, UINT32_MAX, highs[i], 0, 0);
            check_value(199, 0xfffff001, highs[i], 1, 0);
        }
    }
    check_unknown(8); /* Known NULL slot, never an actual unknown host syscall. */
    check_unknown(8 | (12u << 16));
    check_unknown(599);
    if (!baseline) {
        check_unknown(600);
        check_unknown(65535);
        check_unknown(UINT32_MAX);
    }
    printf("SINGLE_CHECKS=%u SINGLE_ERRORS=%u\n", checks, errors);
    for (i = 0; i < 4; ++i) {
        created[i] = pthread_create(&threads[i], NULL, stress, (void *)(uintptr_t)(i + 1)) == 0;
        expect(created[i], "create stress thread");
    }
    for (i = 0; i < 4; ++i) if (created[i]) {
        void *value = NULL;
        expect(pthread_join(threads[i], &value) == 0, "join stress thread");
        expect(value == NULL, "2000 independent thread returns");
    }
    printf("FIXTURE_CHECKS=%u FIXTURE_ERRORS=%u THREAD_CALLS=8000\nFIXTURE_FINISHED\n", checks, errors);
    return errors ? 10 : 0;
}
