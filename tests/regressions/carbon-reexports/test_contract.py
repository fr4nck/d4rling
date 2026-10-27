#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Host-only regression tests for Carbon-to-HIToolbox reexport contracts."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import check_contract as contract


REPO = Path(__file__).resolve().parents[3]


class CarbonReexportContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="carbon-reexport-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for relative in contract.FILES.values():
            original = REPO / relative
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(original.read_bytes())

    def change(self, key: str, old: str, new: str):
        path = self.root / contract.FILES[key]
        body = path.read_text(encoding="utf-8")
        self.assertIn(old, body)
        path.write_text(body.replace(old, new), encoding="utf-8")

    def append(self, key: str, text: str):
        path = self.root / contract.FILES[key]
        with path.open("a", encoding="utf-8") as stream:
            stream.write(text)

    def test_current_sources_match_all_ten_contracts(self):
        result = contract.inspect(self.root)
        self.assertTrue(result["all_checks_pass"], result["checks"])
        self.assertEqual(len(result["checks"]), 10)
        self.assertEqual(result["kind"], "source_only_contract")

    def test_setter_signature_is_bytecount_in_header_and_implementation(self):
        result = contract.inspect(self.root)
        self.assertTrue(result["checks"]["header_setter_uses_bytecount"])
        self.assertTrue(result["checks"]["hitoolbox_implements_matching_setter"])

    def test_legacy_setter_stub_is_rejected(self):
        self.append("carbon_impl", """
OSStatus SetEventParameter(EventRef e, EventParamName n,
                           EventParamType t, UInt32 s, const void* d)
{ return 0; }
""")
        result = contract.inspect(self.root)
        self.assertFalse(result["checks"]["carbon_omits_duplicate_setter"])

    def test_legacy_target_stub_is_rejected(self):
        self.append("carbon_impl", """
EventTargetRef GetApplicationEventTarget(void)
{ return (EventTargetRef)0; }
""")
        result = contract.inspect(self.root)
        self.assertFalse(result["checks"]["carbon_omits_duplicate_application_target"])

    def test_multiple_setter_stubs_still_rejected(self):
        self.append("carbon_impl", """
OSStatus SetEventParameter(EventRef e, EventParamName n,
                           EventParamType t, UInt32 s, const void* d) { return 0; }
OSStatus SetEventParameter(EventRef e, EventParamName n,
                           EventParamType t, ByteCount s, const void* d) { return 0; }
""")
        result = contract.inspect(self.root)
        self.assertFalse(result["checks"]["carbon_omits_duplicate_setter"])

    def test_wrong_header_bytecount_detected(self):
        self.change("event_header", "ByteCount inSize", "UInt32 inSize")
        self.assertFalse(contract.inspect(self.root)["checks"]["header_setter_uses_bytecount"])

    def test_wrong_implementation_bytecount_detected(self):
        self.change("event_impl", "ByteCount inSize", "UInt32 inSize")
        self.assertFalse(contract.inspect(self.root)["checks"]["hitoolbox_implements_matching_setter"])

    def test_setter_must_not_become_a_noop(self):
        self.change("event_impl", "OSStatus status = AllocateParameter(", "OSStatus status = NoopParameter(")
        self.assertFalse(contract.inspect(self.root)["checks"]["hitoolbox_setter_stores_parameters"])

    def test_application_target_must_not_return_null(self):
        self.change("event_impl", "return &applicationTarget;", "return NULL;")
        self.assertFalse(contract.inspect(self.root)["checks"]["hitoolbox_application_target_is_nonnull"])

    def test_missing_application_target_header_detected(self):
        self.change("event_header", "EventTargetRef GetApplicationEventTarget(void);",
                    "EventTargetRef GetOtherEventTarget(void);")
        self.assertFalse(contract.inspect(self.root)["checks"]["hitoolbox_has_application_target_declaration"])

    def test_missing_umbrella_header_detected(self):
        self.change("carbon_impl", "#include <Carbon/Carbon.h>", "#include <Carbon/NoSuchHeader.h>")
        self.assertFalse(contract.inspect(self.root)["checks"]["umbrella_carbon_includes_public_header"])

    def test_missing_reexport_detected(self):
        self.change("carbon_cmake", "reexport(Carbon HIToolbox", "reexport(Carbon Placeholder")
        self.assertFalse(contract.inspect(self.root)["checks"]["carbon_reexports_hitoolbox"])

    def test_missing_hitoolbox_source_detected(self):
        self.change("hitoolbox_cmake", "src/CarbonEventsCore.c", "src/AbsentEventCore.c")
        self.assertFalse(contract.inspect(self.root)["checks"]["hitoolbox_builds_event_core"])

    def test_missing_source_is_failure_not_skip(self):
        (self.root / contract.FILES["event_impl"]).unlink()
        with self.assertRaisesRegex(ValueError, "missing required source"):
            contract.inspect(self.root)

    def test_flat_signature_parser_rejects_duplicate_declarations(self):
        body = """OSStatus SetEventParameter(EventRef e, ByteCount s);
OSStatus SetEventParameter(EventRef e, ByteCount s);
"""
        self.assertIsNone(contract.signature(body, "OSStatus", "SetEventParameter", ";"))

    def test_cli_does_not_overwrite_existing_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contract.json"
            path.write_text("protected", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-B", str(Path(__file__).with_name("check_contract.py")),
                 "--checkout", str(self.root), "--output", str(path)],
                capture_output=True, text=True, check=False
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(path.read_text(encoding="utf-8"), "protected")


if __name__ == "__main__":
    unittest.main(verbosity=2)
