#!/usr/bin/env python3
"""SH15 portable kit tests: exact source pins, negative exits; never execute a fake linker.

GPL-3.0-or-later (C) 2026 D4rling contributors. Run with Python stdlib.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import zipfile

import build_sh15_portable as builder

HERE = Path(__file__).resolve().parent
SUBMODULE = 'd9456c221e1f462e17c0b3297748bc089d5a861e'
BASE = 'b7d0cb6a79fe196657deb9711647f8486bcc5e5e'


class SH15PortableTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='sh15-test-')
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.kit = self.tmp / 'kit'
        self.kit.mkdir()
        self.files = [*builder.TOOL_GIT_BLOBS, builder.SHELL_NAME]
        for name in self.files:
            shutil.copy2(HERE / name, self.kit / name)
        external_zip = Path(os.environ['SOUNDHACK_SH10_PACKAGE']) if os.environ.get('SOUNDHACK_SH10_PACKAGE') else HERE / builder.SH10_NAME
        self.have_zip = external_zip.is_file()
        if self.have_zip:
            shutil.copy2(external_zip, self.kit / builder.SH10_NAME)
        self.license = HERE / 'LICENSE-GPL-3.0.txt'
        if not self.license.is_file():
            self.license = HERE.parents[2] / 'LICENSE'
        self.script = self.kit / builder.SHELL_NAME
        self.root = self.tmp / 'historical'

    def require_zip(self):
        if not self.have_zip:
            self.skipTest('pinned external SH10 ZIP not provided (SOUNDHACK_SH10_PACKAGE)')

    def invoke(self):
        return subprocess.run(['bash', str(self.script)], text=True, capture_output=True,
                              timeout=12, env={**os.environ, 'D4RLING_10400_ROOT': str(self.root)})

    def make_historical_root(self):
        source = self.root / 'source'
        build = self.root / 'build-core-i386'
        (build / 'src/external/cctools-port/cctools/ld64/src/ld/.libs').mkdir(parents=True)
        (source / 'src/external/cctools-port').mkdir(parents=True)
        (source / 'D4RLING-REPRODUCTION.json').write_text(json.dumps({
            'base': BASE, 'historical_local_overlay': True
        }), encoding='utf8')
        (build / 'CMakeCache.txt').write_text(f'CMAKE_HOME_DIRECTORY:INTERNAL={source}\n', encoding='utf8')
        subprocess.run(['git', 'init', '-q', str(source / 'src/external/cctools-port')], check=True)
        (source / 'src/external/cctools-port/.git/HEAD').write_text(SUBMODULE + '\n', encoding='ascii')
        return build

    def test_01_all_modules_match_pinned_git_blobs(self):
        for name, expected in builder.TOOL_GIT_BLOBS.items():
            with self.subTest(name=name):
                self.assertEqual(builder.git_blob((HERE / name).read_bytes()), expected)

    def test_02_actual_sh10_zip_is_pinned(self):
        self.require_zip()
        blob = (self.kit / builder.SH10_NAME).read_bytes()
        self.assertEqual(hashlib.sha256(blob).hexdigest(), builder.SH10_SHA256)

    def test_03_no_root_exits_three_without_creating_validation_folder(self):
        self.require_zip()
        proc = self.invoke()
        self.assertEqual(proc.returncode, 3)
        self.assertIn('root missing', proc.stderr)
        self.assertFalse((self.root / 'validation').exists())

    def test_04_mutated_tool_is_refused_before_build(self):
        self.require_zip()
        with (self.kit / 'macho_audit.py').open('ab') as f:
            f.write(b'# maliciously changed\n')
        proc = self.invoke()
        self.assertEqual(proc.returncode, 3)
        self.assertIn('module modified', proc.stderr)
        self.assertFalse(self.root.exists())

    def test_05_mutated_sh10_zip_is_refused(self):
        self.require_zip()
        with (self.kit / builder.SH10_NAME).open('ab') as f:
            f.write(b'X')
        proc = self.invoke()
        self.assertEqual(proc.returncode, 3)
        self.assertIn('SH10 ZIP SHA-256 mismatch', proc.stderr)
        self.assertFalse(self.root.exists())

    def test_06_historical_build_without_real_linker_is_inconclusive(self):
        self.require_zip()
        self.make_historical_root()
        proc = self.invoke()
        self.assertEqual(proc.returncode, 3, proc.stderr)
        self.assertIn('sh15_linker_candidates', proc.stdout)
        self.assertIn('no single qualified native cctools linker', proc.stderr)
        self.assertFalse((self.root / 'validation').exists())

    def test_07_two_fake_elf_candidates_are_ambiguous_and_not_run(self):
        self.require_zip()
        build = self.make_historical_root()
        for relative in ('src/external/cctools-port/cctools/ld64/src/ld/ld',
                         'src/external/cctools-port/cctools/ld64/src/ld/.libs/ld'):
            p = build / relative
            data = bytearray(96)
            data[:6] = b'\x7fELF\x02\x01'
            struct.pack_into('<H', data, 16, 2)
            machine = 62 if os.uname().machine.lower() == 'x86_64' else 183
            struct.pack_into('<H', data, 18, machine)
            p.write_bytes(data)
            p.chmod(0o755)
        proc = self.invoke()
        self.assertEqual(proc.returncode, 3, proc.stderr)
        self.assertEqual(proc.stdout.count('"sha256"'), 2)
        self.assertFalse((self.root / 'validation').exists())

    def test_08_builder_outputs_repeatable_zip(self):
        self.require_zip()
        first = self.tmp / 'a.zip'
        second = self.tmp / 'b.zip'
        a = builder.create(self.kit, self.kit / builder.SH10_NAME, self.license, first)
        b = builder.create(self.kit, self.kit / builder.SH10_NAME, self.license, second)
        self.assertEqual(a['sha256'], b['sha256'])
        with zipfile.ZipFile(first) as bundle:
            self.assertIsNone(bundle.testzip())
            self.assertEqual(bundle.read('sh12_cctools_replay.py'), (self.kit / 'sh12_cctools_replay.py').read_bytes())

    def test_09_builder_refuses_existing_zip(self):
        self.require_zip()
        out = self.tmp / 'existing.zip'
        out.write_bytes(b'sentinel')
        with self.assertRaisesRegex(ValueError, 'output exists'):
            builder.create(self.kit, self.kit / builder.SH10_NAME, self.license, out)
        self.assertEqual(out.read_bytes(), b'sentinel')

    def test_10_builder_refuses_mutated_source(self):
        self.require_zip()
        with (self.kit / 'sh12_cctools_replay.py').open('ab') as f:
            f.write(b'\n')
        output = self.tmp / 'should-not-exist.zip'
        with self.assertRaisesRegex(ValueError, 'unexpected committed tool'):
            builder.create(self.kit, self.kit / builder.SH10_NAME, self.license, output)
        self.assertFalse(output.exists())

    def test_11_shell_syntax_is_valid_without_external_zip(self):
        proc = subprocess.run(['bash', '-n', str(self.script)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == '__main__':
    unittest.main()
