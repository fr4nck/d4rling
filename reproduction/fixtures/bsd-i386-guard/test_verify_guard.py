#!/usr/bin/env python3
"""Synthetic positive and negative tests for the log verification contract."""
import tempfile
import unittest
from pathlib import Path

from verify_guard import EXPECTED_CANDIDATE, EXPECTED_COUNTS, EXPECTED_KNOWN, EXPECTED_ORIGINAL, validate_case


def sample(variant: str) -> str:
    unknowns = EXPECTED_ORIGINAL if variant == "original" else EXPECTED_CANDIDATE
    rows = ["B15_ACTIVE_HASHES=PASS", f"GUARD_RUNTIME_BEGIN MODE={variant.upper()}",
            "CHECK I386_POINTER_SIZE=PASS"]
    for nr in EXPECTED_KNOWN:
        rows.append(f"CASE=KNOWN NR={nr}")
        rows.extend(f"CHECK {c}=PASS" for c in (
            "KNOWN_EAX", "KNOWN_EDX", "KNOWN_CF", "KNOWN_STACK", "KNOWN_HANDLER"))
    rows.append("CASE=ARGUMENT_FORWARDING")
    rows.extend(f"CHECK {c}=PASS" for c in (
        "FORWARD_14_ARGUMENTS", "FORWARD_ALIGNMENT", "FORWARD_STACK"))
    for nr in unknowns:
        rows.append(f"CASE=UNKNOWN NR={nr} MASKED={nr & 0xffff}")
        rows.extend(f"CHECK {c}=PASS" for c in (
            "UNKNOWN_HANDLER_CALLED", "UNKNOWN_RAW_ENOSYS", "UNKNOWN_RAW_CF",
            "UNKNOWN_STACK"))
        if variant == "original":
            rows.append("CHECK ORIGINAL_NUMBER_BUG_REPRODUCED=PASS")
        else:
            rows.extend(("CHECK CORRECTED_NUMBER=PASS", "CHECK CORRECTED_CALL_ALIGNMENT=PASS"))
    rows += [f"GUARD_CHECKS={EXPECTED_COUNTS[variant]} GUARD_FAILURES=0",
             "GUARD_FINISHED", "FIXTURE_EXIT=0"]
    return "\n".join(rows) + "\n"


class GuardLogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for variant in ("original", "candidate"):
            (self.root / f"{variant}.stdout.log").write_text(sample(variant))
            (self.root / f"{variant}.exit-code.txt").write_text("0\n")

    def test_valid_original_and_candidate(self):
        self.assertEqual(validate_case(self.root, "original"), [])
        self.assertEqual(validate_case(self.root, "candidate"), [])

    def test_reject_out_of_range_case_on_original(self):
        p = self.root / "original.stdout.log"
        p.write_text(p.read_text().replace("CASE=UNKNOWN NR=598 MASKED=598",
                                           "CASE=UNKNOWN NR=600 MASKED=600"))
        self.assertTrue(validate_case(self.root, "original"))

    def test_reject_missing_65535_candidate(self):
        p = self.root / "candidate.stdout.log"
        p.write_text(p.read_text().replace("CASE=UNKNOWN NR=65535 MASKED=65535", ""))
        self.assertTrue(validate_case(self.root, "candidate"))

    def test_reject_fail_even_with_zero_summary(self):
        p = self.root / "candidate.stdout.log"
        p.write_text(p.read_text().replace("CHECK CORRECTED_NUMBER=PASS",
                                           "CHECK CORRECTED_NUMBER=FAIL", 1))
        self.assertTrue(validate_case(self.root, "candidate"))

    def test_reject_false_summary(self):
        p = self.root / "candidate.stdout.log"
        p.write_text(p.read_text().replace("GUARD_CHECKS=61", "GUARD_CHECKS=60"))
        self.assertTrue(validate_case(self.root, "candidate"))

    def test_reject_nonzero_exit(self):
        (self.root / "candidate.exit-code.txt").write_text("137\n")
        self.assertTrue(validate_case(self.root, "candidate"))

    def test_reject_absent_log(self):
        (self.root / "original.stdout.log").unlink()
        self.assertTrue(validate_case(self.root, "original"))

    def test_reject_b15_provenance_missing(self):
        p = self.root / "candidate.stdout.log"
        p.write_text(p.read_text().replace("B15_ACTIVE_HASHES=PASS\n", ""))
        self.assertTrue(validate_case(self.root, "candidate"))

    def test_reject_duplicate_guard_finished(self):
        p = self.root / "candidate.stdout.log"
        p.write_text(p.read_text() + "GUARD_FINISHED\n")
        self.assertTrue(validate_case(self.root, "candidate"))


if __name__ == "__main__":
    unittest.main()
