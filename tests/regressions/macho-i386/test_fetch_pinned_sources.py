#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline tests for the pinned-source retrieval and git blob checks."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fetch_pinned_sources as pinned


class PinnedSourceTests(unittest.TestCase):
    def test_expected_six_source_pins(self):
        self.assertEqual(len(pinned.SOURCES), 6)
        self.assertEqual(len({x[0] for x in pinned.SOURCES}), 6)
        self.assertTrue(all(len(x[2]) == 40 and len(x[4]) == 40 for x in pinned.SOURCES))

    def test_git_blob_sha_for_known_empty_blob(self):
        self.assertEqual(pinned.git_blob_sha(b""),
                         "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")

    def test_git_blob_sha_changes_with_content(self):
        self.assertNotEqual(pinned.git_blob_sha(b"a"), pinned.git_blob_sha(b"b"))

    def test_refuses_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileExistsError):
                pinned.fetch_pinned(Path(tmp), fetcher=lambda _: b"")

    def test_rejects_blob_mismatch_before_writing_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "new"
            with patch.object(pinned, "SOURCES", (("src/file.c", "r/x", "abc", "file.c", "f" * 40),)):
                with self.assertRaisesRegex(pinned.PinError, "blob mismatch"):
                    pinned.fetch_pinned(directory, fetcher=lambda _: b"tampered")
            self.assertFalse((directory / "src/file.c").exists())

    def test_fetch_single_exact_blob_and_written_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "new"
            sample = b"tiny trusted source\n"
            blob = pinned.git_blob_sha(sample)
            with patch.object(pinned, "SOURCES", (("src/other/name.c", "test/source", "1" * 40,
                                                   "upstream.c", blob),)):
                records = pinned.fetch_pinned(directory, fetcher=lambda _: sample)
            self.assertEqual((directory / "src/other/name.c").read_bytes(), sample)
            self.assertEqual(records[0]["git_blob_sha"], blob)
            self.assertEqual(records[0]["commit"], "1" * 40)

    def test_refuses_oversize_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(pinned, "SOURCES", (("src/file.c", "r/x", "abc", "file.c", "a" * 40),)):
                with self.assertRaisesRegex(pinned.PinError, "oversize"):
                    pinned.fetch_pinned(Path(tmp) / "new", fetcher=lambda _: b"a" * (pinned.MAX_SOURCE_BYTES + 1))

    def test_urls_are_immutable_commit_urls(self):
        for relative, repo, commit, source_path, _ in pinned.SOURCES:
            with self.subTest(relative=relative):
                self.assertTrue(repo.startswith("darlinghq/"))
                self.assertNotIn("..", source_path)
                self.assertRegex(commit, r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main(verbosity=2)
