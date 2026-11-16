#!/usr/bin/env python3
"""SH19 contract tests: independent adversarial inputs, no proprietary binaries."""

from __future__ import annotations

import hashlib
from pathlib import Path
import plistlib
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import sh19_app_gate as gate


class AppGateTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(prefix="sh19-fixture-")
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.app = self.root / "SoundHack.app"
        self.bin = self.app / "Contents" / "MacOS" / "SoundHack"
        self.bin.parent.mkdir(parents=True)
        self.bin.write_bytes(b"SYNTHETIC_MACHO_NOT_VENDOR_BYTES")
        self.plist = self.app / "Contents" / "Info.plist"
        self.plist.write_bytes(plistlib.dumps({"CFBundleExecutable": "SoundHack", "CFBundleIdentifier": "test.fixture"}))
        self.sha = hashlib.sha256(self.bin.read_bytes()).hexdigest()
        self.sysroot = self.root / "prefix"
        (self.sysroot / "usr" / "lib").mkdir(parents=True)
        (self.sysroot / "usr" / "lib" / "libSystem.B.dylib").write_bytes(b"MACHO_CANDIDATE")

    def parsed(self, *, arch="i386", bits=32, filetype=2, slices=None, libs=None):
        if slices is None:
            slices = [{"arch":"ppc", "offset":48, "size":32},
                      {"arch":"i386", "offset":80, "size":256}]
        if libs is None:
            libs = [
                {"kind":"load", "name":"/usr/lib/libSystem.B.dylib"},
                {"kind":"load", "name":"/System/Library/Frameworks/Carbon.framework/Versions/A/Carbon"},
                {"kind":"weak", "name":"/System/Library/Frameworks/QuickTime.framework/QuickTime"},
                {"kind":"load", "name":"@rpath/PortAudio.dylib"}
            ]
        return {"arch":arch,"bits":bits,"filetype":filetype,"fat_slices":slices,
                "sha256":self.sha,"dylibs":libs,"imports_nlist":["_Foo","_Bar"],
                "imports_detail":[{"name":"_Foo"},{"name":"_Bar"}],
                "has_symtab":True,"has_dyld_info":False,
                "two_level_namespace":True}

    def with_inspect(self, data, sysroot=True):
        module=types.SimpleNamespace(InvalidMachO=ValueError, inspect=lambda path,arch:data)
        with patch.dict(sys.modules,{"macho_audit":module}):
            return gate.audit_app(self.app,self.sysroot if sysroot else None,self.sha)

    def test_properly_pinned_app_and_literal_sysroot_presence(self):
        report=self.with_inspect(self.parsed())
        self.assertEqual(report["status"],"SH19_ORIGINAL_APP_STATIC_INSPECTED")
        self.assertEqual(report["bundle_file_count"],2)
        self.assertEqual(report["strong_dependencies_not_found_at_literal_prefix_paths"],1)
        self.assertEqual([d["static_location"] for d in report["dyld_load_commands"]],
                         ["FILE_PRESENT_NOT_LOAD_VERIFIED","NOT_FOUND_AT_LITERAL_PATH",
                          "NOT_FOUND_AT_LITERAL_PATH","NOT_RESOLVED_STATICALLY"])
        self.assertEqual(report["execution"],"NOT_RUN")
        self.assertEqual(report["audio"],"NOT_RUN")

    def test_no_prefix_never_infers_missing_libraries(self):
        report=self.with_inspect(self.parsed(),sysroot=False)
        self.assertFalse(report["private_sysroot_checked"])
        self.assertEqual(report["strong_dependencies_not_found_at_literal_prefix_paths"],0)
        self.assertTrue(all(d["static_location"] == "NOT_RESOLVED_STATICALLY"
                            for d in report["dyld_load_commands"]))

    def test_bad_hash_refused_before_macho_parser(self):
        with self.assertRaisesRegex(gate.Blocked,"SHA-256 mismatch"):
            gate.audit_app(self.app,self.sysroot)

    def test_ppc_only_refused(self):
        with self.assertRaisesRegex(gate.Blocked,"Universal"):
            self.with_inspect(self.parsed(slices=[{"arch":"ppc"}]))

    def test_thin_i386_refused_for_pinned_universal_release(self):
        with self.assertRaisesRegex(gate.Blocked,"Universal"):
            self.with_inspect(self.parsed(slices=[]))

    def test_wrong_macho_filetype_refused(self):
        with self.assertRaisesRegex(gate.Blocked,"MH_EXECUTE"):
            self.with_inspect(self.parsed(filetype=6))

    def test_mismatched_macho_digest_refused(self):
        data=self.parsed()
        data["sha256"]="0"*64
        with self.assertRaisesRegex(gate.Blocked,"hash disagree"):
            self.with_inspect(data)

    def test_symlinked_file_refused(self):
        target=self.root/"outside"
        target.write_bytes(b"A")
        (self.app/"Contents"/"Resources").mkdir()
        (self.app/"Contents"/"Resources"/"Audio.rsrc").symlink_to(target)
        with self.assertRaisesRegex(gate.Blocked,"non-regular"):
            self.with_inspect(self.parsed())

    def test_symlinked_dir_refused(self):
        (self.app/"Contents"/"Resources").symlink_to(self.root,target_is_directory=True)
        with self.assertRaisesRegex(gate.Blocked,"symbolic directory"):
            self.with_inspect(self.parsed())

    def test_invalid_plist_fails_closed(self):
        self.plist.write_bytes(b"not a plist")
        with self.assertRaises(plistlib.InvalidFileException):
            self.with_inspect(self.parsed())

    def test_wrong_declared_executable_refused(self):
        self.plist.write_bytes(plistlib.dumps({"CFBundleExecutable":"FauxHack"}))
        with self.assertRaisesRegex(gate.Blocked,"Info.plist executable"):
            self.with_inspect(self.parsed())

    def test_loader_path_confined_to_bundle(self):
        libs=[{"kind":"load","name":"@loader_path/libA.dylib"},
              {"kind":"load","name":"@loader_path/../../../../../outside"}]
        (self.bin.parent/"libA.dylib").write_bytes(b"B")
        report=self.with_inspect(self.parsed(libs=libs))
        self.assertEqual([d["static_location"] for d in report["dyld_load_commands"]],
                         ["FILE_PRESENT_NOT_LOAD_VERIFIED","OUTSIDE_AUTHORIZED_ROOT"])

    def test_sysroot_symlink_escape_refused_as_location(self):
        parent=self.sysroot/"usr"/"lib"
        (parent/"libEscape.dylib").symlink_to(self.bin)
        libs=[{"kind":"load","name":"/usr/lib/libEscape.dylib"}]
        report=self.with_inspect(self.parsed(libs=libs))
        self.assertEqual(report["dyld_load_commands"][0]["static_location"],"OUTSIDE_AUTHORIZED_ROOT")

    def test_no_duplicate_or_unspecified_binary_id(self):
        with self.assertRaisesRegex(gate.Blocked,"install name"):
            self.with_inspect(self.parsed(libs=[{"kind":"id","name":"libFake.dylib"}]))


if __name__ == "__main__":
    unittest.main()
