#!/usr/bin/env python3
"""Offline tests of the Machdep i386 guard and the LDT errno/CF contract."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

from qualify_machdep_i386 import (
    ABI, CUSTOM, GEN, HEADER, LDT_FIXTURE, MACH, MACH_FIXTURE,
    PATCH, PINNED, TABLE, GateError, qualify, read_pinned, validate_source
)


def sample(full=False):
    data = {MACH: MACH_FIXTURE, GEN: LDT_FIXTURE, CUSTOM: LDT_FIXTURE}
    if full:
        data[HEADER] = 'extern void* __machdep_syscall_table[10];\n'
        data[TABLE] = 'void* __machdep_syscall_table[10] = {[3] = sys_thread_set_tsd_base};\n'
    return data


class SourceContract(unittest.TestCase):
    def setUp(self):
        self.data=sample()

    def test_original_is_detected(self):
        validate_source(self.data, full=False)

    def test_pins_are_distinct_except_custom(self):
        self.assertEqual(PINNED[GEN], PINNED[CUSTOM])
        self.assertNotEqual(PINNED[MACH], PINNED[GEN])
        self.assertEqual(len(PINNED), 5)

    def test_missing_dispatch_lookup_detected(self):
        self.data[MACH]=self.data[MACH].replace('(%ecx,%eax,4)', '(%ecx,%edx,4)')
        with self.assertRaises(GateError): validate_source(self.data, full=False)

    def test_missing_get_ldt_detected(self):
        self.data[GEN]=self.data[GEN].replace('_i386_get_ldt:', '_wrong_get_ldt:')
        with self.assertRaises(GateError): validate_source(self.data, full=False)

    def test_missing_set_ldt_detected(self):
        self.data[CUSTOM]=self.data[CUSTOM].replace('_i386_set_ldt:', '_wrong_set_ldt:')
        with self.assertRaises(GateError): validate_source(self.data, full=False)

    def test_changed_ldt_syscall_nr_detected(self):
        self.data[GEN]=self.data[GEN].replace('movl    $6,%eax', 'movl    $7,%eax')
        with self.assertRaises(GateError): validate_source(self.data, full=False)

    def test_missing_ldt_cf_branch_detected(self):
        self.data[GEN]=self.data[GEN].replace('jnb\t\t2f', 'jmp\t\t2f')
        with self.assertRaises(GateError): validate_source(self.data, full=False)

    def test_full_header_table_10_accepted(self):
        validate_source(sample(full=True),full=True)

    def test_full_header_wrong_size_rejected(self):
        s=sample(full=True)
        s[HEADER]=s[HEADER].replace('[10]','[11]')
        with self.assertRaises(GateError): validate_source(s,full=True)

    def test_full_definition_wrong_size_rejected(self):
        s=sample(full=True)
        s[TABLE]=s[TABLE].replace('[10]','[9]')
        with self.assertRaises(GateError): validate_source(s,full=True)

    def test_full_slot_three_wrong_rejected(self):
        s=sample(full=True)
        s[TABLE]=s[TABLE].replace('[3]', '[4]')
        with self.assertRaises(GateError): validate_source(s,full=True)

    def test_full_copies_diverged_rejected(self):
        s=sample(full=True)
        s[CUSTOM]=s[CUSTOM].replace('tramp_cerror','not_cerror')
        with self.assertRaises(GateError): validate_source(s,full=True)

    def test_pinned_loader_rejects_empty_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises((GateError,subprocess.CalledProcessError)):
                read_pinned(Path(tmp))

    def test_shim_defines_only_mock_cf(self):
        self.assertIn('DARLING_SYSCALL_RESULT_TO_CF', ABI)
        self.assertIn('cmc', ABI)
        self.assertIn('jnc 9f', ABI)


class PatchAndAssembly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=qualify(sample(),full=False)

    def test_patch_is_bounded(self):
        self.assertEqual(self.result['patch'],'PASS')
        self.assertEqual(self.result['source'],'SELFTEST_FRAGMENTS')

    def test_i386_object_assembled(self):
        self.assertEqual(self.result['macho_i386'],'PASS')

    def test_bounds_guard_before_dereference(self):
        self.assertEqual(self.result['machdep_guard'],'PASS')

    def test_x86_64_objects_identical(self):
        self.assertEqual(self.result['x86_64_unchanged'],'PASS')

    def test_ldt_darling_is_changed(self):
        self.assertEqual(self.result['ldt_darling_changed'],'PASS')

    def test_ldt_nondarling_identical(self):
        self.assertEqual(self.result['ldt_nondarling_unchanged'],'PASS')

    def test_patch_three_files_only(self):
        data=PATCH.read_text()
        self.assertEqual(data.count('diff --git '),3)
        self.assertIn('machdep_syscall.S',data)
        self.assertIn('gen/bsdsyscalls/custom.S',data)
        self.assertIn('libsyscall/custom/custom.S',data)
        self.assertNotIn('machdep_syscall_table.c',data)

    def test_two_ldt_pairs_modified(self):
        data=PATCH.read_text()
        self.assertEqual(data.count('+\tDARLING_SYSCALL_RESULT_TO_CF'),4)
        self.assertEqual(data.count('+#ifdef DARLING'),4)

    def test_explicit_bounds_index_in_patch(self):
        data=PATCH.read_text()
        self.assertIn('+\tcmpl\t$10, %eax',data)
        self.assertIn('+\tjae\t\t.no_sys',data)
        self.assertIn('+\tpushl\t%edx',data)
        self.assertIn('-\tpushl\t%ecx',data)

    def test_local_error_code_unchanged_for_machdep_tsd(self):
        data=PATCH.read_text()
        self.assertNotIn('thread_set_tsd_base',data)


if __name__=='__main__': unittest.main()
