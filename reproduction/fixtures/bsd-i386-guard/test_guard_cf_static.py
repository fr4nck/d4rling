#!/usr/bin/env python3
"""Compile-only Darwin i386 qualification of the coupled BSD/CF fixture.

No SDK, guest, link editor, 5700X, or i386 executable is required.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


class IntegratedGuardStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='guard-cf-obj-')
        cls.out = Path(cls.temp.name)
        for command in ('clang', 'llvm-objdump', 'file'):
            if not shutil.which(command):
                raise unittest.SkipTest(f'{command} unavailable')
        base = ['clang', '-target', 'i386-apple-macosx10.9']
        subprocess.run(base + ['-c', str(HERE / 'fixture-cf-i386.S'),
                                '-o', str(cls.out / 'positive.o')], check=True)
        subprocess.run(base + ['-DGUARD_CF_MUTANT_NO_CMC', '-c',
                               str(HERE / 'fixture-cf-i386.S'),
                               '-o', str(cls.out / 'mutant.o')], check=True)
        subprocess.run(base + ['-nostdinc', '-fno-builtin', '-fno-stack-protector',
                               '-O1', '-Wall', '-Wextra', '-Werror', '-c',
                               str(HERE / 'probe-cf.c'), '-o', str(cls.out / 'probe.o')],
                       check=True)
        cls.asm = {}
        for name in ('positive', 'mutant'):
            cls.asm[name] = subprocess.check_output(
                ['llvm-objdump', '--macho', '--disassemble', str(cls.out / f'{name}.o')],
                text=True)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'temp'):
            cls.temp.cleanup()

    def test_three_macho_i386_objects(self):
        for name in ('positive.o', 'mutant.o', 'probe.o'):
            data = subprocess.check_output(['file', '-b', str(self.out / name)], text=True)
            self.assertIn('Mach-O i386 object', data)

    def test_dispatcher_called_in_both_raw_and_checked(self):
        self.assertEqual(self.asm['positive'].count('calll\t__fixture_bsd_syscall'), 2)
        self.assertEqual(self.asm['mutant'].count('calll\t__fixture_bsd_syscall'), 2)

    def test_positive_has_exact_conversion(self):
        section = self.asm['positive'].split('checked_stub_cf:', 1)[1]
        names = re.findall(r'\t(cmpl|cmc|jae|negl)\b', section)
        self.assertEqual(names, ['cmpl', 'cmc', 'jae', 'negl'])

    def test_mutant_removes_only_cmc_from_conversion(self):
        mutant = self.asm['mutant'].split('checked_stub_cf:', 1)[1]
        names = re.findall(r'\t(cmpl|cmc|jae|negl)\b', mutant)
        self.assertEqual(names, ['cmpl', 'jae', 'negl'])
        self.assertNotEqual((self.out / 'positive.o').read_bytes(),
                            (self.out / 'mutant.o').read_bytes())

    def test_raw_stub_has_no_conversion(self):
        section = self.asm['positive'].split('raw_stub_cf:', 1)[1].split('checked_stub_cf:', 1)[0]
        self.assertIn('calll\t__fixture_bsd_syscall', section)
        self.assertNotIn('cmc', section)
        self.assertNotIn('negl', section)

    def test_flags_captured_before_arithmetic(self):
        section = self.asm['positive'].split('raw_stub_cf:', 1)[0]
        self.assertRegex(section, r'pushfl\n[^\n]*popl\t%ecx')

    def test_prologue_preserves_three_callee_saved_registers(self):
        section = self.asm['positive'].split('_fixture_invoke_cf:', 1)[1]
        for register in ('%ebx', '%esi', '%edi'):
            self.assertRegex(section, r'pushl\t' + re.escape(register))
            self.assertRegex(section, r'popl\t' + re.escape(register))


if __name__ == '__main__':
    unittest.main()
