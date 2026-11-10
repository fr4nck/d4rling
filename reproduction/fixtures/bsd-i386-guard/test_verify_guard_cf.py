#!/usr/bin/env python3
"""Negative controls for integration fixture's independent evidence gate."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from verify_guard_cf import COUNT, MANIFEST_ITEMS, validate


UNKNOWN = (8, 8 | (12 << 16), 598, 600, 65535, 0xffffffff, 600 | (53 << 16))
KNOWN = ((33, 0), (33, 0x12345678), (33 | (20 << 16), 0xfffff000),
         (599, 0x80000000), (33, 0xffffefff), (33, 0xfffff001),
         (33, 0xffffffb2), (33, 0xfffffffe), (33, 0xffffffff))


def log(case):
    mutant = case == 'mutant'
    entries = ['B15_ACTIVE_HASHES=PASS', 'GUARD_CF_BEGIN']
    entries += [f'GUARD_CF_KNOWN={nr} RAW={raw}' for nr, raw in KNOWN]
    entries += [f'GUARD_CF_UNKNOWN={n} MASKED={n & 65535}' for n in UNKNOWN]
    if mutant:
        entries.append('GUARD_CF_FAIL=KNOWN_CHECKED_EAX CHECK=4')
    entries += [f'GUARD_CF_CHECKS={COUNT} FAILURES={4 if mutant else 0}',
                'GUARD_CF_FINISHED', f'GUARD_CF_EXIT={10 if mutant else 0}']
    return '\n'.join(entries) + '\n'


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for case in ('positive', 'mutant'):
            (self.root / f'{case}.stdout.log').write_text(log(case), encoding='utf-8')
            (self.root / f'{case}.stderr.log').write_text('benign warning\n', encoding='utf-8')
            (self.root / f'{case}.exit-code.txt').write_text('10\n' if case == 'mutant' else '0\n')
            (self.root / f'probe-{case}').write_bytes(b'non-executable synthetic placeholder')
        self.manifest()

    def manifest(self):
        lines = [f'{hashlib.sha256((self.root / name).read_bytes()).hexdigest()}  {name}'
                 for name in MANIFEST_ITEMS]
        (self.root / 'SHA256SUMS').write_text('\n'.join(lines) + '\n')

    def alter(self, case, former, latter, refresh=True):
        path = self.root / f'{case}.stdout.log'
        text = path.read_text(encoding='utf-8')
        self.assertIn(former, text)
        path.write_text(text.replace(former, latter, 1), encoding='utf-8')
        if refresh:
            self.manifest()

    def test_positive_and_negative_fixture(self):
        self.assertEqual(validate(self.root), [])

    def test_reject_missing_mutant(self):
        (self.root / 'mutant.stdout.log').unlink()
        self.assertTrue(validate(self.root))

    def test_reject_false_mutant_success(self):
        (self.root / 'mutant.exit-code.txt').write_text('0\n')
        self.assertTrue(validate(self.root))

    def test_reject_timeout(self):
        (self.root / 'positive.exit-code.txt').write_text('137\n')
        self.assertTrue(validate(self.root))

    def test_reject_mutant_not_killed(self):
        self.alter('mutant', 'FAILURES=4', 'FAILURES=0')
        self.assertTrue(validate(self.root))

    def test_reject_positive_invented_success(self):
        self.alter('positive', 'FAILURES=0', 'FAILURES=2')
        self.assertTrue(validate(self.root))

    def test_reject_wrong_count(self):
        self.alter('positive', f'CHECKS={COUNT}', 'CHECKS=1')
        self.assertTrue(validate(self.root))

    def test_reject_missing_unknown_65535(self):
        self.alter('positive', 'GUARD_CF_UNKNOWN=65535 MASKED=65535\n', '')
        self.assertTrue(validate(self.root))

    def test_reject_duplicate_finished(self):
        self.alter('positive', 'GUARD_CF_FINISHED\n', 'GUARD_CF_FINISHED\nGUARD_CF_FINISHED\n')
        self.assertTrue(validate(self.root))

    def test_reject_missing_b15(self):
        self.alter('positive', 'B15_ACTIVE_HASHES=PASS\n', '')
        self.assertTrue(validate(self.root))

    def test_reject_checksum_mutation(self):
        self.alter('positive', 'GUARD_CF_BEGIN', 'GUARD_CF_CHANGED', refresh=False)
        self.assertTrue(validate(self.root))

    def test_reject_symlinked_artifact(self):
        p = self.root / 'probe-positive'
        p.unlink()
        p.symlink_to(self.root / 'probe-mutant')
        self.assertTrue(validate(self.root))

    def test_reject_missing_hash_file(self):
        (self.root / 'SHA256SUMS').unlink()
        self.assertTrue(validate(self.root))

    def test_reject_duplicate_hash_line(self):
        p = self.root / 'SHA256SUMS'
        p.write_text(p.read_text() + p.read_text().splitlines()[0] + '\n')
        self.assertTrue(validate(self.root))

    def test_reject_bad_hash_format(self):
        p = self.root / 'SHA256SUMS'
        p.write_text(p.read_text().replace('  ', ' *', 1))
        self.assertTrue(validate(self.root))

    def test_reject_missing_dir(self):
        self.assertTrue(validate(self.root / 'missing'))


if __name__ == '__main__':
    unittest.main()
