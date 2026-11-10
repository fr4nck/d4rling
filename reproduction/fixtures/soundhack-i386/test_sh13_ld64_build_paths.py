#!/usr/bin/env python3
"""SH13: candidate-path tests only; fake ELF headers are NEVER executed."""
from pathlib import Path
import platform
import struct
import tempfile
import unittest

import sh12_cctools_replay as gate


def fake_elf():
    data = bytearray(80)
    data[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<H', data, 16, 2)
    struct.pack_into('<H', data, 18, gate.MACHINE.get(platform.machine().lower(), 62))
    return bytes(data)


class BuildLayoutTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix='sh13-layout-')
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)

    def emit(self, relative, data=None):
        p = self.root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(fake_elf() if data is None else data)
        p.chmod(0o755)
        return p

    def assert_only(self, p):
        self.assertEqual([x['path'] for x in gate.find_linkers(self.root)], [str(p)])

    def test_cmake_nested_output(self):
        p = self.emit('src/external/cctools-port/cctools/ld64/src/ld/ld')
        self.assert_only(p)

    def test_cmake_libtool_elf_output(self):
        p = self.emit('src/external/cctools-port/cctools/ld64/src/ld/.libs/ld')
        self.assert_only(p)

    def test_separate_build_root(self):
        p = self.emit('cctools-port/cctools/ld64/src/ld/ld')
        self.assert_only(p)

    def test_libtool_wrapper_ignored(self):
        self.emit('cctools-port/cctools/ld64/src/ld/ld', b'#!/bin/sh\nexit 0\n')
        elf = self.emit('cctools-port/cctools/ld64/src/ld/.libs/ld')
        self.assert_only(elf)

    def test_duplicate_executables_not_silently_selected(self):
        self.emit('cctools-port/cctools/ld64/src/ld/ld')
        self.emit('cctools-port/cctools/ld64/src/ld/.libs/ld')
        self.assertEqual(len(gate.find_linkers(self.root)), 2)

    def test_symlink_candidate_excluded(self):
        elf = self.emit('cctools-port/cctools/ld64/src/ld/.libs/ld')
        (elf.parent.parent / 'ld').symlink_to(elf)
        self.assert_only(elf)

    def test_unrelated_path_excluded(self):
        self.emit('some-other-tool/ld64/src/ld/.libs/ld')
        self.assertEqual(gate.find_linkers(self.root), [])

    def test_old_path_remains_supported(self):
        elf = self.emit('src/external/cctools-port/cctools/ld64/src/ld')
        self.assert_only(elf)


if __name__ == '__main__':
    unittest.main()
