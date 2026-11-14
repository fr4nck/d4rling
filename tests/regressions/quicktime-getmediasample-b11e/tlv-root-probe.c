/* SPDX-License-Identifier: GPL-3.0-or-later
 * QT-B11E diagnostic (Darwin i386 under Darling only): where does the TLV
 * fast path look for the per-thread block, and where was it stored?
 *
 * Locates CarbonCore's own TLV descriptor for g_memoryError (the one MemError
 * calls through; its unslid address is passed as argv[1], read from the
 * disassembly of _MemError), then after GetHandleSize(NULL) (which stores
 * nilHandleErr = -109) compares the two candidate TSD slots:
 *   %fs:key*4  - Darwin TSD on Darling i386 (libsyscall os/tsd.h, DARLING)
 *   %gs:key*4  - what dyld's i386 tlv_get_addr reads (threadLocalHelpers.S)
 */
#include <CarbonCore/MacMemory.h>
#include <dlfcn.h>
#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct probe_tlv_descriptor { void *(*thunk)(struct probe_tlv_descriptor *); unsigned long key; unsigned long offset; };

static uintptr_t read_fs(unsigned long key)
{
    uintptr_t v;
    __asm__ volatile("movl %%fs:(,%1,4), %0" : "=r"(v) : "r"(key));
    return v;
}
static uintptr_t read_gs(unsigned long key)
{
    uintptr_t v;
    __asm__ volatile("movl %%gs:(,%1,4), %0" : "=r"(v) : "r"(key));
    return v;
}

int main(int argc, char **argv)
{
    Dl_info mi, ti;
    struct probe_tlv_descriptor *d;
    uintptr_t fs1, gs1, fs2;
    unsigned long desc_vm;
    int failures = 0;

    if (argc != 2)
        return 2;
    desc_vm = strtoul(argv[1], NULL, 0);
    if (!dladdr((const void *)MemError, &mi))
        return 3;
    d = (struct probe_tlv_descriptor *)((char *)mi.dli_fbase + desc_vm); /* dylib __TEXT vmaddr 0 */
    printf("ROOT carboncore=%s base=%p descriptor=%p\n", mi.dli_fname, mi.dli_fbase, (void *)d);
    GetHandleSize(NULL);            /* stores nilHandleErr through the descriptor */
    printf("ROOT descriptor thunk=%p key=%lu offset=%lu\n", (void *)d->thunk, d->key, d->offset);
    if (dladdr((const void *)d->thunk, &ti))
        printf("ROOT thunk_symbol=%s image=%s\n", ti.dli_sname ? ti.dli_sname : "?", ti.dli_fname);
    fs1 = read_fs(d->key);
    gs1 = read_gs(d->key);
    printf("ROOT after_store fs_slot=0x%08lx gs_slot=0x%08lx\n", (unsigned long)fs1, (unsigned long)gs1);
    if (fs1)
        printf("ROOT fs_block_value=%d (stored nilHandleErr=-109)\n", *(int16_t *)(fs1 + d->offset));
    printf("ROOT memerror_reports=%d\n", MemError());
    fs2 = read_fs(d->key);
    printf("ROOT after_memerror fs_slot=0x%08lx changed=%d\n", (unsigned long)fs2, fs2 != fs1);
    /* Expected under the hypothesis: the stored value lives in a block
     * registered in the %fs (Darwin) slot, the %gs slot read by the fast path
     * is 0, and every access replaces the %fs block with a new zeroed one. */
    failures += !(fs1 && *(int16_t *)(fs1 + d->offset) == -109);
    failures += !(gs1 == 0);
    failures += !(MemError() == 0);
    failures += !(fs2 != fs1);
    printf("ROOT_HYPOTHESIS %s (gs fast path misses the Darwin TSD slot)\n", failures ? "REJECTED" : "CONFIRMED");
    return failures;
}
