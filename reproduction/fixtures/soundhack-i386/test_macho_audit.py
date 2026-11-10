#!/usr/bin/env python3
"""Independent synthetic positive/negative fixtures for macho_audit.py."""

from __future__ import annotations

import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

import macho_audit as audit


def thin(arch="i386", imports=(), exports=(), dylibs=(), *, endian="<", no_symtab=False,
         dyld_info=False):
    cpu = audit.ARCH_CPUS[arch]
    is64 = arch in ("x86_64", "ppc64", "arm64")
    magic = 0xfeedfacf if is64 else 0xfeedface
    header_len = 32 if is64 else 28
    cmds = []
    for name in dylibs:
        raw = name.encode() + b"\0"
        size = (24 + len(raw) + 3) & ~3
        cmds.append(struct.pack(endian + "IIIIII", 0xC, size, 24, 0, 0, 0) + raw + b"\0" * (size - 24 - len(raw)))
    if dyld_info:
        cmds.append(struct.pack(endian + "II", audit.LC_DYLD_INFO_ONLY, 8))
    syms = b""
    strings = b"\0"
    items = [(name, 0x01) for name in imports] + [(name, 0x0F) for name in exports]
    nsize = 16 if is64 else 12
    if not no_symtab:
        cmdsize = sum(map(len, cmds)) + 24
        symoff = header_len + cmdsize
        stroff = symoff + len(items) * nsize
        cmds.append(struct.pack(endian + "IIIIII", audit.LC_SYMTAB, 24, symoff, len(items), stroff, 1 + sum(len(s.encode()) + 1 for s, _ in items)))
        for name, ntype in items:
            si = len(strings)
            strings += name.encode() + b"\0"
            syms += struct.pack(endian + ("IBBhQ" if is64 else "IBBhI"), si, ntype, 1 if ntype == 0x0F else 0, 0, 0)
    all_commands = b"".join(cmds)
    hdr = struct.pack(endian + "IiiIIII", magic, cpu, 3, 2, len(cmds), len(all_commands), 0)
    if is64:
        hdr += struct.pack(endian + "I", 0)
    return hdr + all_commands + syms + strings


def fat(slices):
    count = len(slices)
    pos = 8 + count * 20
    records, content = [], bytearray()
    for arch, body in slices:
        pad = (-pos) % 4
        content += b"\0" * pad
        pos += pad
        records.append(struct.pack(">iiIII", audit.ARCH_CPUS[arch], 3, pos, len(body), 2))
        content += body
        pos += len(body)
    return struct.pack(">II", 0xCAFEBABE, count) + b"".join(records) + bytes(content)


class MachOAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, name, content):
        p = self.root / name
        p.write_bytes(content)
        return p

    def cli(self, *args):
        result = subprocess.run([sys.executable, str(Path(audit.__file__)), *map(str, args)],
                                check=False, text=True, capture_output=True)
        self.assertEqual(result.stderr, "", result.stderr)
        return result.returncode, json.loads(result.stdout)

    def test_i386_imports_dylib_and_exports(self):
        info = audit.parse(thin(imports=["_Movie", "_OpenMovieFile"], exports=["_local"],
                                dylibs=["/System/Library/Frameworks/QuickTime.framework/QuickTime"]), "i386")
        self.assertEqual(info["imports_nlist"], ["_Movie", "_OpenMovieFile"])
        self.assertEqual(info["exports_nlist"], ["_local"])
        self.assertEqual(info["dylibs"][0]["kind"], "load")

    def test_fat_selects_i386_not_ppc(self):
        data = fat([("ppc", thin("ppc", exports=["_wrong"], endian=">")),
                    ("i386", thin(imports=["_wanted"]))])
        self.assertEqual(audit.parse(data, "i386")["imports_nlist"], ["_wanted"])
        self.assertEqual(audit.parse(data, "ppc")["exports_nlist"], ["_wrong"])

    def test_x86_64_not_mistaken_for_i386(self):
        data = thin("x86_64", imports=["_api"])
        self.assertEqual(audit.parse(data, "x86_64")["bits"], 64)
        with self.assertRaisesRegex(audit.InvalidMachO, "architecture i386 absent"):
            audit.parse(data, "i386")

    def test_no_i386_in_fat(self):
        with self.assertRaisesRegex(audit.InvalidMachO, "i386 absent"):
            audit.parse(fat([("ppc", thin("ppc", endian=">"))]), "i386")

    def test_incorrect_fat_slice_arch_rejected(self):
        data = bytearray(fat([("i386", thin("ppc", endian=">"))]))
        with self.assertRaisesRegex(audit.InvalidMachO, "does not match"):
            audit.parse(bytes(data), "i386")

    def test_overlap_fat_slices_rejected(self):
        data = bytearray(fat([("i386", thin()), ("ppc", thin("ppc", endian=">"))]))
        struct.pack_into(">I", data, 8 + 20 + 8, 48)  # force second offset to overlap first
        with self.assertRaisesRegex(audit.InvalidMachO, "overlapping"):
            audit.parse(bytes(data), "i386")

    def test_malformed_magic(self):
        with self.assertRaisesRegex(audit.InvalidMachO, "not Mach-O"):
            audit.parse(b"RIFF" + b"\0" * 64, "i386")

    def test_truncated_load_command(self):
        data = bytearray(thin(imports=["_x"]))
        struct.pack_into("<I", data, 28 + 4, 1)  # bad cmdsize
        with self.assertRaisesRegex(audit.InvalidMachO, "invalid load command size"):
            audit.parse(bytes(data), "i386")

    def test_truncated_symbol_table(self):
        data = bytearray(thin(imports=["_x"]))
        struct.pack_into("<I", data, 28 + 8, len(data) + 1)
        with self.assertRaisesRegex(audit.InvalidMachO, "out-of-bounds"):
            audit.parse(bytes(data), "i386")

    def test_unterminated_dylib(self):
        data = bytearray(thin(dylibs=["Q"]))
        data[28 + 24:28 + 28] = b"XXXX"
        with self.assertRaisesRegex(audit.InvalidMachO, "unterminated"):
            audit.parse(bytes(data), "i386")

    def test_truncated_fat_table(self):
        with self.assertRaisesRegex(audit.InvalidMachO, "truncated FAT"):
            audit.parse(struct.pack(">II", 0xCAFEBABE, 2) + b"\0" * 20, "i386")

    def test_cli_resolved_names(self):
        consumer = self.write("consumer", thin(imports=["_QT", "_PA"]))
        qt = self.write("qt", thin(exports=["_QT"]))
        pa = self.write("pa", thin(exports=["_PA"]))
        code, result = self.cli("--consumer", consumer, "--provider", qt, "--provider", pa, "--strict")
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "STATIC_AUDIT")
        self.assertEqual(result["resolved_nlist"], ["_PA", "_QT"])
        self.assertEqual(result["unresolved_nlist"], [])
        self.assertEqual(len(result["consumer"]["sha256"]), 64)

    def test_cli_missing_symbol_never_passes_strict(self):
        consumer = self.write("consumer", thin(imports=["_NoImplementation"]))
        provider = self.write("provider", thin(exports=["_OtherSymbol"]))
        code, result = self.cli("--consumer", consumer, "--provider", provider, "--strict")
        self.assertEqual(code, 2)
        self.assertEqual(result["unresolved_nlist"], ["_NoImplementation"])

    def test_cli_no_provider_strict_inconclusive(self):
        consumer = self.write("consumer", thin(imports=["_QQ"]))
        code, result = self.cli("--consumer", consumer, "--strict")
        self.assertEqual(code, 3)
        self.assertEqual(result["status"], "STATIC_INCONCLUSIVE")

    def test_cli_no_symtab_strict_inconclusive(self):
        consumer = self.write("consumer", thin(no_symtab=True))
        provider = self.write("provider", thin(exports=["_abc"]))
        code, result = self.cli("--consumer", consumer, "--provider", provider, "--strict")
        self.assertEqual(code, 3)
        self.assertEqual(result["status"], "STATIC_INCONCLUSIVE")

    def test_cli_invalid_is_blocked(self):
        bad = self.write("bad", b"junk")
        code, result = self.cli("--consumer", bad)
        self.assertEqual(code, 3)
        self.assertEqual(result["status"], "BLOCKED")

    def test_arch_endian_and_fat64_tables(self):
        self.assertEqual(audit.parse(thin("ppc", endian=">"), "ppc")["bits"], 32)
        self.assertEqual(audit.parse(thin("arm64"), "arm64")["bits"], 64)

    def test_dyld_info_flag_not_hidden(self):
        info = audit.parse(thin(dyld_info=True), "i386")
        self.assertTrue(info["has_dyld_info"])

    def test_reject_ambiguous_duplicate_arch(self):
        b = fat([("i386", thin()), ("i386", thin())])
        with self.assertRaisesRegex(audit.InvalidMachO, "ambiguous"):
            audit.parse(b, "i386")


if __name__ == "__main__":
    unittest.main()
