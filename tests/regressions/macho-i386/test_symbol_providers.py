#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Host regression for the i386 symbol-provider inventory (no LLVM needed)."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import symbol_providers as scan


class SymbolProviderTests(unittest.TestCase):
    def test_extracts_quoted_undefined_symbols(self):
        error = '''Undefined symbols for architecture i386:
  "_malloc", referenced from:
      _caller in archive.a(file.o)
  "__libkernel_functions", referenced from:
      _init in archive.a(init.o)
  "_malloc", referenced from:
      _another in archive.a(other.o)
ld: symbol(s) not found for architecture i386
'''
        self.assertEqual(scan.parse_undefined(error), {"_malloc", "__libkernel_functions"})

    def test_does_not_infer_symbols_from_plain_text(self):
        self.assertEqual(scan.parse_undefined("_malloc missing, _free missing"), set())

    def test_definition_parser_rejects_undefined_and_local(self):
        value = '''lib.a(member.o):
00000000 T _malloc
00000000 W _weak_func
         U _free
00000000 t _not_global
00000000 D __libkernel_functions
'''
        self.assertEqual(scan.parse_definitions(value),
                         {"_malloc", "_weak_func", "__libkernel_functions"})

    def test_discover_only_relevant_artifact_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "src"
            base.mkdir()
            for name in ("libmalloc.a", "libsystem_c.dylib", "unrelated.a", "readme.txt"):
                (base / name).write_bytes(b"stub")
            names = [path.name for path in scan.discover_candidates(Path(tmp))]
            self.assertEqual(names, ["libmalloc.a", "libsystem_c.dylib"])

    def test_missing_build_tree_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                scan.discover_candidates(Path(tmp))

    def test_architecture_filter_rejects_x86_64_only(self):
        output = subprocess.CompletedProcess(args=[], returncode=0, stdout="x86_64\n", stderr="")
        with patch.object(scan, "_run", return_value=output) as fake:
            definitions, status = scan._definitions_for_i386(
                Path("libsystem_c.dylib"), "lipo", "nm", 2
            )
        self.assertIsNone(definitions)
        self.assertEqual(status, "no-i386-slice")
        fake.assert_called_once()

    def test_single_architecture_direct_nm(self):
        responses = [
            subprocess.CompletedProcess([], 0, "i386\n", ""),
            subprocess.CompletedProcess([], 0, "0000 T _malloc\n", ""),
        ]
        with patch.object(scan, "_run", side_effect=responses) as fake:
            definitions, status = scan._definitions_for_i386(Path("libmalloc.a"), "lipo", "nm", 2)
        self.assertEqual((definitions, status), ({"_malloc"}, "scanned"))
        self.assertEqual(fake.call_count, 2)

    def test_fat_library_is_thinned_before_nm(self):
        responses = [
            subprocess.CompletedProcess([], 0, "i386 x86_64\n", ""),
            subprocess.CompletedProcess([], 0, "", ""),
            subprocess.CompletedProcess([], 0, "0000 T _free\n", ""),
        ]
        with patch.object(scan, "_run", side_effect=responses) as fake:
            definitions, status = scan._definitions_for_i386(Path("libmalloc.dylib"), "lipo", "nm", 2)
        self.assertEqual((definitions, status), ({"_free"}, "scanned"))
        self.assertEqual(fake.call_count, 3)
        self.assertIn("-thin", fake.call_args_list[1].args[0])

    def test_inventory_does_not_confuse_candidate_with_link_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src/libmalloc.a").write_bytes(b"stub")
            linker = root / "link.log"
            linker.write_text('  "_malloc", referenced from:\n      _test in test.o\n')
            with patch.object(scan, "_definitions_for_i386", return_value=({"_malloc"}, "scanned")):
                data = scan.inventory([linker], root)
            self.assertEqual(data["providers"], {"_malloc": ["src/libmalloc.a"]})
            self.assertEqual(data["scan_counts"]["scanned"], 1)
            self.assertIn("not proof", data["qualifier"])
            self.assertEqual(data["source_logs"][0]["name"], "link.log")
            self.assertEqual(len(data["source_logs"][0]["sha256"]), 64)

    def test_inventory_unresolved_classification_and_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            for name in ("libmalloc.a", "libsystem_c.dylib"):
                (root / "src" / name).write_bytes(b"stub")
            linker = root / "link.log"
            linker.write_text('"_free", referenced from:\n')
            with patch.object(scan, "_definitions_for_i386", return_value=(set(), "scanned")):
                data = scan.inventory([linker], root, max_candidates=1)
            self.assertEqual(data["not_found_in_scanned_candidates"], ["_free"])
            self.assertEqual(data["candidates_found"], 2)
            self.assertTrue(data["truncated"])

    def test_rejects_empty_linker_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            linker = root / "link.log"
            linker.write_text("no errors here")
            with self.assertRaises(ValueError):
                scan.inventory([linker], root)

    def test_invalid_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            linker = root / "link.log"
            linker.write_text('"_free", referenced from:\n')
            for options in ({"max_candidates": 0}, {"timeout": 0}):
                with self.assertRaises(ValueError):
                    scan.inventory([linker], root, **options)

    def test_json_stably_serializable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            linker = root / "link.log"
            linker.write_text('"_free", referenced from:\n')
            result = scan.inventory([linker], root)
            self.assertEqual(json.loads(json.dumps(result))["architecture"], "i386")
            self.assertEqual(result["not_found_in_scanned_candidates"], ["_free"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
