/* SPDX-License-Identifier: GPL-3.0-or-later
 * QT-B11E diagnostic: does CarbonCore's MemError() report the error set by
 * the previous Memory Manager call, and does reading/writing thread-local
 * storage allocate memory, in the Darling guest (i386 and x86_64)?
 * Compares CarbonCore (C++ thread_local g_memoryError) with a C11
 * _Thread_local in this executable.
 */
#include <CarbonCore/MacMemory.h>
#include <malloc/malloc.h>
#include <stdio.h>
#include <stdlib.h>

static _Thread_local int local_tls;
static unsigned failures;

static size_t in_use(void)
{
    malloc_statistics_t st;
    malloc_zone_statistics(NULL, &st);
    return st.size_in_use;
}

static void expect(const char *what, long got, long want)
{
    if (got != want)
        ++failures;
    printf("TLS %s got=%ld want=%ld %s\n", what, got, want, got == want ? "PASS" : "FAIL");
}

int main(void)
{
    char *block = malloc(16), **foreign = &block;
    Handle h;
    size_t a, b;
    int i;
    volatile int sink = 0;

    printf("TLS_ABI pointer_bits=%zu\n", sizeof(void *) * 8);
    h = NewHandle(4);
    expect("newhandle_noErr", MemError(), 0);
    GetHandleSize(NULL);
    expect("gethandlesize_null_nilHandleErr", MemError(), -109);
    GetHandleSize((Handle)foreign);
    expect("gethandlesize_foreign_memWZErr", MemError(), -111);
    expect("memerror_stable_second_read", MemError(), -111);
    SetHandleSize(h, -1);
    expect("sethandlesize_negative_memFullErr", MemError(), -108);
    DisposeHandle(h);
    expect("disposehandle_noErr", MemError(), 0);

    local_tls = 1234;
    expect("c11_thread_local_roundtrip", local_tls, 1234);

    a = in_use();
    for (i = 0; i < 1000; ++i)
        sink += local_tls;
    b = in_use();
    expect("c11_thread_local_1000_reads_heap_delta", (long)(b - a), 0);
    a = in_use();
    for (i = 0; i < 1000; ++i)
        sink += MemError();
    b = in_use();
    expect("memerror_1000_reads_heap_delta", (long)(b - a), 0);
    a = in_use();
    for (i = 0; i < 1000; ++i)
        GetHandleSize(NULL);
    b = in_use();
    expect("memerror_1000_writes_heap_delta", (long)(b - a), 0);
    (void)sink;
    free(block);
    printf("TLS_SUMMARY failures=%u\n", failures);
    return failures > 100 ? 100 : (int)failures;
}
