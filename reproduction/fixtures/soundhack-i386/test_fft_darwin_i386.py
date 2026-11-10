#!/usr/bin/env python3
"""SH08: target/ABI/symbol checks, including negative controls."""
# Copyright (C) 2026 D4rling contributors. GPL-3.0-or-later.

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import fft_darwin_i386 as sh08
from fft_host_probe import git_blob_sha, Inconclusive

FAKE_C = b"void bogus(void) {}\n"
FAKE_H = b"void bogus(void);\n"
FAKE_IMAGE = {
    "arch": "i386", "bits": 32, "filetype": 1, "has_symtab": True,
    "has_dyld_info": False, "two_level_namespace": False, "dylibs": [],
    "exports_nlist": sorted(sh08.EXPECTED_DEFINITIONS),
    "imports_nlist": sorted(sh08.EXPECTED_UNDEFINED),
    "symbol_caveats": []
}


class Sh08Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-sh08-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def put_sources(self, c=FAKE_C, h=FAKE_H):
        (self.directory / "FFT.c").write_bytes(c)
        (self.directory / "FFT.h").write_bytes(h)
        return self.directory

    def test_expected_target_model(self):
        fields = "\n".join(f"#define {name} {value}" for name, value in sh08.EXPECTED_MACROS.items())
        self.assertEqual(sh08.check_macros(fields), [])

    def test_missing_i386_is_rejected(self):
        fields = "\n".join(f"#define {name} {value}" for name, value in sh08.EXPECTED_MACROS.items()
                           if name != "__i386__")
        self.assertTrue(any("__i386__" in p for p in sh08.check_macros(fields)))

    def test_host_long_64_bit_is_rejected(self):
        fields = "\n".join(f"#define {name} {value if name != '__SIZEOF_LONG__' else '8'}"
                           for name, value in sh08.EXPECTED_MACROS.items())
        self.assertTrue(any("__SIZEOF_LONG__" in p for p in sh08.check_macros(fields)))

    def test_lp64_prevents_target_pass(self):
        fields = "\n".join(f"#define {name} {value}" for name, value in sh08.EXPECTED_MACROS.items())
        self.assertTrue(any("LP64" in p for p in sh08.check_macros(fields + "\n#define __LP64__ 1")))

    def test_invalid_object_is_inconclusive(self):
        with self.assertRaises(Inconclusive):
            sh08.check_object(b"garbage")

    def test_empty_object_is_inconclusive(self):
        with self.assertRaises(Inconclusive):
            sh08.check_object(b"")

    def test_oversized_object_is_inconclusive(self):
        with self.assertRaises(Inconclusive):
            sh08.check_object(b"z" * (sh08.MAX_OBJECT_BYTES + 1))

    def test_wrong_arch_object_is_inconclusive(self):
        with self.assertRaises(Inconclusive):
            sh08.check_object(b"\xcf\xfa\xed\xfe" + b"\x00" * 32)

    def test_defined_symbol_regression_is_detected(self):
        image = dict(FAKE_IMAGE, exports_nlist=["_FFT", "_RealFFT"])
        with patch.object(sh08, "parse_macho", return_value=image):
            result = sh08.check_object(b"placeholder")
        self.assertTrue(result["problems"])
        self.assertIn("defined symbol mismatch", result["problems"][0])

    def test_new_undefined_dependency_is_detected(self):
        image = dict(FAKE_IMAGE, imports_nlist=sorted(sh08.EXPECTED_UNDEFINED | {"_made_up_import"}))
        with patch.object(sh08, "parse_macho", return_value=image):
            result = sh08.check_object(b"placeholder")
        self.assertTrue(any("undefined symbol mismatch" in p for p in result["problems"]))

    def test_wrong_filetype_is_detected(self):
        image = dict(FAKE_IMAGE, filetype=2)
        with patch.object(sh08, "parse_macho", return_value=image):
            result = sh08.check_object(b"placeholder")
        self.assertTrue(any("filetype" in p for p in result["problems"]))

    def test_caveats_are_not_ignored(self):
        image = dict(FAKE_IMAGE, symbol_caveats=["_foo: unsupported type"])
        with patch.object(sh08, "parse_macho", return_value=image):
            result = sh08.check_object(b"placeholder")
        self.assertTrue(any("symbol caveats" in p for p in result["problems"]))

    def test_no_source_returns_inconclusive_json(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = sh08.main(["--source-dir", str(self.directory)])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(output.getvalue())["status"], "INCONCLUSIVE")

    def test_mutated_upstream_source_fails_before_compilation(self):
        self.put_sources()
        with self.assertRaises(Inconclusive):
            sh08.qualify(self.directory)

    def test_missing_clang_is_inconclusive(self):
        self.assertRaises(Inconclusive, sh08.installed_clang, "definitely-not-clang-sh08")

    def test_wrong_target_model_aborts_before_compile(self):
        # Pin verification is mocked only to isolate the target ABI gate.
        self.put_sources()
        with (patch.object(sh08, "require_pinned"),
              patch.object(sh08, "installed_clang", return_value="clang"),
              patch.object(sh08, "invoke", return_value="#define __SIZEOF_POINTER__ 8") as called):
            result = sh08.qualify(self.directory)
        self.assertEqual(result["status"], "TARGET_CONTRACT_FAIL")
        self.assertEqual(called.call_count, 1)

    @unittest.skipUnless(shutil.which("clang") and os.environ.get("SOUNDHACK_MATH_DIR"),
                         "Clang and pinned SoundHack Math source required")
    def test_real_original_source_macho_i386(self):
        source = Path(os.environ["SOUNDHACK_MATH_DIR"])
        original_c, original_h = (source / "FFT.c").read_bytes(), (source / "FFT.h").read_bytes()
        self.assertEqual(git_blob_sha(original_c), sh08.SOURCE_SHA)
        self.assertEqual(git_blob_sha(original_h), sh08.HEADER_SHA)
        result = sh08.qualify(source)
        self.assertEqual(result["status"], "TARGET_OBJECT_PASS")
        self.assertEqual((result["object"]["bits"], result["object"]["filetype"]), (32, 1))
        self.assertEqual(result["object"]["defined_nlist"], sorted(sh08.EXPECTED_DEFINITIONS))
        self.assertEqual(result["object"]["undefined_nlist"], sorted(sh08.EXPECTED_UNDEFINED))
        self.assertEqual((source / "FFT.c").read_bytes(), original_c)
        self.assertEqual((source / "FFT.h").read_bytes(), original_h)

    @unittest.skipUnless(shutil.which("clang") and os.environ.get("SOUNDHACK_MATH_DIR"),
                         "Clang and pinned SoundHack Math source required")
    def test_exclusive_object_save_and_no_overwrite(self):
        source = Path(os.environ["SOUNDHACK_MATH_DIR"])
        output = self.directory / "saved.macho"
        result = sh08.qualify(source, output=output)
        self.assertEqual(result["status"], "TARGET_OBJECT_PASS")
        data = output.read_bytes()
        self.assertEqual(len(data), result["object"]["bytes"])
        self.assertEqual(sh08.check_object(data)["problems"], [])
        with self.assertRaises(Inconclusive):
            sh08.qualify(source, output=output)
        self.assertEqual(output.read_bytes(), data)

    @unittest.skipUnless(shutil.which("clang") and os.environ.get("SOUNDHACK_MATH_DIR"),
                         "Clang and pinned SoundHack Math source required")
    def test_symlink_is_never_overwritten(self):
        source = Path(os.environ["SOUNDHACK_MATH_DIR"])
        protected = self.directory / "protected.txt"
        protected.write_text("do not touch\n", encoding="ascii")
        linked = self.directory / "linked.macho"
        linked.symlink_to(protected)
        with self.assertRaises(Inconclusive):
            sh08.qualify(source, output=linked)
        self.assertEqual(protected.read_text(encoding="ascii"), "do not touch\n")
        self.assertTrue(linked.is_symlink())

    @unittest.skipUnless(shutil.which("clang") and os.environ.get("SOUNDHACK_MATH_DIR"),
                         "Clang and pinned SoundHack Math source required")
    def test_mutated_original_header_fails_closed(self):
        original = Path(os.environ["SOUNDHACK_MATH_DIR"])
        c = (original / "FFT.c").read_bytes()
        h = (original / "FFT.h").read_bytes()
        self.put_sources(c, h + b"\n/* mutation */\n")
        with self.assertRaises(Inconclusive):
            sh08.qualify(self.directory)


if __name__ == "__main__":
    unittest.main()
