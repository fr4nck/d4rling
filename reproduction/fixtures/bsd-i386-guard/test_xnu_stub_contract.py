#!/usr/bin/env python3
"""Mutation tests for the pinned authentic XNU/i386 source contract."""
from __future__ import annotations

import unittest
from xnu_stub_contract import source_contract, PINNED, ordered, section


def valid_sources() -> dict[str, str]:
    header = '''#include <sys/syscall.h>
#if defined(__i386__)
#ifdef DARLING
#define DARLING_SYSCALL_RESULT_TO_CF \\
  cmpl\t$-4095, %eax ;\\
  cmc ;\\
  jnc 9f ;\\
  negl %eax ;\\
  9:
#define UNIX_SYSCALL_SYSENTER call __darling_bsd_syscall ; DARLING_SYSCALL_RESULT_TO_CF
#define UNIX_SYSCALL_INT_TRAP UNIX_SYSCALL_TRAP ; DARLING_SYSCALL_RESULT_TO_CF
#define ULOCK_RAW_SYSCALL(name) movl $SYS_##name, %eax ; call __darling_bsd_syscall
#define __SYSCALL_NOERROR(pseudo, name, nargs) LEAF(pseudo,0) ; movl $SYS_##name, %eax ; call\t__darling_bsd_syscall ; ret
#endif
#define ULOCK_SYSCALL(pseudo,name,nargs,cerror) testl $ULF_NO_ERRNO_BIT,4(%esp) ; ULOCK_RAW_SYSCALL(name) ; UNIX_SYSCALL_NONAME(name, nargs, cerror)
#elif defined(__x86_64__)
... omitted ...
'''
    sw = '''#if defined(__i386__)
#ifndef DARLING
#define UNIX_SYSCALL_TRAP \\
 int $(UNIX_INT)
#else // DARLING
#define UNIX_SYSCALL_TRAP \\
 call __darling_bsd_syscall
#define MACHDEP_SYSCALL_TRAP \\
 call __darling_machdep_syscall
#endif
#endif
'''
    lseek = '''#elif defined(__i386__)
#ifdef DARLING
LEAF(___lseek, 0)
 movl $SYS_lseek, %eax
 call\t__darling_bsd_syscall
 cmpl\t$-1, %edx
 jne\t2f
 cmpl\t$-4095, %eax
 jb\t2f
 negl\t%eax
 BRANCH_EXTERN(tramp_cerror)
2:
 ret
#else
__SYSCALL_INT(___lseek, lseek, 3)
#endif
#elif defined(__arm__)
... omitted ...
'''
    result = {
        'gen/bsdsyscalls/SYS.h': header,
        'libsyscall/custom/SYS.h': header,
        'osfmk/mach/i386/syscall_sw.h': sw,
        'gen/bsdsyscalls/___lseek.S': lseek,
        'libsyscall/custom/__lseek.S': lseek,
        'gen/bsdsyscalls/___sigreturn.S': '#elif defined(__i386__)\n__SYSCALL_INT(___sigreturn, sigreturn, 3)\n#elif defined(__arm__)\n',
        'libsyscall/custom/__sigaltstack.S': '#elif defined(__i386__)\n__SYSCALL_INT(___sigaltstack, sigaltstack, 3)\n#elif defined(__arm__)\n',
    }
    assert set(result) == set(PINNED)
    return result


