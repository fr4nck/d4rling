#!/usr/bin/env python3
"""Tests of the SoundHack original-FFT host probe (not guest or audio)."""
# Copyright (C) 2026 D4rling contributors; GPL-3.0-or-later.
import contextlib
import io
import json
import math
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import fft_host_probe as probe

HEADER = b"void InitFFTTable(void);\nvoid FFT(float *, long, short);\nvoid RealFFT(float *, long, short);\n"
NOOP = b"""void InitFFTTable(void) {}\nvoid FFT(float *d, long n, short dir) {(void)d;(void)n;(void)dir;}\nvoid RealFFT(float *d, long n, short dir) {(void)d;(void)n;(void)dir;}\n"""
NAN = b"""#include <math.h>\nvoid InitFFTTable(void) {}\nvoid FFT(float *d, long n, short dir) {(void)n;(void)dir;d[0]=NAN;}\nvoid RealFFT(float *d, long n, short dir) {(void)n;(void)dir;d[0]=NAN;}\n"""
MISSING = b"""void InitFFTTable(void) {}\nvoid FFT(float *d, long n, short dir) {(void)d;(void)n;(void)dir;}\n"""
INVALID = b"this is not a C program!\n"


class FFTProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-sh-fft-")
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)

    def make_sources(self, source=NOOP, header=HEADER):
        (self.dir / "FFT.c").write_bytes(source)
        (self.dir / "FFT.h").write_bytes(header)
        return probe.git_blob_sha(source), probe.git_blob_sha(header)

    def run_cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as buffer:
            code = probe.main(["--source-dir", str(self.dir), *args])
        return code, json.loads(buffer.getvalue())

    def test_git_blob_matches_known_reference(self):
        self.assertEqual(probe.git_blob_sha(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_dft_oracle_has_positive_exponent(self):
        spec = probe.dft([0, 1, 0, 0])
        for got, want in zip(spec, [1, 1j, -1, -1j]):
            self.assertLess(abs(got - want), 1e-12)

    def test_rejects_missing_sources(self):
        code, result = self.run_cli()
        self.assertEqual((code, result["status"]), (3, "INCONCLUSIVE"))

    def test_rejects_unexpected_source_hash(self):
        self.make_sources()
        code, result = self.run_cli()
        self.assertEqual(code, 3)
        self.assertIn("unexpected Git blob", result["error"])

    def test_rejects_unexpected_header_hash(self):
        src_sha, _ = self.make_sources()
        code, result = self.run_cli("--expected-source-blob", src_sha)
        self.assertEqual(code, 3)
        self.assertIn("FFT.h", result["error"])

    def test_rejects_missing_compiler(self):
        src_sha, hdr_sha = self.make_sources()
        code, result = self.run_cli("--expected-source-blob", src_sha,
                                    "--expected-header-blob", hdr_sha,
                                    "--cc", "this-compiler-does-not-exist")
        self.assertEqual(code, 3)
        self.assertIn("compiler not available", result["error"])

    @unittest.skipUnless(shutil.which("cc"), "C compiler not installed")
    def test_compiler_failure_not_pass(self):
        src_sha, hdr_sha = self.make_sources(INVALID)
        code, result = self.run_cli("--expected-source-blob", src_sha,
                                    "--expected-header-blob", hdr_sha)
        self.assertEqual(code, 3)
        self.assertIn("compiler returned nonzero", result["error"])

    @unittest.skipUnless(shutil.which("cc"), "C compiler not installed")
    def test_missing_entrypoint_not_pass(self):
        src_sha, hdr_sha = self.make_sources(MISSING)
        code, result = self.run_cli("--expected-source-blob", src_sha,
                                    "--expected-header-blob", hdr_sha)
        self.assertEqual(code, 3)
        self.assertIn("RealFFT", result["error"])

    @unittest.skipUnless(shutil.which("cc"), "C compiler not installed")
    def test_noop_mutant_is_detected(self):
        src_sha, hdr_sha = self.make_sources()
        code, result = self.run_cli("--expected-source-blob", src_sha,
                                    "--expected-header-blob", hdr_sha)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "HOST_DSP_FAIL")
        self.assertLess(result["passed"], 24)

    @unittest.skipUnless(shutil.which("cc"), "C compiler not installed")
    def test_nonfinite_mutant_is_detected_and_json_safe(self):
        src_sha, hdr_sha = self.make_sources(NAN)
        code, result = self.run_cli("--expected-source-blob", src_sha,
                                    "--expected-header-blob", hdr_sha)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "HOST_DSP_FAIL")
        self.assertGreater(result["spectral_abs_max"], 1e20)
        self.assertTrue(math.isfinite(result["spectral_abs_max"]))

    @unittest.skipUnless(os.environ.get("SOUNDHACK_MATH_DIR"),
                         "Provide pinned SoundHack Math/ source in SOUNDHACK_MATH_DIR")
    @unittest.skipUnless(shutil.which("cc"), "C compiler not installed")
    def test_original_fft_and_realfft_against_oracle(self):
        original = Path(os.environ["SOUNDHACK_MATH_DIR"])
        result = probe.run(original)
        self.assertEqual(result["status"], "HOST_DSP_PASS")
        self.assertEqual((result["passed"], result["cases"]), (24, 24))


    @unittest.skipUnless(os.environ.get("SOUNDHACK_MATH_DIR"),
                         "Provide pinned SoundHack Math/ source in SOUNDHACK_MATH_DIR")
    @unittest.skipUnless(shutil.which("cc"), "C compiler not installed")
    def test_real_source_wrong_sign_mutant_is_detected(self):
        source_dir = Path(os.environ["SOUNDHACK_MATH_DIR"])
        original = (source_dir / "FFT.c").read_bytes()
        self.assertEqual(probe.git_blob_sha(original), probe.SOURCE_SHA)
        old = b"omegaPiImag = gOmegaPiImag[n];"
        self.assertEqual(original.count(old), 1)
        altered = original.replace(old, b"omegaPiImag = -gOmegaPiImag[n];")
        source_sha, header_sha = self.make_sources(
            altered, (source_dir / "FFT.h").read_bytes())
        result = probe.run(self.dir, source_sha, header_sha)
        self.assertEqual(result["status"], "HOST_DSP_FAIL")
        self.assertLess(result["passed"], result["cases"])

    @unittest.skipUnless(os.environ.get("SOUNDHACK_MATH_DIR"),
                         "Provide pinned SoundHack Math/ source in SOUNDHACK_MATH_DIR")
    @unittest.skipUnless(shutil.which("cc"), "C compiler not installed")
    def test_real_source_no_inverse_scaling_mutant_is_detected(self):
        source_dir = Path(os.environ["SOUNDHACK_MATH_DIR"])
        original = (source_dir / "FFT.c").read_bytes()
        self.assertEqual(probe.git_blob_sha(original), probe.SOURCE_SHA)
        old = b"data[i] *= scale;"
        self.assertEqual(original.count(old), 1)
        altered = original.replace(old, b"data[i] *= 1.0f;")
        source_sha, header_sha = self.make_sources(
            altered, (source_dir / "FFT.h").read_bytes())
        result = probe.run(self.dir, source_sha, header_sha)
        self.assertEqual(result["status"], "HOST_DSP_FAIL")
        self.assertTrue(any(case["spectral_abs_error"] < probe.SPECTRAL_LIMIT and
                            case["roundtrip_abs_error"] > probe.ROUNDTRIP_LIMIT
                            for case in result["results"]))


if __name__ == "__main__":
    unittest.main()
