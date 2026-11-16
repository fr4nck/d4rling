#!/usr/bin/env python3
"""SH20 synthetic negative/positive tests (never fetch SoundHack or execute 7zz)."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path
import plistlib
import stat
import struct
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import sh20_official_replay as replay


def odc(entries):
    data = bytearray()
    for name, contents, mode in entries + [("TRAILER!!!", b"", 0)]:
        name = name.encode() + b"\x00"
        header = (b"070707" + b"".join(format(v, "06o").encode() for v in [0, 1, mode, 0, 0, 1, 0]) +
                  format(0, "011o").encode() + format(len(name), "06o").encode() +
                  format(len(contents), "011o").encode())
        assert len(header) == 76
        data += header + name + contents
    return bytes(data)


def app_entries(binary=b"SYNTHETIC_UNTRUSTED_NOT_APPLE"):
    base = "SoundHack.app/Contents/"
    entries = [("SoundHack.app", b"", stat.S_IFDIR | 0o755),
               (base + "MacOS", b"", stat.S_IFDIR | 0o755),
               (base + "Resources", b"", stat.S_IFDIR | 0o755),
               (base + "MacOS/SoundHack", binary, stat.S_IFREG | 0o755),
               (base + "Info.plist", plistlib.dumps({"CFBundleExecutable": "SoundHack"}), stat.S_IFREG | 0o644)]
    entries += [(base + "Resources/Resource%d" % i, b"resource" + bytes([i]), stat.S_IFREG | 0o644)
                for i in range(6)]
    return entries


def fake_elf():
    b = bytearray(b"\x00" * 120000)
    b[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", b, 18, 62)
    return bytes(b)


def make_tar(blob):
    b = io.BytesIO()
    with tarfile.open(fileobj=b, mode="w:xz") as t:
        info = tarfile.TarInfo("./7zz")
        info.size = len(blob)
        t.addfile(info, io.BytesIO(blob))
    return b.getvalue()


def fake_dmg():
    image = bytearray(b"A" * 1024)
    image[-512:-508] = b"koly"
    return bytes(image)


def make_zip(image):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("SH896.dmg", image)
        z.writestr("__MACOSX/._SH896.dmg", b"APPLEDOUBLE_IS_IGNORED")
    return b.getvalue()


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.output = self.base / "replay"
        self.audit = self.base / "tools"
        self.audit.mkdir()
        (self.audit / "sh19_app_gate.py").write_text("# synthetic stub")
        (self.audit / "macho_audit.py").write_text("# synthetic stub")
        self.original = b"SYNTHETIC_UNTRUSTED_NOT_APPLE"
        self.archive = odc(app_entries(self.original))
        self.pax = gzip.compress(self.archive)
        self.image = fake_dmg()
        self.zip = make_zip(self.image)
        self.seven = make_tar(fake_elf())
        self.patches = [
            patch.object(replay, "DMG_SIZE", len(self.image)),
            patch.object(replay, "PIN_ZIP", replay.digest(self.zip)),
            patch.object(replay, "PIN_DMG", replay.digest(self.image)),
            patch.object(replay, "PIN_PAX", replay.digest(self.pax)),
            patch.object(replay, "PIN_BIN", replay.digest(self.original)),
            patch.object(replay, "PIN_SEVEN", replay.digest(self.seven)),
        ]
        for x in self.patches:
            x.start(); self.addCleanup(x.stop)

    def test_odc_recognizes_8_app_files(self):
        records = replay.cpio_odc(self.archive)
        self.assertEqual(len(records), 11)
        count, amount = replay.extract_app(records, self.output)
        self.assertEqual(count, 8)
        self.assertGreater(amount, 10)
        self.assertEqual((self.output / "Contents/MacOS/SoundHack").read_bytes(), self.original)

    def test_cpio_bad_magic(self):
        with self.assertRaisesRegex(replay.Blocked, "CPIO-ODC"):
            replay.cpio_odc(b"bad" + self.archive[3:])

    def test_cpio_truncated_header(self):
        with self.assertRaisesRegex(replay.Blocked, "CPIO-ODC"):
            replay.cpio_odc(self.archive[:7])

    def test_cpio_truncated_content(self):
        with self.assertRaisesRegex(replay.Blocked, "bounds"):
            replay.cpio_odc(self.archive[:80])

    def test_cpio_path_escape_refused(self):
        a = odc(app_entries() + [("SoundHack.app/../../escape", b"X", stat.S_IFREG | 0o644)])
        with self.assertRaisesRegex(replay.Blocked, "unsafe CPIO path"):
            replay.cpio_odc(a)

    def test_cpio_symlink_refused(self):
        a = odc(app_entries() + [("SoundHack.app/Contents/Resources/x", b"../outside", stat.S_IFLNK | 0o777)])
        records = replay.cpio_odc(a)
        with self.assertRaisesRegex(replay.Blocked, "special file"):
            replay.extract_app(records, self.output)
        self.assertFalse(self.output.exists())

    def test_cpio_duplicate_refused(self):
        a = odc(app_entries() + [("SoundHack.app/Contents/MacOS/SoundHack", b"X", stat.S_IFREG | 0o755)])
        with self.assertRaisesRegex(replay.Blocked, "duplicate"):
            replay.extract_app(replay.cpio_odc(a), self.output)

    def test_cpio_wrong_executable_fingerprint(self):
        other = odc(app_entries(b"tampered binary"))
        with self.assertRaisesRegex(replay.Blocked, "SHA-256"):
            replay.extract_app(replay.cpio_odc(other), self.output)
        self.assertFalse(self.output.exists())

    def test_wrong_zip_hash_refused_before_output(self):
        with patch.object(replay, "PIN_ZIP", "f" * 64):
            with self.assertRaisesRegex(replay.Blocked, "ZIP SHA-256"):
                replay.replay(self.zip, self.seven, self.output, self.audit, None)
        self.assertFalse(self.output.exists())

    def test_wrong_tool_hash_refused_before_output(self):
        with patch.object(replay, "PIN_SEVEN", "f" * 64):
            with self.assertRaisesRegex(replay.Blocked, "7ZZ SHA-256"):
                replay.replay(self.zip, self.seven, self.output, self.audit, None)
        self.assertFalse(self.output.exists())

    def test_zip_only_real_dmg_selected(self):
        self.assertEqual(replay.extract_dmg_from_zip(self.zip), self.image)

    def test_zip_truncated_dmg_refused(self):
        bad = make_zip(self.image[:-1])
        with self.assertRaisesRegex(replay.Blocked, "one authentic"):
            replay.extract_dmg_from_zip(bad)

    def test_zip_corrupt_udif_refused(self):
        bad_image = self.image[:-512] + b"abcd" + self.image[-508:]
        with self.assertRaisesRegex(replay.Blocked, "UDIF signature"):
            replay.extract_dmg_from_zip(make_zip(bad_image))

    def test_tar_rejects_non_elf(self):
        with self.assertRaisesRegex(replay.Blocked, "not x86_64"):
            replay.get_7zz_from_tar(make_tar(b"Z" * 150000))

    def test_tar_reads_portable_7zz_only(self):
        self.assertEqual(replay.get_7zz_from_tar(self.seven), fake_elf())

    def test_outdir_exclusive_never_overwrite(self):
        self.output.mkdir()
        with self.assertRaisesRegex(replay.Blocked, "exists"):
            replay.replay(self.zip, self.seven, self.output, self.audit, None)

    def test_prefix_missing_refused_early(self):
        with self.assertRaisesRegex(replay.Blocked, "sysroot missing"):
            replay.replay(self.zip, self.seven, self.output, self.audit, self.base / "absent")
        self.assertFalse(self.output.exists())

    def test_hfs_symlink_refused_after_extract(self):
        seven = self.base / "seven"; seven.write_bytes(b"7Z")
        dmg = self.base / "dmg"; dmg.write_bytes(b"IMG")
        def fake_run(cmd, **kw):
            p = Path(next(x[2:] for x in cmd if x.startswith("-o"))) / replay.PAX_MEMBER
            p.parent.mkdir(parents=True)
            p.symlink_to(self.base / "outside")
            return subprocess.CompletedProcess(cmd, 0, b"", b"")
        with patch.object(replay.subprocess, "run", side_effect=fake_run):
            with self.assertRaisesRegex(replay.Blocked, "missing or symbolic"):
                replay.portable_hfs_extract(seven, dmg, self.output)

    def test_integration_mock_hfs_and_sh19(self):
        def fake_run(command, **kwargs):
            if command[0].endswith("7zz-26.06"):
                out = Path(next(x[2:] for x in command if x.startswith("-o")))
                pax = out / replay.PAX_MEMBER
                pax.parent.mkdir(parents=True)
                pax.write_bytes(self.pax)
                return subprocess.CompletedProcess(command, 0, b"Everything is Ok", b"")
            if "sh19_app_gate.py" in command[2]:
                out = Path(command[command.index("--output") + 1])
                out.write_text(json.dumps({"status": "SH19_ORIGINAL_APP_STATIC_INSPECTED",
                                           "executable_sha256": replay.PIN_BIN,
                                           "nlist_import_count": 120,
                                           "dyld_load_commands": [
                                               {"load_kind": "load", "install_name": "/System/Library/.../Carbon",
                                                "static_location": "NOT_RESOLVED_STATICALLY"}],
                                           "strong_dependencies_not_found_at_literal_prefix_paths": 0}))
                return subprocess.CompletedProcess(command, 0, b"{}", b"")
            self.fail("unexpected subprocess call: " + repr(command))
        with patch.object(replay.subprocess, "run", side_effect=fake_run):
            r = replay.replay(self.zip, self.seven, self.output, self.audit, None)
        self.assertEqual(r["status"], "SH20_OFFICIAL_APP_REPLAY_STATIC_PASS")
        self.assertEqual(r["bundle_files"], 8)
        self.assertEqual(r["nlist_import_count"], 120)
        self.assertEqual((self.output / "SoundHack.app/Contents/MacOS/SoundHack").read_bytes(), self.original)
        self.assertTrue((self.output / "SH20-summary.json").is_file())


if __name__ == "__main__":
    unittest.main()
