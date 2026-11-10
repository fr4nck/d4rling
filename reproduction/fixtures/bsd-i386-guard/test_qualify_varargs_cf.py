#!/usr/bin/env python3
"""Local, bounded tests of i386 variadic syscall CF patch and compilation gate.

Only fragment-level tests run here; pinned-source --xnu qualification is OPEN.
"""
from pathlib import Path
import tempfile
import subprocess
import unittest

from qualify_varargs_cf import (ABI_SHIM, BLOBS, EXCERPT, GateError, REV,
                               TARGET, REPLACE, apply_candidate, check_disassembly,
                               check_upstream_macros, compile_i386, i386_part,
                               load_pinned, qualify)

HERE=Path(__file__).resolve().parent


class SourceTests(unittest.TestCase):
    def test_distinct_pinned_blobs(self):
        self.assertEqual(len(BLOBS), 5)
        self.assertEqual(len(set(BLOBS.values())), len(BLOBS))
        self.assertEqual(len(REV), 40)

    def test_patch_single_site(self):
        self.assertEqual(EXCERPT.count(TARGET), 1)
        candidate=apply_candidate(EXCERPT)
        self.assertEqual(candidate.count('DARLING_SYSCALL_RESULT_TO_CF'), 1)
        self.assertIn(REPLACE, candidate)

    def test_surgery_preserves_unrelated_architecture(self):
        candidate=apply_candidate(EXCERPT)
        marker='#elif defined(__x86_64__)'
        self.assertEqual(EXCERPT.split(marker, 1)[1], candidate.split(marker, 1)[1])

    def test_duplicate_original_site_rejected(self):
        duplicated=EXCERPT.replace(TARGET, TARGET+'\n'+TARGET)
        with self.assertRaises(GateError):
            apply_candidate(duplicated)

    def test_already_patched_rejected(self):
        with self.assertRaises(GateError):
            apply_candidate(apply_candidate(EXCERPT))

    def test_missing_source_anchor_rejected(self):
        with self.assertRaises(GateError):
            apply_candidate(EXCERPT.replace('UNIX_SYSCALL_TRAP', 'int $0x80'))

    def test_reject_bad_architecture_markers(self):
        with self.assertRaises(GateError):
            i386_part(EXCERPT.replace('#elif defined(__x86_64__)', 'NO_X64'))

    def test_truncated_upstream_refuses_pinned_loader(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises((subprocess.CalledProcessError, GateError)):
                load_pinned(Path(temp))

    def test_wrong_macro_contract_rejected(self):
        fake={k:'not real XNU' for k in BLOBS}
        with self.assertRaises(GateError):
            check_upstream_macros(fake)

    def test_negative_wrong_flags_sequence(self):
        asm='calll\t__darling_bsd_syscall\n\tcmpl\t$0, %eax\n\tjae\t0x20\n'
        with self.assertRaises(GateError):
            check_disassembly('calll\t__darling_bsd_syscall\n', asm)


class I386ObjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=tempfile.TemporaryDirectory(prefix='d4rling-syscall-cf-tests-')
        cls.dir=Path(cls.t.name)
        (cls.dir/'abi-shim.h').write_text(ABI_SHIM)
        cls.original,cls.original_disasm=compile_i386(EXCERPT,cls.dir,'old')
        cls.candidate,cls.candidate_disasm=compile_i386(apply_candidate(EXCERPT),cls.dir,'new')

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,'t'):
            cls.t.cleanup()

    def test_objects_are_macho_i386(self):
        for data in (self.original,self.candidate):
            self.assertEqual(data[:4],b'\xce\xfa\xed\xfe')
            self.assertEqual(data[4:8],(7).to_bytes(4,'little'))

    def test_changed_binary(self):
        self.assertNotEqual(self.original,self.candidate)

    def test_expected_conversion_sequence(self):
        check_disassembly(self.original_disasm,self.candidate_disasm)

    def test_cerror_branch_still_present(self):
        self.assertIn('jmp\ttramp_cerror',self.original_disasm)
        self.assertIn('jmp\ttramp_cerror',self.candidate_disasm)

    def test_dispatcher_called_once(self):
        for asm in (self.original_disasm,self.candidate_disasm):
            self.assertEqual(asm.count('calll\t__darling_bsd_syscall'),1)

    def test_pushed_return_address_preserved(self):
        for asm in (self.original_disasm,self.candidate_disasm):
            self.assertIn('popl\t%ecx',asm)
            self.assertIn('popl\t%eax',asm)
            self.assertIn('pushl\t%ecx',asm)
            self.assertIn('pushl\t%edx',asm)

    def test_non_darling_object_unchanged(self):
        old,_=compile_i386(EXCERPT,self.dir,'old-normal',('-DGUARD_NON_DARLING',))
        patched,_=compile_i386(apply_candidate(EXCERPT),self.dir,'new-normal',('-DGUARD_NON_DARLING',))
        self.assertEqual(old,patched)

    def test_selftest_entrypoint(self):
        qualify({'gen/bsdsyscalls/___syscall.S':EXCERPT})


class PatchFormatTests(unittest.TestCase):
    def test_patch_touches_only_two_xnu_sources(self):
        patch=(HERE/'bsd-i386-syscall-varargs-cf-ba34c8ac.patch').read_text()
        self.assertEqual(patch.count('diff --git '),2)
        self.assertEqual(patch.count('+\tDARLING_SYSCALL_RESULT_TO_CF'),2)
        self.assertNotIn('bsd_syscall.S',patch)

    def test_patch_applies_in_private_worktree(self):
        patch=HERE/'bsd-i386-syscall-varargs-cf-ba34c8ac.patch'
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for p in ('gen/bsdsyscalls/___syscall.S','libsyscall/custom/__syscall.S'):
                f=root/p
                f.parent.mkdir(parents=True,exist_ok=True)
                f.write_text(EXCERPT)
            subprocess.run(['git','apply','--check',str(patch)],cwd=root,check=True)
            subprocess.run(['git','apply',str(patch)],cwd=root,check=True)
            for p in ('gen/bsdsyscalls/___syscall.S','libsyscall/custom/__syscall.S'):
                self.assertEqual((root/p).read_text(),apply_candidate(EXCERPT))


if __name__=='__main__':
    unittest.main()
