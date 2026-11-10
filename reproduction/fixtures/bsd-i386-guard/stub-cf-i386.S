/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Independent Mach-O i386 assembly witness for the DARLING SYS.h sequence. */
.text
.globl _guard_stub_result_to_cf
_guard_stub_result_to_cf:
    movl 4(%esp), %eax
    cmpl $-4095, %eax
    cmc
    jnc 9f
    negl %eax
9:
    retl
