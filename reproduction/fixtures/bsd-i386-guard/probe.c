/* BSD i386 guard: isolated synthetic runtime fixture.
 * Uses raw syscall returns, not the obsolete B15 CF conversion.
 * No SDK headers or system syscalls are required by the probe.
 */

struct input {
    unsigned nr;
    unsigned wrapper;
    unsigned args[14];
};

struct output {
    unsigned eax;
    unsigned edx;
    unsigned cf;
    unsigned stack_delta;
};

extern void fixture_invoke(
    const struct input *,
    struct output *
);

extern void fixture_returner(void);
extern void fixture_observer(void);
extern int printf(const char *, ...);

void *__fixture_bsd_table[600];

unsigned fixture_errno;
unsigned observed_args[14];
unsigned observed_alignment;
unsigned unknown_number;
unsigned unknown_calls;

static unsigned checks;
static unsigned failures;

static void check(const char *name, int passed)
{
    ++checks;

    if (!passed)
        ++failures;

    printf("CHECK %s=%s\n",
           name, passed ? "PASS" : "FAIL");
}

static void fill(struct input *in, unsigned nr)
{
    unsigned i;

    in->nr = nr;
    in->wrapper = 0;

    for (i = 0; i < 14; ++i)
        in->args[i] = 0x12340000u + i * 0x10101u;
}

static void known(unsigned nr)
{
    struct input in;
    struct output out;
    unsigned before = unknown_calls;

    printf("CASE=KNOWN NR=%u\n", nr);

    fill(&in, nr);
    fixture_invoke(&in, &out);

    check("KNOWN_EAX", out.eax == in.args[0]);
    check("KNOWN_EDX", out.edx == in.args[1]);
    check("KNOWN_CF", out.cf == 0);
    check("KNOWN_STACK", out.stack_delta == 0);
    check("KNOWN_HANDLER",
          unknown_calls == before);
}

static void observer(void)
{
    struct input in;
    struct output out;
    unsigned i;
    int same = 1;

    printf("CASE=ARGUMENT_FORWARDING\n");

    fill(&in, 34);
    fixture_invoke(&in, &out);

    for (i = 0; i < 14; ++i)
        if (observed_args[i] != in.args[i])
            same = 0;

    check("FORWARD_14_ARGUMENTS", same);
    check("FORWARD_ALIGNMENT",
          observed_alignment == 0);
    check("FORWARD_STACK",
          out.stack_delta == 0);
}

static void unknown(unsigned nr, int baseline)
{
    struct input in;
    struct output out;
    unsigned before = unknown_calls;
    unsigned expected = nr & 0xffffu;

    printf("CASE=UNKNOWN NR=%u MASKED=%u\n",
           nr, expected);

    fill(&in, nr);
    fixture_invoke(&in, &out);

    check("UNKNOWN_HANDLER_CALLED",
          unknown_calls == before + 1);

    check("UNKNOWN_RAW_ENOSYS",
          out.eax == (unsigned)-78);

    check("UNKNOWN_RAW_CF",
          out.cf == 0);

    check("UNKNOWN_STACK",
          out.stack_delta == 0);

    if (baseline) {
        check("ORIGINAL_NUMBER_BUG_REPRODUCED",
              unknown_number != expected);
    } else {
        check("CORRECTED_NUMBER",
              unknown_number == expected);

        check("CORRECTED_CALL_ALIGNMENT",
              observed_alignment == 0);
    }
}

int main(int argc, char **argv)
{
    int baseline = argc > 1;

    (void)argv;

    printf("GUARD_RUNTIME_BEGIN MODE=%s\n",
           baseline ? "ORIGINAL" : "CANDIDATE");

    check("I386_POINTER_SIZE",
          sizeof(void *) == 4);

    __fixture_bsd_table[33] = (void *)fixture_returner;
    __fixture_bsd_table[34] = (void *)fixture_observer;
    __fixture_bsd_table[599] = (void *)fixture_returner;

    known(33);
    known(33u | (20u << 16));
    known(599);

    observer();

    unknown(8, baseline);
    unknown(8u | (12u << 16), baseline);
    unknown(598, baseline);

    if (!baseline) {
        /* Never perform these accesses on the original:
         * its dispatch table lookup is not bounds-checked.
         */
        unknown(600, 0);
        unknown(65535, 0);
        unknown(0xffffffffu, 0);
        unknown(600u | (53u << 16), 0);
    }

    printf("GUARD_CHECKS=%u GUARD_FAILURES=%u\n",
           checks, failures);
    printf("GUARD_FINISHED\n");

    return failures ? 10 : 0;
}
