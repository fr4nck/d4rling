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
         dyld_info=False, two_level=False, install_name=None):
    cpu = audit.ARCH_CPUS[arch]
    is64 = arch in ("x86_64", "ppc64", "arm64")
    magic = 0xfeedfacf if is64 else 0xfeedface
    header_len = 32 if is64 else 28
    cmds = []
    for name, cmd in ([(install_name, 0xD)] if install_name else []) + [(n, 0xC) for n in dylibs]:
        raw = name.encode() + b"\0"
        size = (24 + len(raw) + 3) & ~3
        cmds.append(struct.pack(endian + "IIIIII", cmd, size, 24, 0, 0, 0) + raw + b"\0" * (size - 24 - len(raw)))
    if dyld_info:
        cmds.append(struct.pack(endian + "II", audit.LC_DYLD_INFO_ONLY, 8))
    syms = b""
    strings = b"\0"
    # import tuples: (symbol, library ordinal, weak_import[, n_value])
    items = [((sym if isinstance(sym, str) else sym[0]), 0x01,
              (0 if isinstance(sym, str) else (sym[1] << 8) | (0x40 if sym[2] else 0)),
              (0 if isinstance(sym, str) or len(sym) < 4 else sym[3])) for sym in imports]
    items += [(name, 0x0F, 0, 0) for name in exports]
    nsize = 16 if is64 else 12
    if not no_symtab:
        cmdsize = sum(map(len, cmds)) + 24
        symoff = header_len + cmdsize
        stroff = symoff + len(items) * nsize
        cmds.append(struct.pack(endian + "IIIIII", audit.LC_SYMTAB, 24, symoff, len(items), stroff, 1 + sum(len(name.encode()) + 1 for name, _, _, _ in items)))
        for name, ntype, desc, value in items:
            si = len(strings)
            strings += name.encode() + b"\0"
            syms += struct.pack(endian + ("IBBHQ" if is64 else "IBBHI"), si, ntype, 1 if ntype == 0x0F else 0, desc, value)
    all_commands = b"".join(cmds)
    hdr = struct.pack(endian + "IiiIIII", magic, cpu, 3, 6 if install_name else 2, len(cmds), len(all_commands), audit.MH_TWOLEVEL if two_level else 0)
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

    def test_two_level_ordinal_matched_to_correct_install_name(self):
        consumer = self.write("consumer", thin(imports=[("_Play", 1, False)],
                                  dylibs=["/A/Correct.dylib"], two_level=True))
        right = self.write("right", thin(exports=["_Play"], install_name="/A/Correct.dylib"))
        code, out = self.cli("--consumer", consumer, "--provider", right, "--strict")
        self.assertEqual(code, 0)
        self.assertEqual(out["resolved_nlist"], ["_Play"])
        self.assertEqual(out["consumer"]["imports_detail"][0]["library_name"], "/A/Correct.dylib")
        self.assertEqual(out["consumer"]["imports_detail"][0]["lookup"], "library")

    def test_two_level_wrong_library_does_not_false_pass_by_name(self):
        consumer = self.write("consumer", thin(imports=[("_Play", 1, False)],
                                  dylibs=["/A/Expected.dylib"], two_level=True))
        wrong = self.write("wrong", thin(exports=["_Play"], install_name="/B/Other.dylib"))
        code, out = self.cli("--consumer", consumer, "--provider", wrong, "--strict")
        self.assertEqual(code, 2)
        self.assertEqual(out["resolved_nlist"], [])
        self.assertEqual(out["unresolved_nlist_detail"], [{"name": "_Play", "expected_library": "/A/Expected.dylib"}])

    def test_two_level_provider_without_id_is_inconclusive(self):
        consumer = self.write("consumer", thin(imports=[("_Play", 1, False)],
                                  dylibs=["/A/Correct.dylib"], two_level=True))
        unnamed = self.write("unnamed", thin(exports=["_Play"]))
        code, out = self.cli("--consumer", consumer, "--provider", unnamed, "--strict")
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "STATIC_INCONCLUSIVE")
        self.assertEqual(out["unresolved_nlist"], [])

    def test_two_level_weak_missing_is_optional_not_successful_binding(self):
        consumer = self.write("consumer", thin(imports=[("_Optional", 1, True)],
                                  dylibs=["/A/Fwk.dylib"], two_level=True))
        provider = self.write("provider", thin(exports=["_Different"], install_name="/A/Fwk.dylib"))
        code, out = self.cli("--consumer", consumer, "--provider", provider, "--strict")
        self.assertEqual(code, 0)
        self.assertEqual(out["unresolved_nlist"], [])
        self.assertEqual(out["optional_missing_nlist"][0]["name"], "_Optional")

    def test_id_command_does_not_change_import_ordinal(self):
        # A dylib's LC_ID_DYLIB is not an imported-library ordinal.
        data = thin(imports=[("_Dep", 1, False)], install_name="/Self.dylib",
                    dylibs=["/Dep.dylib"], two_level=True)
        info = audit.parse(data, "i386")
        self.assertEqual(info["install_name"], "/Self.dylib")
        self.assertEqual(info["imports_detail"][0]["library_name"], "/Dep.dylib")

    def test_install_name_illegal_in_executable_rejected(self):
        data = bytearray(thin(install_name="/Fake.dylib"))
        struct.pack_into("<I", data, 12, 2)  # MH_EXECUTE with LC_ID_DYLIB
        with self.assertRaisesRegex(audit.InvalidMachO, "non-dylib image"):
            audit.parse(bytes(data), "i386")

    def test_two_level_ordinal_two_is_second_load_order(self):
        info = audit.parse(thin(imports=[("_Other", 2, False)], two_level=True,
                                dylibs=["/First", "/Second"]), "i386")
        self.assertEqual(info["imports_detail"][0]["library_name"], "/Second")

    def test_duplicate_id_rejected(self):
        data = bytearray(thin(install_name="/Self.dylib"))
        # Reuse ID load command, extending header table with a duplicate.
        cmd_size = struct.unpack_from("<I", data, 32)[0]
        cmd = bytes(data[28:28 + cmd_size])
        struct.pack_into("<I", data, 16, 2)
        struct.pack_into("<I", data, 20, cmd_size * 2)
        data[28 + cmd_size:28 + cmd_size] = cmd
        with self.assertRaisesRegex(audit.InvalidMachO, "duplicate dylib install name"):
            audit.parse(bytes(data), "i386")

    def test_invalid_two_level_library_ordinal_rejected(self):
        with self.assertRaisesRegex(audit.InvalidMachO, "invalid library ordinal"):
            audit.parse(thin(imports=[("_X", 2, False)], dylibs=["/A/One"], two_level=True), "i386")

    def test_special_ordinal_dynamic_lookup_is_not_assigned_arbitrary_provider(self):
        consumer = self.write("consumer", thin(imports=[("_DynamicallyLookedUp", 0xFE, False)], two_level=True))
        provider = self.write("provider", thin(exports=["_DynamicallyLookedUp"], install_name="/A/Other"))
        code, out = self.cli("--consumer", consumer, "--provider", provider, "--strict")
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "STATIC_INCONCLUSIVE")
        self.assertEqual(out["consumer"]["imports_detail"][0]["lookup"], "dynamic_lookup")

    def test_common_symbol_does_not_get_strict_pass_by_name(self):
        consumer = self.write("consumer", thin(imports=[("_Common", 0, False, 8)]))
        provider = self.write("provider", thin(exports=["_Common"]))
        code, out = self.cli("--consumer", consumer, "--provider", provider, "--strict")
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "STATIC_INCONCLUSIVE")

    def test_indirect_export_is_not_real_definition(self):
        raw = bytearray(thin(exports=["_Alias"]))
        # Locate the nlist table in the LC_SYMTAB load command.
        symoff = struct.unpack_from("<I", raw, 28 + 8)[0]
        raw[symoff + 4] = 0x0B  # N_EXT | N_INDR
        provider = self.write("provider", bytes(raw))
        self.assertEqual(audit.inspect(provider, "i386")["exports_nlist"], [])
        self.assertTrue(audit.inspect(provider, "i386")["symbol_caveats"])
        consumer = self.write("consumer", thin(imports=["_Alias"]))
        code, out = self.cli("--consumer", consumer, "--provider", provider, "--strict")
        self.assertEqual(code, 3)

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
