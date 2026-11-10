/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Record EAX and CF before any caller-side arithmetic can alter flags. */
.text
.globl _guard_stub_capture
_guard_stub_capture:
    pushl %ebp
    movl %esp, %ebp
    pushl 8(%ebp)
    calll _guard_stub_result_to_cf
    pushfl
    popl %edx
    addl $4, %esp
    movl 12(%ebp), %ecx
    movl %eax, (%ecx)
    andl $1, %edx
    movl %edx, 4(%ecx)
    popl %ebp
    retl
