#!/usr/bin/env python3
"""Fail-closed negative controls for the eight-file I1 evidence contract."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from verify_guard_cf import (
    COUNT, EXPECTED_KNOWN, EXPECTED_UNKNOWN, MANIFEST_ITEMS, MUTANT_FAILURES, validate
)


def synthetic_log(case):
    mutated = case == "mutant"
    rows = ["B15_ACTIVE_HASHES=PASS", "GUARD_CF_BEGIN"]
    rows.extend(f"GUARD_CF_KNOWN={nr} RAW={value}" for nr, value in EXPECTED_KNOWN)
    rows.extend(f"GUARD_CF_UNKNOWN={nr} MASKED={nr & 0xffff}" for nr in EXPECTED_UNKNOWN)
    if mutated:
        rows.extend(("GUARD_CF_FAIL=KNOWN_CHECKED_EAX CHECK=5",
                     "GUARD_CF_FAIL=KNOWN_CHECKED_ERRNO CHECK=7"))
    rows += [f"GUARD_CF_CHECKS={COUNT} FAILURES={MUTANT_FAILURES if mutated else 0}",
             "GUARD_CF_FINISHED", f"GUARD_CF_EXIT={10 if mutated else 0}"]
    return "\n".join(rows) + "\n"


class EvidenceGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for case in ("positive", "mutant"):
            (self.root / f"{case}.stdout.log").write_text(synthetic_log(case), encoding="utf-8")
            (self.root / f"{case}.stderr.log").write_text("benign warning\n", encoding="utf-8")
            (self.root / f"{case}.exit-code.txt").write_text(
                "10\n" if case == "mutant" else "0\n", encoding="ascii"
            )
            (self.root / f"probe-{case}").write_bytes(b"mock object only, not executable")
        self.manifest()

    def manifest(self):
        records = [f"{hashlib.sha256((self.root / name).read_bytes()).hexdigest()}  {name}"
                   for name in MANIFEST_ITEMS]
        (self.root / "SHA256SUMS").write_text("\n".join(records) + "\n", encoding="ascii")

    def alter_stdout(self, case, before, after, refresh=True):
        target = self.root / f"{case}.stdout.log"
        original = target.read_text()
        self.assertIn(before, original)
        target.write_text(original.replace(before, after, 1))
        if refresh:
            self.manifest()

    def test_positive_and_mutant_accepted(self):
        self.assertEqual(validate(self.root), [])

    def test_mutant_expected_71(self):
        self.assertEqual(MUTANT_FAILURES, 71)

    def test_reject_too_few_mutant_failures(self):
        self.alter_stdout("mutant", "FAILURES=71", "FAILURES=1")
        self.assertTrue(validate(self.root))

    def test_reject_too_many_mutant_failures(self):
        self.alter_stdout("mutant", "FAILURES=71", "FAILURES=72")
        self.assertTrue(validate(self.root))

    def test_reject_mutant_false_success(self):
        self.alter_stdout("mutant", "FAILURES=71", "FAILURES=0")
        self.assertTrue(validate(self.root))

    def test_reject_false_positive_success(self):
        self.alter_stdout("positive", "FAILURES=0", "FAILURES=2")
        self.assertTrue(validate(self.root))

    def test_reject_mutant_without_checked_failure(self):
        self.alter_stdout("mutant", "GUARD_CF_FAIL=KNOWN_CHECKED_EAX CHECK=5",
                          "GUARD_CF_FAIL=UNRELATED CHECK=5")
        self.alter_stdout("mutant", "GUARD_CF_FAIL=KNOWN_CHECKED_ERRNO CHECK=7",
                          "GUARD_CF_FAIL=UNRELATED CHECK=7")
        self.assertTrue(validate(self.root))

    def test_reject_missing_mutant(self):
        (self.root / "mutant.stdout.log").unlink()
        self.assertTrue(validate(self.root))

    def test_reject_timeout(self):
        (self.root / "positive.exit-code.txt").write_text("137\n")
        self.assertTrue(validate(self.root))

    def test_exit_code_tamper_breaks_sha256_even_when_expected(self):
        p = self.root / "mutant.exit-code.txt"
        p.write_text("010\n")
        self.assertTrue(any("SHA256 mismatch: mutant.exit-code.txt" in err
                            for err in validate(self.root)))

    def test_reject_manifest_missing_exit_code(self):
        p = self.root / "SHA256SUMS"
        p.write_text("\n".join(line for line in p.read_text().splitlines()
                               if "positive.exit-code.txt" not in line) + "\n")
        self.assertTrue(validate(self.root))

    def test_reject_bad_manifest_entry(self):
        p = self.root / "SHA256SUMS"
        p.write_text(p.read_text().replace("  ", " *", 1))
        self.assertTrue(validate(self.root))

    def test_reject_duplicate_manifest_entry(self):
        p = self.root / "SHA256SUMS"
        p.write_text(p.read_text() + p.read_text().splitlines()[0] + "\n")
        self.assertTrue(validate(self.root))

    def test_reject_modified_binary(self):
        with (self.root / "probe-positive").open("ab") as f:
            f.write(b"tamper")
        self.assertTrue(validate(self.root))

    def test_reject_symlink_binary(self):
        p = self.root / "probe-mutant"
        p.unlink()
        p.symlink_to(self.root / "probe-positive")
        self.assertTrue(validate(self.root))

    def test_reject_unknown_case_missing(self):
        self.alter_stdout("positive", "GUARD_CF_UNKNOWN=65535 MASKED=65535\n", "")
        self.assertTrue(validate(self.root))

    def test_reject_wrong_known_value(self):
        self.alter_stdout("positive", "GUARD_CF_KNOWN=33 RAW=0\n", "GUARD_CF_KNOWN=33 RAW=1\n")
        self.assertTrue(validate(self.root))

    def test_reject_missing_b15(self):
        self.alter_stdout("positive", "B15_ACTIVE_HASHES=PASS\n", "")
        self.assertTrue(validate(self.root))

    def test_reject_duplicate_finished(self):
        self.alter_stdout("positive", "GUARD_CF_FINISHED\n", "GUARD_CF_FINISHED\nGUARD_CF_FINISHED\n")
        self.assertTrue(validate(self.root))

    def test_reject_contradictory_exit_marker(self):
        self.alter_stdout("positive", "GUARD_CF_EXIT=0\n", "GUARD_CF_EXIT=10\n")
        self.assertTrue(validate(self.root))

    def test_reject_bad_summary_count(self):
        self.alter_stdout("positive", "GUARD_CF_CHECKS=222", "GUARD_CF_CHECKS=221")
        self.assertTrue(validate(self.root))

    def test_reject_missing_manifest(self):
        (self.root / "SHA256SUMS").unlink()
        self.assertTrue(validate(self.root))

    def test_reject_missing_directory(self):
        self.assertTrue(validate(self.root / "missing"))


if __name__ == "__main__":
    unittest.main()
