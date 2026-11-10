#!/usr/bin/env python3
"""SH12 closed-world replay tests. Synthetic ELF files are NEVER executed."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
import zipfile

import sh12_cctools_replay as sh

TEST_PACKAGE = os.environ.get("SOUNDHACK_SH10_PACKAGE")


def fake_elf():
    header = bytearray(64)
    header[:4] = b"\x7fELF"
    header[4:6] = bytes([2, 1])
    struct.pack_into("<H", header, 16, 2)   # ELF executable
    struct.pack_into("<H", header, 18, sh.MACHINE.get(__import__("platform").machine().lower(), 62))
    return bytes(header) + b"synthetic data - never executed\n"


class LinkReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sh12-tests-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.package = self.root / "sh10.zip"

    def use_original_package(self):
        if not TEST_PACKAGE or not Path(TEST_PACKAGE).is_file():
            self.skipTest("Provide real pinned SH10 ZIP via SOUNDHACK_SH10_PACKAGE")
        shutil.copyfile(TEST_PACKAGE, self.package)

    def valid_fake_linker(self, name="x86_64-apple-darwin20-ld"):
        folder = self.root / "src/external/cctools-port/cctools/ld64/src"
        folder.mkdir(parents=True, exist_ok=True)
        file = folder / name
        file.write_bytes(fake_elf())
        file.chmod(0o755)
        return file

    def rewrite_zip(self, edit):
        with zipfile.ZipFile(self.package) as z:
            data = {name: z.read(name) for name in z.namelist()}
        edit(data)
        with zipfile.ZipFile(self.package, "w", compression=zipfile.ZIP_STORED) as z:
            for key, value in data.items():
                z.writestr(key, value)

    def test_missing_package_refused(self):
        with self.assertRaises(sh.Inconclusive):
            with tempfile.TemporaryDirectory() as tmp:
                sh.read_sh10_package(self.package, Path(tmp))

    def test_native_local_elf_candidate_is_identified_but_not_run(self):
        path = self.valid_fake_linker()
        found = sh.find_linkers(self.root)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["path"], str(path))
        self.assertEqual(len(found[0]["sha256"]), 64)
        self.assertIn("provenance NOT proved", found[0]["identity_scope"])

    def test_no_linker_is_not_pass(self):
        self.assertEqual(sh.find_linkers(self.root), [])

    def test_ignores_lld_and_scripts(self):
        self.valid_fake_linker(name="ld64.lld")
        folder = self.root / "src/external/cctools-port/cctools/ld64/src"
        script = folder / "ld64"
        script.write_bytes(b"#!/bin/sh\necho fake\n")
        script.chmod(0o755)
        self.assertEqual(sh.find_linkers(self.root), [])

    def test_symlink_candidate_ignored(self):
        file = self.valid_fake_linker()
        path = file.parent / "ld64"
        path.symlink_to(file)
        self.assertEqual(len(sh.find_linkers(self.root)), 1)

    def test_ambiguous_distinct_candidates_detected(self):
        self.valid_fake_linker()
        self.valid_fake_linker(name="i386-apple-darwin11-ld")
        self.assertEqual(len(sh.find_linkers(self.root)), 2)

    def test_elf_relocatable_candidate_ignored(self):
        file = self.valid_fake_linker()
        data = bytearray(file.read_bytes())
        struct.pack_into("<H", data, 16, 1)  # ET_REL cannot be executed
        file.write_bytes(data)
        self.assertEqual(sh.find_linkers(self.root), [])

    def test_wrong_machine_candidate_ignored(self):
        file = self.valid_fake_linker()
        data = bytearray(file.read_bytes())
        struct.pack_into("<H", data, 18, 3)  # Linux i386, not x86_64
        file.write_bytes(data)
        self.assertEqual(sh.find_linkers(self.root), [])

    def test_linker_outside_source_tree_rejected(self):
        evil = self.root / "elsewhere" / "ld64"
        evil.parent.mkdir(parents=True)
        evil.write_bytes(fake_elf())
        evil.chmod(0o755)
        with self.assertRaises(sh.Inconclusive):
            sh.linker_identity(evil, self.root)

    def test_symlinked_build_root_refused(self):
        (self.root / "fake-build").symlink_to(self.root)
        with self.assertRaises(sh.Inconclusive):
            sh.find_linkers(self.root / "fake-build")

    def test_cli_missing_package_inconclusive(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = sh.main(["--sh10-package", str(self.package), "--build-root", str(self.root)])
        result = json.loads(out.getvalue())
        self.assertEqual((code, result["status"]), (3, "INCONCLUSIVE"))

    def test_real_package_recovers_exact_sh08_object(self):
        self.use_original_package()
        with tempfile.TemporaryDirectory() as tmp:
            result = sh.read_sh10_package(self.package, Path(tmp))
            self.assertEqual(result["object_sha256"], sh.EXPECTED_SH08_SHA256)
            self.assertEqual(result["archive_sha256"], sh.ARCHIVE_SHA256)
            self.assertEqual(result["object_path"].stat().st_size, sh.OBJECT_BYTES)

    def test_real_package_missing_linker_fails_closed(self):
        self.use_original_package()
        linked = self.root / "must-not-exist.dylib"
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = sh.main(["--sh10-package", str(self.package), "--build-root", str(self.root),
                            "--linked-output", str(linked)])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out.getvalue())["status"], "LINKER_ABSENT")
        self.assertFalse(linked.exists())

    def test_real_package_missing_build_root_fails_closed(self):
        self.use_original_package()
        result = sh.qualify(self.package, None)
        self.assertEqual(result["status"], "LINKER_ABSENT")

    def test_package_modified_archive_rejected(self):
        self.use_original_package()
        self.rewrite_zip(lambda d: d.__setitem__(sh.ARCHIVE_NAME, d[sh.ARCHIVE_NAME][:-1] + b"X"))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(sh.ContractFailure):
                sh.read_sh10_package(self.package, Path(tmp))

    def test_package_missing_license_rejected(self):
        self.use_original_package()
        self.rewrite_zip(lambda d: d.__setitem__("LICENSE-MIT-SoundHack.txt", b"no license"))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(sh.ContractFailure):
                sh.read_sh10_package(self.package, Path(tmp))

    def test_package_malformed_manifest_rejected(self):
        self.use_original_package()
        self.rewrite_zip(lambda d: d.__setitem__("qualification.json", b'{"archive": null}'))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(sh.ContractFailure):
                sh.read_sh10_package(self.package, Path(tmp))

    def test_package_duplicate_member_rejected(self):
        self.use_original_package()
        with zipfile.ZipFile(self.package, "a") as z:
            with __import__("warnings").catch_warnings():
                __import__("warnings").simplefilter("ignore", UserWarning)
                z.writestr(sh.ARCHIVE_NAME, b"different archive")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(sh.ContractFailure):
                sh.read_sh10_package(self.package, Path(tmp))

    def test_package_symlink_rejected(self):
        self.use_original_package()
        linked = self.root / "package-symlink.zip"
        linked.symlink_to(self.package)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(sh.Inconclusive):
                sh.read_sh10_package(linked, Path(tmp))


if __name__ == "__main__":
    unittest.main()
