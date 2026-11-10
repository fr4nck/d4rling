import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import verify_bsd_i386_patchset as m


class SourceHunkTests(unittest.TestCase):
    def test_git_blob_hash_known(self):
        self.assertEqual(m.git_blob(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_unlisted_source_rejected(self):
        with self.assertRaises(m.GateError):
            m.verify_pinned_content("wrong", b"anything")

    def test_mismatched_source_rejected(self):
        k=next(iter(m.PINNED))
        with self.assertRaises(m.GateError):
            m.verify_pinned_content(k, b"different")

    def test_missing_sources_dir_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(m.GateError):
                m.load_pinned_dir(Path(tmp))

    def test_good_hunk_exact(self):
        source="first\nsecond\nthird\n"
        hunk={"old":2,"old_count":1,"new":2,"new_count":2,"lines":["-second","+new","+extra"]}
        self.assertEqual(m.apply_hunks(source,[hunk]),"first\nnew\nextra\nthird\n")

    def test_bad_context_rejected(self):
        hunk={"old":1,"old_count":1,"new":1,"new_count":1,"lines":["-wrong","+new"]}
        with self.assertRaises(m.GateError):
            m.apply_hunks("old\n",[hunk])

    def test_bad_count_rejected(self):
        hunk={"old":1,"old_count":3,"new":1,"new_count":1,"lines":["-old","+new"]}
        with self.assertRaises(m.GateError):
            m.apply_hunks("old\n",[hunk])

    def test_duplicate_patch_path_rejected(self):
        body="diff --git a/a b/a\n--- a/a\n+++ b/a\n@@ -1 +1 @@\n-x\n+y\n"
        with self.assertRaises(m.GateError):
            m.split_patch(body+body)

    def test_patch_scope_rejected(self):
        body="diff --git a/../unsafe b/../unsafe\n--- a/../unsafe\n+++ b/../unsafe\n@@ -1 +1 @@\n-x\n+y\n"
        with self.assertRaises(m.GateError):
            m.split_patch(body)

    def test_sequential_hunks(self):
        a={"old":1,"old_count":1,"new":1,"new_count":2,"lines":["-a","+a1","+a2"]}
        b={"old":3,"old_count":1,"new":4,"new_count":1,"lines":["-c","+c1"]}
        self.assertEqual(m.apply_hunks("a\nb\nc\n",[a,b]),"a1\na2\nb\nc1\n")

    def test_overlap_rejected(self):
        a={"old":1,"old_count":2,"new":1,"new_count":2,"lines":[" a"," b"]}
        b={"old":2,"old_count":1,"new":2,"new_count":1,"lines":["-b","+b1"]}
        with self.assertRaises(m.GateError):
            m.apply_hunks("a\nb\n",[a,b])

    def test_symlink_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            first=next(iter(m.PINNED))
            actual=root/"other"
            actual.write_text("fake")
            src=root/first
            src.parent.mkdir(parents=True)
            src.symlink_to(actual)
            with self.assertRaises(m.GateError):
                m.load_pinned_dir(root)

    def test_revision_path_mismatch_rejected(self):
        with patch.object(m, "git_read", side_effect=[(m.REV + "\n").encode(), b"not-the-expected-blob\n"]):
            with self.assertRaises(m.GateError):
                m.load_xnu(Path("/irrelevant"))

    def test_git_revision_unavailable_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(m.GateError):
                m.load_xnu(Path(d))

    def test_require_lf(self):
        h={"old":1,"old_count":1,"new":1,"new_count":1,"lines":["-a","+b"]}
        with self.assertRaises(m.GateError):
            m.apply_hunks("a",[h])


if __name__=="__main__":
    unittest.main()
