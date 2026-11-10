#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""C4-D-M2: end-to-end host CLI gate with synthetic i386 Mach-O dylibs.

These are fabricated test fixtures, NOT a production QuickTime/CarbonCore build.
The existing SoundHack reader and thin fixture generator are reused unchanged.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

GATE = Path(__file__).with_name('check_c4d_macho_i386.py')
spec = importlib.util.spec_from_file_location('c4d_m2_cli_reader', GATE)
if spec is None or spec.loader is None:
    raise RuntimeError('M2 gate module is missing')
m2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m2)
sys.path.insert(0, str(m2.PARSER.parent))
try:
    from test_macho_audit import thin
finally:
    sys.path.pop(0)

IDS = {
    'QuickTime': '/System/Library/Frameworks/QuickTime.framework/Versions/A/QuickTime',
    'CoreServices': '/System/Library/Frameworks/CoreServices.framework/Versions/A/CoreServices',
    'CarbonCore': ('/System/Library/Frameworks/CoreServices.framework/Frameworks/'
                   'CarbonCore.framework/Versions/A/CarbonCore'),
}


def fixture_images(*, reexport=True, dyld_info=False):
    qt = thin(install_name=IDS['QuickTime'], dylibs=[IDS['CoreServices']],
              imports=[(symbol, 1, False) for symbol in m2.SYMS],
              exports=['_GetMediaSample'], two_level=True, dyld_info=dyld_info)
    core = bytearray(thin(install_name=IDS['CoreServices'],
                          dylibs=[IDS['CarbonCore']], two_level=True))
    if reexport:
        pos = 28
        changed = 0
        for _ in range(struct.unpack_from('<I', core, 16)[0]):
            cmd, size = struct.unpack_from('<II', core, pos)
            if cmd == 0xC:
                struct.pack_into('<I', core, pos, 0x8000001F)
                changed += 1
            pos += size
        if changed != 1:
            raise AssertionError('expected exactly one synthetic CarbonCore load')
    carbon = thin(install_name=IDS['CarbonCore'], exports=m2.SYMS, two_level=True)
    return {'QuickTime': qt, 'CoreServices': bytes(core), 'CarbonCore': carbon}


class MachOCLITests(unittest.TestCase):
    def call_gate(self, *, reexport=True, dyld_info=False):
        with tempfile.TemporaryDirectory(prefix='d4rling-c4d-m2-') as tmp:
            files = {name: Path(tmp) / name for name in m2.FRAMEWORKS}
            for name, body in fixture_images(reexport=reexport, dyld_info=dyld_info).items():
                files[name].write_bytes(body)
            hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                      for name, path in files.items()}
            cmd = [sys.executable, '-B', str(GATE)]
            for name in m2.FRAMEWORKS:
                cmd.extend(['--' + name.lower(), str(files[name])])
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertFalse(proc.stderr, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertEqual(proc.returncode, result['exit_code'])
            self.assertEqual(hashes, {name: hashlib.sha256(path.read_bytes()).hexdigest()
                                      for name, path in files.items()}, 'input mutated')
            self.assertEqual(hashes, {name: result['inputs'][name]['sha256']
                                      for name in files}, 'sha256 evidence mismatch')
            self.assertEqual(result['shared_parser_git_blob'], m2.PARSER_BLOB)
            return result

    def test_valid_synthetic_reexport_chain(self):
        result = self.call_gate()
        self.assertEqual((result['exit_code'], result['status']), (0, 'STATIC_GATE_PASS'))
        self.assertTrue(any('no C4 ABI' in x for x in result['limitations']))

    def test_missing_reexport_is_static_fail(self):
        result = self.call_gate(reexport=False)
        self.assertEqual((result['exit_code'], result['status']), (2, 'STATIC_FAIL'))
        self.assertIn('LC_REEXPORT_DYLIB', ' '.join(result['errors']))

    def test_dyld_info_is_inconclusive_not_false_pass(self):
        result = self.call_gate(dyld_info=True)
        self.assertEqual((result['exit_code'], result['status']), (3, 'STATIC_INCONCLUSIVE'))
        self.assertIn('LC_DYLD_INFO', ' '.join(result['inconclusive']))


if __name__ == '__main__':
    unittest.main()
