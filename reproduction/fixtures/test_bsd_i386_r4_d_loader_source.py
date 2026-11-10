#!/usr/bin/env python3
"""Read-only structural guard for the opt-in i386 mmap diagnostics.

Run from repository root:
python3 -m unittest discover -s reproduction/fixtures -p 'test_bsd_i386_r4_d_loader_source.py' -v
"""
from pathlib import Path
import re
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "src/startup/mldr/loader.c"


class MldrI386MmapDiagnostics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_cmake_option_is_off_by_default_and_scoped_to_mldr32(self):
        cmake = (SOURCE.parent / "CMakeLists.txt").read_text(encoding="utf-8")
        declaration = 'option(D4RLING_MLDR_I386_MMAP_DIAG "Enable opt-in mmap failure diagnostics in mldr32 only" OFF)'
        self.assertEqual(cmake.count(declaration), 1)
        target = "target_compile_definitions(mldr32 PRIVATE D4RLING_MLDR_I386_MMAP_DIAG)"
        self.assertEqual(cmake.count(target), 1)
        self.assertNotIn("target_compile_definitions(mldr PRIVATE D4RLING_MLDR_I386_MMAP_DIAG)", cmake)
        self.assertLess(cmake.index("if (BUILD_TARGET_32BIT)"), cmake.index(target))
        self.assertLess(cmake.index("if (D4RLING_MLDR_I386_MMAP_DIAG)"), cmake.index(target))
        self.assertLess(cmake.index("add_executable(mldr32"), cmake.index(target))

    def test_template_undefines_diagnostic_between_64_and_32_bit_passes(self):
        mldr = (SOURCE.parent / "mldr.c").read_text(encoding="utf-8")
        self.assertIn('#define GEN_64BIT\\n#include "loader.c"', mldr)
        self.assertIn('#define GEN_32BIT\\n#include "loader.c"', mldr)
        self.assertEqual(self.source.count("#undef MLDR_MMAP_DIAG"), 1)
        self.assertLess(
            self.source.rindex("#undef MAP_EXTRA"),
            self.source.rindex("#undef MLDR_MMAP_DIAG"),
        )

    def test_guard_requires_both_i386_and_opt_in(self):
        self.assertIn(
            "#if defined(GEN_32BIT) && defined(D4RLING_MLDR_I386_MMAP_DIAG)",
            self.source,
        )
        self.assertIn(
            "#define MLDR_MMAP_DIAG(branch, seg, address, length, slide, flags) ((void)0)",
            self.source,
        )

    def test_each_failure_path_has_its_own_diagnostic(self):
        branches = {
            "anonymous-slide": "addr, seg->vmsize, slide, MAP_ANONYMOUS | MAP_PRIVATE | MAP_FIXED_NOREPLACE",
            "anonymous-tail": "PAGE_ALIGN(seg->vmaddr + seg->vmsize - size), PAGE_ROUNDUP(size), slide, MAP_ANONYMOUS | MAP_PRIVATE | MAP_FIXED_NOREPLACE",
            "file-backed": "addr, seg->filesize, slide, flag | MAP_PRIVATE",
        }
        for name, args in branches.items():
            with self.subTest(branch=name):
                call = 'MLDR_MMAP_DIAG("' + name + '", seg, ' + args + ');'
                self.assertEqual(self.source.count(call), 1)
                after = self.source.split(call, 1)[1]
                self.assertRegex(after[:260], r'fprintf\(stderr, "Cannot mmap segment')
        self.assertEqual(len(re.findall(r'MLDR_MMAP_DIAG\("', self.source)), 3)

    def test_legacy_error_message_is_preserved(self):
        legacy = 'fprintf(stderr, "Cannot mmap segment %s at %p: %s\\n", seg->segname, (void*)(uintptr_t)seg->vmaddr, strerror(errno));'
        self.assertEqual(self.source.count(legacy), 3)

    def test_diagnostic_format_is_newline_terminated(self):
        macro = self.source.split(
            "#if defined(GEN_32BIT) && defined(D4RLING_MLDR_I386_MMAP_DIAG)", 1
        )[1].split("#else", 1)[0]
        escaped_newline = chr(92) + "n"
        self.assertIn('errno=%d' + escaped_newline + '",', macro)
        self.assertNotIn('errno=%d' + chr(92) + escaped_newline + '",', macro)

    def test_diagnostic_is_only_on_failure_paths(self):
        for branch in ("anonymous-slide", "anonymous-tail", "file-backed"):
            call = 'MLDR_MMAP_DIAG("' + branch + '"'
            before = self.source.split(call, 1)[0]
            self.assertIn("if (rv == (void*)MAP_FAILED)", before[-750:])
        self.assertNotIn(
            "D4RLING_MLDR_I386_MMAP_DIAG",
            self.source.split('#include "loader.h"', 1)[0],
        )

    def test_no_mapping_policy_changes_in_diagnostic(self):
        macro = self.source.split("#if defined(GEN_32BIT) && defined(D4RLING_MLDR_I386_MMAP_DIAG)", 1)[1].split("#endif", 1)[0]
        self.assertIn("fprintf(stderr", macro)
        self.assertNotIn("compatible_mmap(", macro)
        self.assertNotIn("mprotect(", macro)


if __name__ == "__main__":
    unittest.main()
