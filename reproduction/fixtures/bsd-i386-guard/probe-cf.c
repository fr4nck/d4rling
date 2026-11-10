/* SPDX-License-Identifier: GPL-3.0-or-later */
/* i386 Mach-O integration fixture: real BSD dispatcher with synthetic
 * table/handlers and a mirrored SYS.h conversion, not real cerror/TLS.
 */
struct input { unsigned nr, wrapper, args[14]; };
struct output { unsigned eax, edx, cf, stack_delta; };
extern void fixture_invoke_cf(const struct input *, struct output *);
extern void fixture_returner(void);
extern void fixture_observer(void);
extern int printf(const char *, ...);

void *__fixture_bsd_table[600];
unsigned fixture_errno;
unsigned observed_args[14], observed_alignment;
unsigned unknown_number, unknown_calls;
static unsigned checks, errors;

static void expect(int passed, const char *name) {
    ++checks;
    if (!passed) {
        ++errors;
        if (errors <= 20)
            printf("GUARD_CF_FAIL=%s CHECK=%u\n", name, checks);
    }
}
static struct input make_input(unsigned nr, unsigned value, unsigned carry) {
    struct input in = {0};
    in.nr = nr;
    in.args[0] = value;
    in.args[1] = 0x31415926u;
    in.args[2] = carry;
    for (unsigned i = 3; i < 14; ++i) in.args[i] = 0x11220000u + i;
    return in;
}
static void known_case(unsigned nr, unsigned value, unsigned success, unsigned err) {
    printf("GUARD_CF_KNOWN=%u RAW=%u\n", nr, value);
    for (unsigned incoming_cf = 0; incoming_cf < 2; ++incoming_cf) {
        struct input in = make_input(nr, value, incoming_cf);
        struct output out = {0};
        unsigned old_unknown = unknown_calls;
        in.wrapper = 0;
        fixture_invoke_cf(&in, &out);
        expect(out.eax == value, "KNOWN_RAW_EAX");
        expect(out.stack_delta == 0, "KNOWN_RAW_STACK");
        expect(old_unknown == unknown_calls, "KNOWN_RAW_HANDLER");
        /* CF of the raw entry is irrelevant; the checked stub must reset it. */
        in.wrapper = 1;
        fixture_errno = 77;
        fixture_invoke_cf(&in, &out);
        expect(out.eax == (success ? value : 0xffffffffu), "KNOWN_CHECKED_EAX");
        expect(out.cf == (success ? 0u : 1u), "KNOWN_CHECKED_CF");
        expect(fixture_errno == (success ? 77u : err), "KNOWN_CHECKED_ERRNO");
        expect(out.stack_delta == 0, "KNOWN_CHECKED_STACK");
        expect(old_unknown == unknown_calls, "KNOWN_CHECKED_HANDLER");
    }
}
static void unknown_case(unsigned nr) {
    unsigned masked = nr & 0xffffu;
    printf("GUARD_CF_UNKNOWN=%u MASKED=%u\n", nr, masked);
    struct input in = make_input(nr, 0, 0);
    struct output out = {0};
    unsigned before = unknown_calls;
    in.wrapper = 0;
    fixture_invoke_cf(&in, &out);
    expect(out.eax == (unsigned)-78, "UNKNOWN_RAW_ENOSYS");
    expect(out.stack_delta == 0, "UNKNOWN_RAW_STACK");
    expect(unknown_calls == before + 1, "UNKNOWN_RAW_COUNT");
    expect(unknown_number == masked, "UNKNOWN_RAW_NR");
    in.wrapper = 1;
    fixture_errno = 77;
    fixture_invoke_cf(&in, &out);
    expect(out.eax == 0xffffffffu, "UNKNOWN_CHECKED_EAX");
    expect(out.cf == 1, "UNKNOWN_CHECKED_CF");
    expect(fixture_errno == 78, "UNKNOWN_CHECKED_ERRNO");
    expect(out.stack_delta == 0, "UNKNOWN_CHECKED_STACK");
    expect(unknown_calls == before + 2, "UNKNOWN_CHECKED_COUNT");
    expect(unknown_number == masked, "UNKNOWN_CHECKED_NR");
    expect(observed_alignment == 0, "UNKNOWN_CALL_ALIGNMENT");
}
int main(void) {
    printf("GUARD_CF_BEGIN\n");
    expect(sizeof(void *) == 4, "POINTER_SIZE_4");
    __fixture_bsd_table[33] = (void *) fixture_returner;
    __fixture_bsd_table[34] = (void *) fixture_observer;
    __fixture_bsd_table[599] = (void *) fixture_returner;
    known_case(33, 0, 1, 0);
    known_case(33, 0x12345678u, 1, 0);
    known_case(33 | (20u << 16), 0xfffff000u, 1, 0);
    known_case(599, 0x80000000u, 1, 0);
    known_case(33, 0xffffefffu, 1, 0);
    known_case(33, 0xfffff001u, 0, 4095);
    known_case(33, 0xffffffb2u, 0, 78);
    known_case(33, 0xfffffffeu, 0, 2);
    known_case(33, 0xffffffffu, 0, 1);
    unknown_case(8);
    unknown_case(8 | (12u << 16));
    unknown_case(598);
    /* Out-of-range values belong to candidate only, not baseline. */
    unknown_case(600);
    unknown_case(65535);
    unknown_case(0xffffffffu);
    unknown_case(600u | (53u << 16));
    printf("GUARD_CF_CHECKS=%u FAILURES=%u\n", checks, errors);
    printf("GUARD_CF_FINISHED\n");
    return errors ? 10 : 0;
}
