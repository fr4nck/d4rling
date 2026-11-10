#!/usr/bin/env python3
"""Synthetic positive/negative tests for the R4-B read-only Mach-O probe.

Run: python3 -m unittest discover -s reproduction/fixtures -p 'test_bsd_i386_r4_b_readonly.py' -v
No external SDK, guest execution, network, or installation required.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import struct
import unittest


PROBE = Path(__file__).with_name("bsd-i386-r4-b-readonly.py")
SPEC = importlib.util.spec_from_file_location("bsd_i386_r4_b_probe", PROBE)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def thin(*, cpu=7, flags=0, vmaddr=0x1000, malformed=False):
    name = b"__TEXT" + b"\x00" * 10
    segment = struct.pack("<II16sIIIIIIII", 1, 56, name, vmaddr,
                          0x2000, 0, 0x1000, 7, 5, 0, 0)
    if malformed:
        segment = bytearray(segment[:40])
        struct.pack_into("<I", segment, 4, 40)
        segment = bytes(segment)
    header = struct.pack("<IIIIIII", 0xfeedface, cpu, 3, 2, 1,
                         len(segment), flags)
    return header + segment


def fat(slice_data, *, cpu=7, offset=28):
    header = struct.pack(">II", 0xcafebabe, 1)
    arch = struct.pack(">IIIII", cpu, 3, offset, len(slice_data), 0)
    return header + arch + b"\x00" * (offset - 28) + slice_data


def output(data):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        probe.inspect(data)
    return buf.getvalue()


class ProbeR4BTests(unittest.TestCase):
    def test_thin_i386_text_at_0x1000(self):
        out = output(thin())
        self.assertIn("CPU=i386", out)
        self.assertIn("PIE=False", out)
        self.assertIn("SEGMENT=__TEXT VMADDR=0x1000", out)
        self.assertIn("INITPROT=0x5 MAXPROT=0x7", out)

    def test_pie_flag_is_reported_not_interpreted_as_effective_address(self):
        out = output(thin(flags=0x200000))
        self.assertIn("PIE=True", out)
        self.assertIn("VMADDR=0x1000", out)

    def test_fat_i386_slice(self):
        self.assertIn("SEGMENT=__TEXT", output(fat(thin())))

    def test_wrong_architecture_rejected(self):
        with self.assertRaisesRegex(ValueError, "not i386"):
            output(thin(cpu=0x01000007))

    def test_fat_without_i386_rejected(self):
        with self.assertRaisesRegex(ValueError, "exactly one i386"):
            output(fat(thin(), cpu=12))

    def test_fat_slice_out_of_bounds_rejected(self):
        broken = bytearray(fat(thin()))
        struct.pack_into(">I", broken, 16, 0xffffffff)
        with self.assertRaisesRegex(ValueError, "bounds"):
            output(bytes(broken))

    def test_truncated_segment_rejected(self):
        with self.assertRaisesRegex(ValueError, "truncated LC_SEGMENT"):
            output(thin(malformed=True))

    def test_invalid_load_command_size_rejected(self):
        broken = bytearray(thin())
        struct.pack_into("<I", broken, 32, 0)
        with self.assertRaisesRegex(ValueError, "invalid load command size"):
            output(bytes(broken))

    def test_fat_duplicate_i386_slices_rejected(self):
        payload = thin()
        offset = 8 + 2 * 20
        header = struct.pack(">II", 0xcafebabe, 2)
        arch1 = struct.pack(">IIIII", 7, 3, offset, len(payload), 0)
        arch2 = struct.pack(">IIIII", 7, 3, offset, len(payload), 0)
        with self.assertRaisesRegex(ValueError, "exactly one i386"):
            output(header + arch1 + arch2 + payload)

    def test_fat_i386_slice_overlapping_header_rejected(self):
        payload = thin()
        wrapped = bytearray(fat(payload))
        struct.pack_into(">I", wrapped, 16, 8)
        with self.assertRaisesRegex(ValueError, "invalid FAT i386 bounds"):
            output(bytes(wrapped))

    def test_fat_truncated_architecture_table_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid FAT architecture table"):
            output(struct.pack(">II", 0xcafebabe, 2) + b"\x00" * 20)

    def test_macho_command_table_truncated_rejected(self):
        broken = bytearray(thin())
        struct.pack_into("<I", broken, 20, 4096)
        with self.assertRaisesRegex(ValueError, "invalid Mach-O command table"):
            output(bytes(broken))

    def test_macho_extra_bytes_in_command_table_rejected(self):
        broken = bytearray(thin())
        struct.pack_into("<I", broken, 16, 0)
        with self.assertRaisesRegex(ValueError, "load commands do not consume"):
            output(bytes(broken))

    def test_big_endian_thin_i386(self):
        name = b"__TEXT" + b"\x00" * 10
        segment = struct.pack(">II16sIIIIIIII", 1, 56, name,
                              0x1000, 0x2000, 0, 0x1000, 7, 5, 0, 0)
        header = struct.pack(">IIIIIII", 0xfeedface, 7, 3, 2, 1, 56, 0)
        self.assertIn("SEGMENT=__TEXT VMADDR=0x1000", output(header + segment))

    def test_little_endian_fat_wrapper(self):
        payload = thin()
        header = struct.pack("<II", 0xcafebabe, 1)
        arch = struct.pack("<IIIII", 7, 3, 28, len(payload), 0)
        self.assertIn("CPU=i386", output(header + arch + payload))

    def test_fat_slice_with_nonzero_padding(self):
        self.assertIn("SEGMENT=__TEXT", output(fat(thin(), offset=64)))

    def test_unrecognized_format_rejected(self):
        with self.assertRaisesRegex(ValueError, "not a 32-bit Mach-O"):
            output(b"Z" * 100)


if __name__ == "__main__":
    unittest.main()
