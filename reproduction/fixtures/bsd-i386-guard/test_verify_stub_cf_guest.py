#!/usr/bin/env python3
"""Synthetic positive and negative tests for the independent log checker."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from verify_stub_cf_guest import EXPECTED_FILES, EXPECTED_MARKERS, validate_result


class StubCfGuestLogTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'guest.stdout.log').write_text('\n'.join(EXPECTED_MARKERS) + '\n', encoding='utf-8')
        (self.root / 'guest.stderr.log').write_text('prefix initialization\n', encoding='utf-8')
        (self.root / 'stub-cf-guest').write_bytes(b'mock Mach-O bytes, not an executable')
        (self.root / 'guest.exit-code.txt').write_text('0\n', encoding='ascii')
        self.write_manifest()

    def write_manifest(self):
        lines = [f'{hashlib.sha256((self.root / name).read_bytes()).hexdigest()}  {self.root / name}'
                 for name in EXPECTED_FILES]
        (self.root / 'SHA256SUMS').write_text('\n'.join(lines) + '\n', encoding='ascii')

    def change_log(self, transform, *, refresh=True):
        p = self.root / 'guest.stdout.log'
        p.write_text(transform(p.read_text(encoding='utf-8')), encoding='utf-8')
        if refresh:
            self.write_manifest()

    def test_pass_valid_result(self):
        self.assertEqual(validate_result(self.root), [])

    def test_reject_nonzero_exit_code(self):
        (self.root / 'guest.exit-code.txt').write_text('137\n')
        self.assertTrue(validate_result(self.root))

    def test_reject_missing_begin(self):
        self.change_log(lambda s: s.replace('STUB_CF_GUEST_BEGIN\n', ''))
        self.assertTrue(validate_result(self.root))

    def test_reject_duplicate_finished(self):
        self.change_log(lambda s: s + 'STUB_CF_GUEST_FINISHED\n')
        self.assertTrue(validate_result(self.root))

    def test_reject_fail_line_despite_false_success(self):
        self.change_log(lambda s: s + 'STUB_CF_GUEST_CASE=8 FAIL raw=4294967218 eax=0 cf=0\n')
        self.assertTrue(validate_result(self.root))

    def test_reject_wrong_count(self):
        self.change_log(lambda s: s.replace('CHECKS=12', 'CHECKS=11'))
        self.assertTrue(validate_result(self.root))

    def test_reject_contradictory_guest_exit(self):
        self.change_log(lambda s: s + 'STUB_CF_GUEST_EXIT=10\n')
        self.assertTrue(validate_result(self.root))

    def test_reject_modified_log_without_new_manifest(self):
        self.change_log(lambda s: s + 'append log\n', refresh=False)
        self.assertTrue(validate_result(self.root))

    def test_reject_bad_digest(self):
        p = self.root / 'SHA256SUMS'
        p.write_text(p.read_text().replace('a', 'b', 1))
        self.assertTrue(validate_result(self.root))

    def test_reject_missing_manifest_entry(self):
        p = self.root / 'SHA256SUMS'
        p.write_text('\n'.join(p.read_text().splitlines()[:2]) + '\n')
        self.assertTrue(validate_result(self.root))

    def test_reject_duplicate_manifest_entry(self):
        p = self.root / 'SHA256SUMS'
        p.write_text(p.read_text() + p.read_text().splitlines()[0] + '\n')
        self.assertTrue(validate_result(self.root))

    def test_reject_symlink_binary(self):
        p = self.root / 'stub-cf-guest'
        p.unlink()
        p.symlink_to(self.root / 'guest.stdout.log')
        self.assertTrue(validate_result(self.root))

    def test_reject_invalid_utf8(self):
        (self.root / 'guest.stdout.log').write_bytes(b'\xff')
        self.assertTrue(validate_result(self.root))

    def test_reject_missing_stderr(self):
        (self.root / 'guest.stderr.log').unlink()
        self.assertTrue(validate_result(self.root))

    def test_reject_missing_result_directory(self):
        self.assertTrue(validate_result(self.root / 'nonexistent'))


if __name__ == '__main__':
    unittest.main()
