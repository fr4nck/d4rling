#!/usr/bin/env python3
"""SH11: safe ld64 fingerprint and verified-dylib handoff; no guest execution.

Only SH09/SH10 synthetic FFT-shaped objects are used by this test class.
Copyright (C) 2026 D4rling contributors; GPL-3.0-or-later.
"""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import darwin_archive_gate as gate
from test_i386_link_gate import SYNTH


@unittest.skipUnless(shutil.which('clang') and shutil.which('llvm-ar') and
                     shutil.which('llvm-objdump'), 'Required installed host tools absent')
class SH11LinkDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='sh11-check-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.folder = Path(cls.tmp.name)
        s = cls.folder / 'synthetic.c'
        s.write_text(SYNTH, encoding='ascii')
        cls.obj = cls.folder / 'synthetic.o'
        subprocess.run(['clang', '-target', 'i386-apple-darwin9', '-nostdinc',
                        '-fno-stack-protector', '-std=c99', '-O1', '-c', str(s),
                        '-o', str(cls.obj)], check=True, capture_output=True, timeout=25)
        cls.pin = hashlib.sha256(cls.obj.read_bytes()).hexdigest()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sh11-run-')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.linker = self.work / 'ld64'
        self.target = self.work / 'result.dylib'

    def fake(self, *, rc=1, touch_output=False, marker=False):
        text = '#!/bin/sh\n'
        if marker:
            text += 'printf invoked > "' + str(self.work / 'was-called') + '"\n'
        if touch_output:
            text += ('while [ "$#" -gt 0 ]; do\n'
                     ' if [ "$1" = "-o" ]; then shift; printf BAD > "$1"; exit 0; fi\n'
                     ' shift\ndone\nexit 1\n')
        else:
            text += 'exit ' + str(rc) + '\n'
        self.linker.write_text(text, encoding='ascii')
        self.linker.chmod(0o700)
        return hashlib.sha256(self.linker.read_bytes()).hexdigest()

    def call(self, *arguments):
        with contextlib.redirect_stdout(io.StringIO()) as stream:
            code = gate.main(['--object', str(self.obj),
                              '--expected-sha256', self.pin, *arguments])
        return code, json.loads(stream.getvalue())

    def test_absent_linker_cannot_save_dylib(self):
        code, out = self.call('--linked-output', str(self.target))
        self.assertEqual((code, out['status']), (3, 'INCONCLUSIVE'))
        self.assertFalse(self.target.exists())

    def test_pin_without_linker_is_inconclusive(self):
        code, out = self.call('--ld64-sha256', 'a'*64)
        self.assertEqual((code, out['status']), (3, 'INCONCLUSIVE'))

    def test_bad_pin_format_rejected_before_linker_is_run(self):
        self.fake(marker=True)
        code, out = self.call('--ld64', str(self.linker), '--ld64-sha256', 'broken',
                              '--linked-output', str(self.target))
        self.assertEqual((code, out['status']), (3, 'INCONCLUSIVE'))
        self.assertFalse((self.work / 'was-called').exists())
        self.assertFalse(self.target.exists())

    def test_wrong_linker_hash_refuses_execution(self):
        self.fake(marker=True)
        code, out = self.call('--ld64', str(self.linker), '--ld64-sha256', '0'*64,
                              '--linked-output', str(self.target))
        self.assertEqual((code, out['status']), (3, 'INCONCLUSIVE'))
        self.assertIn('SHA-256', out['error'])
        self.assertFalse((self.work / 'was-called').exists())
        self.assertFalse(self.target.exists())

    def test_linker_sha_recorded_even_on_failure(self):
        pin = self.fake(marker=True)
        code, out = self.call('--ld64', str(self.linker), '--ld64-sha256', pin,
                              '--linked-output', str(self.target))
        self.assertEqual((code, out['status']), (3, 'LINK_TOOLCHAIN_BLOCKED'))
        self.assertEqual(out['link_attempt']['linker_sha256'], pin)
        self.assertEqual(out['link_attempt']['linker_basename'], 'ld64')
        self.assertTrue((self.work / 'was-called').exists())
        self.assertFalse(self.target.exists())

    def test_unpinned_linker_failure_cannot_create_output(self):
        self.fake()
        code, out = self.call('--ld64', str(self.linker), '--linked-output', str(self.target))
        self.assertEqual((code, out['status']), (3, 'LINK_TOOLCHAIN_BLOCKED'))
        self.assertFalse(self.target.exists())

    def test_success_without_dylib_not_saved(self):
        self.fake(rc=0)
        code, out = self.call('--ld64', str(self.linker), '--linked-output', str(self.target))
        self.assertEqual((code, out['status']), (2, 'TARGET_CONTRACT_FAIL'))
        self.assertFalse(self.target.exists())

    def test_invalid_fake_dylib_not_saved(self):
        self.fake(touch_output=True)
        code, out = self.call('--ld64', str(self.linker), '--linked-output', str(self.target))
        self.assertEqual((code, out['status']), (2, 'TARGET_CONTRACT_FAIL'))
        self.assertFalse(self.target.exists())

    def test_existing_output_not_touched_after_link_failure(self):
        self.fake()
        self.target.write_bytes(b'PROTECTED')
        code, out = self.call('--ld64', str(self.linker), '--linked-output', str(self.target))
        self.assertEqual((code, out['status']), (3, 'LINK_TOOLCHAIN_BLOCKED'))
        self.assertEqual(self.target.read_bytes(), b'PROTECTED')

    def test_output_symlink_target_not_modified_after_failure(self):
        self.fake()
        protected = self.work / 'protected'
        protected.write_bytes(b'PROTECTED')
        self.target.symlink_to(protected)
        code, out = self.call('--ld64', str(self.linker), '--linked-output', str(self.target))
        self.assertEqual((code, out['status']), (3, 'LINK_TOOLCHAIN_BLOCKED'))
        self.assertEqual(protected.read_bytes(), b'PROTECTED')

    def test_same_archive_and_dylib_destination_rejected(self):
        self.fake()
        code, out = self.call('--ld64', str(self.linker), '--output', str(self.target),
                              '--linked-output', str(self.target))
        self.assertEqual((code, out['status']), (3, 'INCONCLUSIVE'))
        self.assertFalse(self.target.exists())

    def test_no_fake_success_for_real_lld(self):
        if not shutil.which('ld64.lld'):
            self.skipTest('ld64.lld absent')
        code, out = self.call('--ld64', 'ld64.lld', '--linked-output', str(self.target))
        self.assertEqual((code, out['status']), (3, 'LINK_TOOLCHAIN_BLOCKED'))
        self.assertIn('unsupported -arch i386', out['link_attempt']['linker_stderr_tail'])
        self.assertFalse(self.target.exists())

    def test_copy_mechanism_with_synthetic_verifier_only(self):
        # Mock is deliberately LIMITED to delivery I/O and is never runtime evidence.
        self.fake(touch_output=True)
        synthetic = hashlib.sha256(b'BAD').hexdigest()
        with mock.patch.object(gate, 'verify_linked', return_value={'sha256': synthetic}):
            code, out = self.call('--ld64', str(self.linker), '--linked-output', str(self.target))
        self.assertEqual((code, out['status']), (0, 'LINK_STRUCTURE_PASS'))
        self.assertEqual(out['link_attempt']['saved_dylib'], str(self.target))
        self.assertEqual(self.target.read_bytes(), b'BAD')

    def test_synthetic_verified_candidate_refuses_existing_destination(self):
        self.fake(touch_output=True)
        self.target.write_bytes(b'PROTECTED')
        synthetic = hashlib.sha256(b'BAD').hexdigest()
        with mock.patch.object(gate, 'verify_linked', return_value={'sha256': synthetic}):
            code, out = self.call('--ld64', str(self.linker), '--linked-output', str(self.target))
        self.assertEqual((code, out['status']), (3, 'INCONCLUSIVE'))
        self.assertEqual(self.target.read_bytes(), b'PROTECTED')

    def test_synthetic_verified_candidate_refuses_symlink_destination(self):
        self.fake(touch_output=True)
        protected = self.work / 'protected'
        protected.write_bytes(b'PROTECTED')
        self.target.symlink_to(protected)
        synthetic = hashlib.sha256(b'BAD').hexdigest()
        with mock.patch.object(gate, 'verify_linked', return_value={'sha256': synthetic}):
            code, out = self.call('--ld64', str(self.linker), '--linked-output', str(self.target))
        self.assertEqual((code, out['status']), (3, 'INCONCLUSIVE'))
        self.assertEqual(protected.read_bytes(), b'PROTECTED')

    def test_wrong_verified_digest_rejected_before_creating_file(self):
        self.fake(touch_output=True)
        with mock.patch.object(gate, 'verify_linked', return_value={'sha256': '0'*64}):
            code, out = self.call('--ld64', str(self.linker), '--linked-output', str(self.target))
        self.assertEqual((code, out['status']), (2, 'TARGET_CONTRACT_FAIL'))
        self.assertFalse(self.target.exists())

    def test_explicit_link_failure_does_not_touch_input_object(self):
        self.fake()
        before = self.obj.read_bytes()
        code, out = self.call('--ld64', str(self.linker), '--linked-output', str(self.target))
        self.assertEqual(code, 3)
        self.assertEqual(before, self.obj.read_bytes())


if __name__ == '__main__':
    unittest.main()
