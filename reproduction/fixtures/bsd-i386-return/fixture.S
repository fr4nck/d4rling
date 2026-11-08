/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Tests call the real compiled dispatcher through the two-return-address
 * layout used by Darwin's syscall stubs. No arithmetic may precede capture
 * of the returned flags. All state for concurrent cases is passed on stack. */
.text
.globl _fixture_invoke
_fixture_invoke:
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
    cmpl $0, 4(%esi)
    movl (%esi), %eax
    jne 1f
    calll raw_stub
    jmp 2f
1:
    calll errno_stub
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
raw_stub:
    calll __fixture_bsd_syscall
    retl
errno_stub:
    calll __fixture_bsd_syscall
    jnb 3f
    movl %eax, _fixture_errno
    movl $-1, %eax
    movl $-1, %edx
3:
    retl

.globl _fixture_observer
_fixture_observer:
    .set slot, 0
    .rept 14
    movl 4+slot(%esp), %eax
    movl %eax, _observed_args+slot
    .set slot, slot+4
    .endr
    leal 4(%esp), %eax
    andl $15, %eax
    movl %eax, _observed_alignment
.globl _fixture_returner
_fixture_returner:
    movl 4(%esp), %eax
    movl 8(%esp), %edx
    cmpl $0, 12(%esp)
    je 4f
    stc
    retl
4:
    clc
    retl

.globl ___fixture_unknown_syscall
___fixture_unknown_syscall:
    movl 4(%esp), %eax
    movl %eax, _unknown_number
    leal 4(%esp), %eax
    andl $15, %eax
    movl %eax, _observed_alignment
    incl _unknown_calls
    movl $-78, %eax /* Darwin ENOSYS; this is a 32-bit C return. */
    movl $0x5a5a5a5a, %edx
    clc
    retl
