#!/usr/bin/env python3
"""Offline, no-network tests for dual-hash full-source Machdep gate."""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import qualify_machdep_i386 as q


class PinnedSourceDirectoryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='d4rling-machdep-source-test-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.samples = {
            'machdep/dispatch.S': b'test machdep asm\n',
            'generated/custom.S': b'test stubs\n',
            'custom/custom.S': b'test stubs\n',
            'include/table.h': b'test header\n',
            'src/table.c': b'test table\n',
        }
        self.sha1 = {}
        self.sha256 = {}
        for name, data in self.samples.items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            self.sha1[name] = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
            self.sha256[name] = hashlib.sha256(data).hexdigest()
        patches = (patch.object(q, 'PINNED', self.sha1),
                   patch.object(q, 'PINNED_SHA256', self.sha256))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_accepts_exact_five_files(self):
        self.assertEqual(q.read_pinned_directory(self.root),
                         {k: v.decode('utf-8') for k, v in self.samples.items()})

    def test_does_not_modify_source_files(self):
        before = {k: (self.root / k).stat().st_mtime_ns for k in self.samples}
        q.read_pinned_directory(self.root)
        self.assertEqual(before, {k: (self.root / k).stat().st_mtime_ns for k in self.samples})

    def test_rejects_missing_source(self):
        (self.root / 'machdep/dispatch.S').unlink()
        with self.assertRaises(q.GateError):
            q.read_pinned_directory(self.root)

    def test_rejects_extra_byte(self):
        with (self.root / 'src/table.c').open('ab') as f:
            f.write(b'x')
        with self.assertRaisesRegex(q.GateError, 'Git blob mismatch'):
            q.read_pinned_directory(self.root)

    def test_rejects_crlf_drift(self):
        (self.root / 'generated/custom.S').write_bytes(b'test stubs\r\n')
        with self.assertRaisesRegex(q.GateError, 'Git blob mismatch'):
            q.read_pinned_directory(self.root)

    def test_rejects_mismatched_sha256_even_with_valid_git_sha1(self):
        self.sha256['src/table.c'] = '0' * 64
        with self.assertRaisesRegex(q.GateError, 'SHA-256 mismatch'):
            q.read_pinned_directory(self.root)

    def test_rejects_incomplete_sha256_contract(self):
        del self.sha256['src/table.c']
        with self.assertRaisesRegex(q.GateError, 'incomplete'):
            q.read_pinned_directory(self.root)

    def test_rejects_symlink_source_file(self):
        p = self.root / 'src/table.c'
        p.unlink()
        p.symlink_to(self.root / 'include/table.h')
        with self.assertRaisesRegex(q.GateError, 'symlink'):
            q.read_pinned_directory(self.root)

    def test_rejects_symlink_intermediate_directory(self):
        (self.root / 'include/table.h').unlink()
        (self.root / 'include').rmdir()
        (self.root / 'include').symlink_to(self.root / 'src')
        with self.assertRaisesRegex(q.GateError, 'symlink'):
            q.read_pinned_directory(self.root)

    def test_rejects_symlink_source_root(self):
        link = self.root.parent / (self.root.name + '-link')
        link.symlink_to(self.root)
        self.addCleanup(link.unlink)
        with self.assertRaisesRegex(q.GateError, 'symlink'):
            q.read_pinned_directory(link)

    def test_rejects_missing_root(self):
        with self.assertRaisesRegex(q.GateError, 'root missing'):
            q.read_pinned_directory(self.root / 'absent')

    def test_rejects_invalid_utf8_when_digests_are_valid(self):
        data = b'\xff'
        name = 'src/table.c'
        (self.root / name).write_bytes(data)
        self.sha1[name] = hashlib.sha1(b'blob 1\0\xff').hexdigest()
        self.sha256[name] = hashlib.sha256(data).hexdigest()
        with self.assertRaisesRegex(q.GateError, 'not valid UTF-8'):
            q.read_pinned_directory(self.root)


if __name__ == '__main__':
    unittest.main()
