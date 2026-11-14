#!/usr/bin/env python3
"""Unit tests for verify_probe.py on synthetic run records (no guest needed)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_probe as vp  # noqa: E402

KSHA = "a" * 64


def fixed_lines():
    lines = ["BSDP_STARTED pointer=4 off_t=8"]
    for s, names in vp.ALL.items():
        lines += [f"BSDP {s} {n} PASS ok" for n in names]
    total = sum(len(v) for v in vp.ALL.values())
    lines += [f"BSDP_SUMMARY checks={total} failures=0 section_failures=A0:B0:C0:D0:E0:F0", "BSDP_FINISHED_OK"]
    return lines


def defect_lines():
    lines = ["BSDP_STARTED pointer=4 off_t=8"]
    lines += [f"BSDP A {n} PASS ok" for n in vp.A_NAMES]
    lines += [f"BSDP B {n} PASS ok" for n in vp.B_NAMES]
    lines += ["BSDP C syscall_getpid PASS ret=5", "BSDP C syscall_access_ok PASS ret=0",
              "BSDP C syscall_access_ENOENT FAIL ret=-2 errno=0", "BSDP C syscall_close_EBADF FAIL ret=-9 errno=0"]
    for nr in (8, 599, 600, 1000):
        lines += [f"BSDP D unknown_{nr} FAIL nr={nr} ret=-78 errno=0 out=x",
                  f"BSDP D unknown_{nr}_reported_number FAIL want=y out=x"]
    lines += ["BSDP D unknown_65535 FAIL nr=65535 child_signal_or_error=11 exit=-1 out="]
    lines += ["BSDP E i386_get_ldt_error FAIL ret=-78 errno=0", "BSDP E i386_get_ldt_reported_trap FAIL want=x",
              "BSDP E i386_set_ldt_error FAIL ret=-78 errno=0", "BSDP E i386_set_ldt_reported_trap FAIL want=x"]
    lines += ["BSDP F threads_created PASS x", "BSDP F threads_calls PASS x", "BSDP F threads_errno_stubs PASS x",
              "BSDP F threads_errno_syscall FAIL bad=200"]
    lines += ["BSDP_SUMMARY checks=45 failures=16", "BSDP_FINISHED_WITH_FAILURES"]
    return lines


def make(root, name, out, rc, *, residual="0", ds="0", mounts=("41", "41"), setgroups=True, ksha=KSHA):
    run = Path(root) / name
    run.mkdir()
    (run / "stdout.log").write_text("\n".join(out) + "\n")
    err = ["PREFLIGHT setgroups=allow" if setgroups else "PREFLIGHT setgroups=deny"]
    if setgroups:
        err.append("PREFLIGHT probe=OK")
    err.append(f"PREFLIGHT ns_kernel={ksha}")
    (run / "stderr.log").write_text("\n".join(err) + "\n")
    (run / "meta.txt").write_text(
        f"label={name}\nhost_mounts_before={mounts[0]} darlingserver_before=0\nrc={rc}\n"
        f"host_mounts_after={mounts[1]} darlingserver_after={ds}\nresidual_prefix_processes={residual}\n")
    (run / "rc").write_text(f"{rc}\n")
    return run


class VerifyProbe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_fixed_record_passes(self):
        run = make(self.root, "f", fixed_lines(), 0)
        self.assertEqual(vp.verify(run, "fixed", KSHA), [])

    def test_defect_record_passes(self):
        run = make(self.root, "d", defect_lines(), 10)
        self.assertEqual(vp.verify(run, "defect", KSHA), [])

    def test_fixed_rejects_one_failure(self):
        out = [l.replace("BSDP C syscall_close_EBADF PASS", "BSDP C syscall_close_EBADF FAIL") for l in fixed_lines()]
        self.assertTrue(vp.verify(make(self.root, "f1", out, 0), "fixed"))

    def test_fixed_rejects_missing_check(self):
        out = [l for l in fixed_lines() if "unknown_65535_reported_number" not in l]
        self.assertTrue(vp.verify(make(self.root, "f2", out, 0), "fixed"))

    def test_fixed_rejects_nonzero_rc(self):
        self.assertTrue(vp.verify(make(self.root, "f3", fixed_lines(), 10), "fixed"))

    def test_fixed_rejects_duplicate(self):
        out = fixed_lines()
        out.insert(2, out[1])
        self.assertTrue(vp.verify(make(self.root, "f4", out, 0), "fixed"))

    def test_rejects_wrong_namespace_kernel(self):
        run = make(self.root, "f5", fixed_lines(), 0, ksha="b" * 64)
        self.assertTrue(vp.verify(run, "fixed", KSHA))

    def test_rejects_residual_process(self):
        self.assertTrue(vp.verify(make(self.root, "f6", fixed_lines(), 0, residual="1"), "fixed"))

    def test_rejects_leftover_darlingserver(self):
        self.assertTrue(vp.verify(make(self.root, "f7", fixed_lines(), 0, ds="1"), "fixed"))

    def test_rejects_mount_leak(self):
        self.assertTrue(vp.verify(make(self.root, "f8", fixed_lines(), 0, mounts=("41", "42")), "fixed"))

    def test_rejects_setgroups_denied(self):
        self.assertTrue(vp.verify(make(self.root, "f9", fixed_lines(), 0, setgroups=False), "fixed"))

    def test_defect_rejects_fixed_record(self):
        self.assertTrue(vp.verify(make(self.root, "d1", fixed_lines(), 0), "defect"))

    def test_fixed_rejects_defect_record(self):
        self.assertTrue(vp.verify(make(self.root, "d2", defect_lines(), 10), "fixed"))

    def test_defect_requires_stub_sections_to_pass(self):
        out = [l.replace("BSDP A access_ENOENT PASS", "BSDP A access_ENOENT FAIL") for l in defect_lines()]
        self.assertTrue(vp.verify(make(self.root, "d3", out, 10), "defect"))

    def test_defect_requires_raw_errno_signature(self):
        out = [l.replace("ret=-2 errno=0", "ret=-1 errno=2") for l in defect_lines()]
        self.assertTrue(vp.verify(make(self.root, "d4", out, 10), "defect"))

    def test_defect_rejects_documented_enosys_past_table(self):
        out = [l.replace("FAIL nr=65535 child_signal_or_error=11 exit=-1 out=", "PASS nr=65535 ret=-1 errno=78 out=x")
               for l in defect_lines()]
        self.assertTrue(vp.verify(make(self.root, "d5", out, 10), "defect"))

    def test_defect_accepts_unrelated_handler_past_table(self):
        out = [l.replace("nr=600 ret=-78 errno=0", "nr=600 ret=-45 errno=0") for l in defect_lines()]
        self.assertEqual(vp.verify(make(self.root, "d7", out, 10), "defect"), [])

    def test_defect_requires_raw_enosys_inside_table(self):
        out = [l.replace("nr=8 ret=-78 errno=0", "nr=8 ret=-1 errno=78") for l in defect_lines()]
        self.assertTrue(vp.verify(make(self.root, "d8", out, 10), "defect"))

    def test_defect_accepts_crash_at_600(self):
        out = [l for l in defect_lines() if "unknown_600_reported_number" not in l]
        out = [l.replace("nr=600 ret=-78 errno=0", "nr=600 child_signal_or_error=11 exit=-1") for l in out]
        self.assertEqual(vp.verify(make(self.root, "d6", out, 10), "defect"), [])

    def test_unreadable_record(self):
        self.assertTrue(vp.verify(Path(self.root) / "absent", "fixed"))


if __name__ == "__main__":
    unittest.main()
