#!/usr/bin/env python3
"""Regression and deliberate counter-examples for the SH03 source witness."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import quicktime_stubs as witness


def sample(name, stub=True):
    if stub:
        return f'void* {name}(void)\n{{\n    if (verbose) puts("STUB: {name} called");\n    return NULL;\n}}\n'
    return f'TimeScale {name}(Movie m)\n{{\n    return m ? 600 : 0;\n}}\n'


class SourceWitnessTests(unittest.TestCase):
    def test_realistic_explicit_stub_marker(self):
        self.assertEqual(witness.status(sample("OpenMovieFile"), "OpenMovieFile"), "EXPLICIT_STUB")

    def test_no_marker_is_not_a_pass(self):
        self.assertEqual(witness.status(sample("GetMovieTimeScale", False), "GetMovieTimeScale"), "NO_EXPLICIT_STUB_MARKER")

    def test_declaration_is_not_definition(self):
        self.assertEqual(witness.status("void* OpenMovieFile(void);", "OpenMovieFile"), "ABSENT_OR_AMBIGUOUS")

    def test_multiple_defs_ambiguous(self):
        self.assertEqual(witness.status(sample("StartMovie") * 2, "StartMovie"), "ABSENT_OR_AMBIGUOUS")

    def test_comment_does_not_suffice(self):
        s = '// STUB: StartMovie called\n' + sample("StartMovie", False)
        self.assertEqual(witness.status(s, "StartMovie"), "NO_EXPLICIT_STUB_MARKER")

    def test_strict_stub_exits_two(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "QuickTime.c"
            p.write_text("\n".join(sample(n) for n in witness.PLAY_CALLS), encoding="utf-8")
            r = subprocess.run([sys.executable, str(Path(witness.__file__)),
                                "--quicktime-source", str(p), "--strict"],
                               capture_output=True, text=True, check=False)
            self.assertEqual(r.returncode, 2, r.stderr)
            result = json.loads(r.stdout)
            self.assertEqual(len(result["explicit_stubs"]), len(witness.PLAY_CALLS))
            self.assertEqual(result["status"], "STATIC_BLOCKED")

    def test_all_unmarked_source_structural_only(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "QuickTime.c"
            p.write_text("\n".join(sample(n, False) for n in witness.PLAY_CALLS), encoding="utf-8")
            r = subprocess.run([sys.executable, str(Path(witness.__file__)),
                                "--quicktime-source", str(p), "--strict"],
                               capture_output=True, text=True, check=False)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout)["status"], "STATIC_UNMARKED")

    def test_empty_source_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "QuickTime.c"
            p.write_text("", encoding="utf-8")
            r = subprocess.run([sys.executable, str(Path(witness.__file__)),
                                "--quicktime-source", str(p), "--strict"],
                               capture_output=True, text=True, check=False)
            self.assertEqual(r.returncode, 3)
            self.assertEqual(json.loads(r.stdout)["status"], "STATIC_INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