class SourceContractTests(unittest.TestCase):
    def setUp(self):
        self.src = valid_sources()

    def mutate(self, path: str, before: str, after: str):
        self.assertIn(before, self.src[path])
        self.src[path] = self.src[path].replace(before, after, 1)
        self.assertTrue(source_contract(self.src))

    def test_baseline(self):
        self.assertEqual(source_contract(self.src), [])

    def test_missing_file(self):
        del self.src['gen/bsdsyscalls/SYS.h']
        self.assertTrue(source_contract(self.src))

    def test_drift_between_headers(self):
        self.mutate('libsyscall/custom/SYS.h', 'cmc', 'nop')

    def test_reject_missing_cmc(self):
        self.mutate('gen/bsdsyscalls/SYS.h', 'cmc', 'nop')

    def test_reject_changed_errno_threshold(self):
        self.mutate('gen/bsdsyscalls/SYS.h', '-4095', '-4096')

    def test_reject_sysenter_bypassing_darling(self):
        self.mutate('gen/bsdsyscalls/SYS.h',
                    'UNIX_SYSCALL_SYSENTER call __darling_bsd_syscall',
                    'UNIX_SYSCALL_SYSENTER int $0x80')

    def test_reject_int_stubs_missing_cf(self):
        self.mutate('gen/bsdsyscalls/SYS.h',
                    'UNIX_SYSCALL_TRAP ; DARLING_SYSCALL_RESULT_TO_CF',
                    'UNIX_SYSCALL_TRAP')

    def test_reject_host_linux_int_from_trap_macro(self):
        self.mutate('osfmk/mach/i386/syscall_sw.h',
                    'call __darling_bsd_syscall', 'int $(UNIX_INT)')

    def test_reject_missing_machdep_call(self):
        self.mutate('osfmk/mach/i386/syscall_sw.h',
                    'call __darling_machdep_syscall', 'int $(MACHDEP_INT)')

    def test_reject_ulock_raw_conversion(self):
        self.mutate('gen/bsdsyscalls/SYS.h',
                    '#define ULOCK_RAW_SYSCALL(name) movl $SYS_##name, %eax ; call __darling_bsd_syscall',
                    '#define ULOCK_RAW_SYSCALL(name) movl $SYS_##name, %eax ; int $0x80')

    def test_reject_noerror_path(self):
        self.mutate('gen/bsdsyscalls/SYS.h',
                    'call\t__darling_bsd_syscall ; ret', 'call\t__darling_bsd_syscall ; negl %eax ; ret')

    def test_reject_both_noerror_headers_converted(self):
        for path in ('gen/bsdsyscalls/SYS.h', 'libsyscall/custom/SYS.h'):
            self.src[path] = self.src[path].replace('call\t__darling_bsd_syscall ; ret',
                                                     'call\t__darling_bsd_syscall ; negl %eax ; ret')
        self.assertTrue(source_contract(self.src))

    def test_reject_both_ulock_headers_converted(self):
        for path in ('gen/bsdsyscalls/SYS.h', 'libsyscall/custom/SYS.h'):
            self.src[path] = self.src[path].replace(
                '#define ULOCK_RAW_SYSCALL(name) movl $SYS_##name, %eax ; call __darling_bsd_syscall',
                '#define ULOCK_RAW_SYSCALL(name) movl $SYS_##name, %eax ; call __darling_bsd_syscall ; cmc')
        self.assertTrue(source_contract(self.src))

    def test_reject_wrong_lseek_edx_guard(self):
        self.mutate('gen/bsdsyscalls/___lseek.S', '$-1, %edx', '$0, %edx')

    def test_reject_wrong_lseek_errno_range(self):
        self.mutate('libsyscall/custom/__lseek.S', '$-4095, %eax', '$-4096, %eax')

    def test_reject_sigreturn_int_stub_missing(self):
        self.mutate('gen/bsdsyscalls/___sigreturn.S',
                    '__SYSCALL_INT', '__SYSCALL')

    def test_reject_sigaltstack_int_stub_missing(self):
        self.mutate('libsyscall/custom/__sigaltstack.S',
                    '__SYSCALL_INT', '__SYSCALL')

    def test_reject_lseek_generated_custom_drift(self):
        self.mutate('gen/bsdsyscalls/___lseek.S', 'ret\n#else', 'nop\nret\n#else')

    def test_macro_continuation(self):
        from xnu_stub_contract import macro_definition
        snippet = '#define ULOCK_RAW_SYSCALL(name) \\\n call __darling_bsd_syscall'
        self.assertIn('__darling_bsd_syscall', macro_definition(snippet, 'ULOCK_RAW_SYSCALL'))

    def test_section_missing_marker(self):
        self.assertEqual(section('arbitrary', '#if defined(__i386__)', '#endif'), '')

    def test_ordered_rejects_out_of_order(self):
        self.assertFalse(ordered('AAA BBB', ('BBB', 'AAA')))


if __name__ == '__main__':
    unittest.main()
