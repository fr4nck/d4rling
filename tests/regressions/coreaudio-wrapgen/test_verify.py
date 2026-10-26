#!/usr/bin/env python3
"""Self-contained mock tests; no Darling, JACK, PulseAudio, or network needed."""

import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

MODULE_FILE = Path(__file__).with_name("verify.py")
spec = importlib.util.spec_from_file_location("ca10_verify", MODULE_FILE)
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        samples = {
            "cmake/wrap_elf.cmake": """function(wrap_elf name elfname)
add_custom_command(
 OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/${name}.c
 COMMAND wrapgen ${elfname} ${name}.c ${name}_vars.h
)
endfunction(wrap_elf)
""",
            "src/libelfloader/wrapgen/wrapgen.cpp": """if (!vars.empty()) {
 std::ofstream outputHeader(argv[3]);
}
""",
            "src/CoreAudio/CMakeLists.txt": "wrap_elf(pulse libpulse.so)\n",
        }
        for path, contents in samples.items():
            dest = self.root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(contents, encoding="utf-8")

    def test_contract_allows_optional_header(self):
        self.assertEqual(verify.verify_contract(self.root)[0], "PASS")

    def test_contract_rejects_required_header(self):
        cmake = self.root / "cmake/wrap_elf.cmake"
        cmake.write_text(cmake.read_text().replace(
            "OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/${name}.c",
            "OUTPUT ${name}.c ${name}_vars.h"), encoding="utf-8")
        self.assertEqual(verify.verify_contract(self.root)[0], "FAIL")

    def test_contract_rejects_unconditional_header(self):
        generator = self.root / "src/libelfloader/wrapgen/wrapgen.cpp"
        generator.write_text("std::ofstream outputHeader(argv[3]);\n", encoding="utf-8")
        self.assertEqual(verify.verify_contract(self.root)[0], "FAIL")


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / verify.SOURCE_RELATIVE
        self.header = self.root / verify.HEADER_RELATIVE
        self.object = self.root / verify.OBJECT_RELATIVE
        self.source.parent.mkdir(parents=True)
        self.object.parent.mkdir(parents=True)
        self.source.write_text(
            '#include <elfcalls.h>\nvoid* foo(){ __asm__(".symbol_resolver _foo"); }\n'
            'asm("___elfname: libpulse.so.0");\n', encoding="utf-8")
        self.object.write_bytes(struct.pack("<IIII", 0xFEEDFACF, 0x01000007, 3, 1))

    def test_valid_source(self):
        self.assertEqual(verify.verify_generated_source(self.source)[0], "PASS")

    def test_optional_header_absent(self):
        self.assertEqual(verify.verify_optional_header(self.header, self.source)[0],
                         "SKIP_OPTIONAL")

    def test_optional_header_present(self):
        self.header.write_text("#pragma once\n", encoding="utf-8")
        self.assertEqual(verify.verify_optional_header(self.header, self.source)[0],
                         "PASS")

    def test_missing_header_cannot_be_referenced(self):
        self.source.write_text(self.source.read_text() + '#include "pulse_vars.h"\n')
        self.assertEqual(verify.verify_optional_header(self.header, self.source)[0],
                         "FAIL")

    def test_empty_generated_source(self):
        self.source.write_text("", encoding="utf-8")
        self.assertEqual(verify.verify_generated_source(self.source)[0], "FAIL")

    def test_valid_macho(self):
        self.assertEqual(verify.verify_macho_object(self.object)[0], "PASS")

    def test_reject_elf(self):
        self.object.write_bytes(b"\x7fELF" + b"\0" * 12)
        self.assertEqual(verify.verify_macho_object(self.object)[0], "FAIL")

    def test_reject_other_cpu(self):
        self.object.write_bytes(struct.pack("<IIII", 0xFEEDFACF, 7, 3, 1))
        self.assertEqual(verify.verify_macho_object(self.object)[0], "FAIL")

    def test_reject_non_object(self):
        self.object.write_bytes(struct.pack("<IIII", 0xFEEDFACF, 0x01000007, 3, 6))
        self.assertEqual(verify.verify_macho_object(self.object)[0], "FAIL")

    def test_reject_missing_object(self):
        self.object.unlink()
        self.assertEqual(verify.verify_macho_object(self.object)[0], "FAIL")


if __name__ == "__main__":
    unittest.main()
