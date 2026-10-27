#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Host-only regression checks for the independent i386 Mach-O loader fixture."""

import hashlib
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

import generate


GENERATOR = Path(__file__).with_name("generate.py")


def _commands(data):
    magic, cpu, subtype, kind, count, size, flags = struct.unpack_from("<7I", data)
    if magic != 0xFEEDFACE:
        raise ValueError("not a 32-bit Mach-O")
    position = 28
    result = []
    for _ in range(count):
        command, length = struct.unpack_from("<2I", data, position)
        if length < 8 or position + length > 28 + size:
            raise ValueError("invalid load command bounds")
        result.append((command, data[position:position + length]))
        position += length
    if position != 28 + size:
        raise ValueError("load command size mismatch")
    return (cpu, subtype, kind, flags), result


class MachOFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = 0x100000
        cls.binary = generate.make_binary(cls.base)
        cls.header, cls.commands = _commands(cls.binary)

    def test_fixed_page_size(self):
        self.assertEqual(len(self.binary), 4096)

    def test_i386_executable_header(self):
        self.assertEqual(self.header, (7, 3, 2, 1))

    def test_exact_load_commands(self):
        self.assertEqual([kind for kind, _ in self.commands], [1, 1, 5])
        self.assertEqual([len(value) for _, value in self.commands], [56, 124, 80])

    def test_no_dynamic_loader_or_library_commands(self):
        self.assertFalse({12, 13, 14, 15, 24, 31, 32, 35}.intersection(
            kind for kind, _ in self.commands
        ))

    def test_pagezero_segment(self):
        fields = struct.unpack_from("<II16s8I", self.commands[0][1])
        self.assertEqual(fields[2].rstrip(b"\0"), b"__PAGEZERO")
        self.assertEqual(fields[3:11], (0, self.base, 0, 0, 0, 0, 0, 0))

    def test_text_segment_mapping(self):
        fields = struct.unpack_from("<II16s8I", self.commands[1][1])
        self.assertEqual(fields[2].rstrip(b"\0"), b"__TEXT")
        self.assertEqual(fields[3:11], (self.base, 4096, 0, 4096, 7, 5, 1, 0))

    def test_text_section(self):
        section = struct.unpack_from("<16s16s9I", self.commands[1][1], 56)
        self.assertEqual(section[0].rstrip(b"\0"), b"__text")
        self.assertEqual(section[1].rstrip(b"\0"), b"__TEXT")
        self.assertEqual(section[2:6], (self.base + 0x200, 36, 0x200, 4))
        self.assertEqual(section[8], 0x80000400)

    def test_unixthread_flavor_and_eip(self):
        command, length, flavor, register_count = struct.unpack_from(
            "<4I", self.commands[2][1]
        )
        self.assertEqual((command, length, flavor, register_count), (5, 80, 1, 16))
        registers = struct.unpack_from("<16I", self.commands[2][1], 16)
        self.assertEqual(registers[10], self.base + 0x200)
        self.assertEqual(tuple(value for index, value in enumerate(registers)
                               if index != 10), (0,) * 15)

    def test_write_syscall_arguments(self):
        code = self.binary[0x200:0x200 + 36]
        self.assertEqual(code[0:11], b"\xb8\x04\x00\x00\x00\xbb\x01\x00\x00\x00\xb9")
        self.assertEqual(struct.unpack_from("<I", code, 11)[0],
                         self.base + 0x200 + 36)
        self.assertEqual(code[15], 0xBA)
        self.assertEqual(struct.unpack_from("<I", code, 16)[0], len(generate.MARKER))
        self.assertEqual(code[20:22], b"\xcd\x80")

    def test_exit_syscall_arguments(self):
        code = self.binary[0x200:0x200 + 36]
        self.assertEqual(code[22:28], b"\xb8\x01\x00\x00\x00\xbb")
        self.assertEqual(struct.unpack_from("<I", code, 28)[0], 43)
        self.assertEqual(code[32:36], b"\xcd\x80\x0f\x0b")

    def test_marker_data(self):
        self.assertEqual(
            self.binary[0x200 + 36:0x200 + 36 + len(generate.MARKER)],
            b"D4RLING_I386_MACHO_OK\n",
        )

    def test_repeatable_binary_and_digest(self):
        self.assertEqual(self.binary, generate.make_binary(self.base))
        self.assertEqual(len(hashlib.sha256(self.binary).hexdigest()), 64)

    def test_alternative_base_relocates_entry_and_message(self):
        other = generate.make_binary(0x10000)
        _, cmds = _commands(other)
        eip = struct.unpack_from("<16I", cmds[2][1], 16)[10]
        ptr = struct.unpack_from("<I", other, 0x200 + 11)[0]
        self.assertEqual(eip, 0x10200)
        self.assertEqual(ptr, 0x10200 + 36)
        self.assertNotEqual(other, self.binary)

    def test_invalid_bases_rejected(self):
        for base in (-1, 0, 0x1000, 0x10001, 0xFFFFFFFF, "0x100000"):
            with self.subTest(base=base), self.assertRaises(ValueError):
                generate.make_binary(base)

    def test_cli_generates_executable_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "probe"
            call = [sys.executable, "-B", str(GENERATOR), "--output", str(target)]
            result = subprocess.run(call, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("entry=0x100200", result.stdout)
            self.assertEqual(target.read_bytes(), self.binary)
            self.assertTrue(os.access(target, os.X_OK))
            again = subprocess.run(call, capture_output=True, text=True, check=False)
            self.assertEqual(again.returncode, 2)
            self.assertEqual(target.read_bytes(), self.binary)

    def test_cli_refuses_existing_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp) / "do-not-change"
            original.write_bytes(b"protected")
            link = Path(tmp) / "existing-symlink"
            link.symlink_to(original)
            result = subprocess.run(
                [sys.executable, "-B", str(GENERATOR), "--output", str(link)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(original.read_bytes(), b"protected")
            self.assertTrue(link.is_symlink())

    def test_cli_bad_base_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "invalid"
            result = subprocess.run(
                [sys.executable, "-B", str(GENERATOR), "--output", str(target),
                 "--base", "0x10001"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
