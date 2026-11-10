/* SPDX-License-Identifier: GPL-3.0-or-later */
/* i386 Mach-O: two-return-address fixture call for real BSD dispatch plus
 * syscall stub mirror (raw -> CF + positive errno -> mock cerror).
 * This does not invoke Apple's cerror/TLS entry point.
 */
.text
.globl _fixture_invoke_cf
_fixture_invoke_cf:
    pushl %ebp
    movl %esp, %ebp
    pushl %ebx
    pushl %esi
    pushl %edi
    subl $76, %esp
    movl 8(%ebp), %esi
    movl 12(%ebp), %edi
    .set slot, 0
    .rept 14
    movl 8+slot(%esi), %eax
    movl %eax, slot(%esp)
    .set slot, slot+4
    .endr
    movl %esp, %ebx
    movl (%esi), %eax
    cmpl $0, 4(%esi)
    jne 1f
    calll raw_stub_cf
    jmp 2f
1:
    calll checked_stub_cf
2:
    pushfl
    popl %ecx
    movl %eax, (%edi)
    movl %edx, 4(%edi)
    andl $1, %ecx
    movl %ecx, 8(%edi)
    movl %esp, %eax
    subl %ebx, %eax
    movl %eax, 12(%edi)
    addl $76, %esp
    popl %edi
    popl %esi
    popl %ebx
    popl %ebp
    retl
raw_stub_cf:
    calll __fixture_bsd_syscall
    retl
checked_stub_cf:
    calll __fixture_bsd_syscall
    /* Mirror of Darwin i386 SYS.h after XNU #49: -errno -> CF/EAX. */
    cmpl $-4095, %eax
#ifndef GUARD_CF_MUTANT_NO_CMC
    cmc
#endif
    jnc 9f
    negl %eax
    /* Mock only: real Darwin uses tramp_cerror and thread-local errno. */
    movl %eax, _fixture_errno
    movl $-1, %eax
9:
    retl
