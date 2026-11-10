#!/usr/bin/env python3
"""Positive/negative HOST-only gates for actual-source Gestalt extraction."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import gestalt_startup_gate as gate

# No Apple SDK code copied; these are synthetic minimal C++ behaviors.
GOOD = '''OSStatus Gestalt(uint32_t type, int* value) {
    if (type == gestaltCarbonVersion) { *value = 0x0101; return 0; }
    if (type == gestaltSystemVersion) { *value = 0x1040; return 0; }
    if (type == gestaltSysArchitecture) { *value = gestaltIntel; return 0; }
    *value = 0; return unimpErr;
}
'''
BAD_CARBON = GOOD.replace('if (type == gestaltCarbonVersion) { *value = 0x0101; return 0; }',
                           'if (type == gestaltCarbonVersion) { *value = 0; return unimpErr; }')
BAD_SYSTEM = GOOD.replace('if (type == gestaltSystemVersion) { *value = 0x1040; return 0; }',
                           'if (type == gestaltSystemVersion) { *value = gestaltIntel; return 0; }')


@unittest.skipUnless(shutil.which('c++'), 'requires existing host C++ compiler')
class GestaltGateTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)

    def file(self, text):
        f = self.root / 'Gestalt.cpp'
        f.write_text(text, encoding='utf-8')
        return f

    def run_cli(self, source, *extra):
        r = subprocess.run([sys.executable, str(Path(gate.__file__)), '--gestalt-source', str(source), *extra],
                           text=True, capture_output=True, check=False)
        self.assertFalse(r.stderr, r.stderr)
        return r.returncode, json.loads(r.stdout)

    def test_synthetic_working_carbon_and_system_pass(self):
        rc, out = self.run_cli(self.file(GOOD))
        self.assertEqual(rc, 0)
        self.assertEqual(out['status'], 'HOST_STARTUP_GATE_ELIGIBLE')
        self.assertFalse(out['carbon_selector']['blocks_soundhack'])
        self.assertFalse(out['system_selector']['blocks_soundhack'])

    def test_unknown_carbon_selector_blocks_before_mainloop(self):
        rc, out = self.run_cli(self.file(BAD_CARBON))
        self.assertEqual(rc, 2)
        self.assertTrue(out['carbon_selector']['blocks_soundhack'])
        self.assertFalse(out['system_selector']['blocks_soundhack'])

    def test_wrong_system_value_blocks_gate(self):
        rc, out = self.run_cli(self.file(BAD_SYSTEM))
        self.assertEqual(rc, 2)
        self.assertEqual(out['system_selector']['value'], 10)
        self.assertFalse(out['carbon_selector']['blocks_soundhack'])

    def test_expected_blob_mismatch_fails_closed(self):
        rc, out = self.run_cli(self.file(GOOD), '--expected-blob', '0' * 40)
        self.assertEqual(rc, 3)
        self.assertIn('blob mismatch', out['error'])

    def test_invalid_or_duplicate_source_fails_closed(self):
        f = self.file('not a C++ Gestalt body')
        self.assertEqual(self.run_cli(f)[0], 3)
        self.assertEqual(self.run_cli(self.file(GOOD + GOOD))[0], 3)

    def test_compile_failure_is_blocked_not_pass(self):
        f = self.file('OSStatus Gestalt(uint32_t type, int* value) { this is not valid C++; }')
        rc, out = self.run_cli(f)
        self.assertEqual(rc, 3)
        self.assertIn('compile failed', out['error'])

    def test_missing_compiler_blocks_not_fake_pass(self):
        rc, out = self.run_cli(self.file(GOOD), '--compiler', 'nonexistent-cxx-tool-SH05')
        self.assertEqual(rc, 3)
        self.assertIn('missing host C++ compiler', out['error'])

    def test_source_bytes_unchanged(self):
        f = self.file(GOOD)
        before = f.read_bytes()
        self.assertEqual(self.run_cli(f)[0], 0)
        self.assertEqual(f.read_bytes(), before)

    def test_pinned_production_source_if_present(self):
        # In a real D4rling checkout (not a temporary fixture-only package).
        repo = Path(__file__).resolve().parents[3]
        prod = repo / 'src/frameworks/CoreServices/src/CarbonCore/Gestalt.cpp'
        if not prod.exists():
            self.skipTest('complete D4rling checkout not available in this test workspace')
        if gate.git_blob(prod.read_bytes()) != gate.PINNED_BLOB:
            self.skipTest('production Gestalt.cpp changed; requires revision-specific requalification')
        rc, out = self.run_cli(prod, '--expected-blob', gate.PINNED_BLOB)
        self.assertEqual(rc, 2)
        self.assertTrue(out['carbon_selector']['blocks_soundhack'])
        self.assertTrue(out['system_selector']['blocks_soundhack'])
        self.assertEqual(out['architecture_selector']['value'], 10)


if __name__ == '__main__':
    unittest.main()
