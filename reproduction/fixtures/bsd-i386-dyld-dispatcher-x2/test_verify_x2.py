#!/usr/bin/env python3
"""Unit tests of verify_x2.py on synthetic records (no guest needed)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_x2 as v  # noqa: E402

DY_NEW = "3a" * 32
DY_OLD = "81" * 32
KE = "30" * 32
TABLE = 0xF7BB1A34


def entry(nr):
    return TABLE + 4 * nr


def make(root: Path, name: str, profile: str, dyld=DY_NEW, kernel=KE, edit=None):
    rec = root / name
    rec.mkdir()
    out = ["X2_STARTED pid=13", f"X2_DYLD_SHA256 {dyld}", f"X2_KERNEL_SHA256 {kernel}",
           f"X2_INFO dyld_dispatcher bound_insn={'present' if profile == 'fixed' else 'absent'} first_bytes=90"]
    fails = 0
    for sec, n in v.EXPECTED:
        status, detail = "PASS", "x"
        if profile == "defect":
            if (sec, n) == ("S", "access_enoent_ret"):
                status, detail = "FAIL", "nr=33 ret=-2 errno=0 want_ret=-1 want_errno=2"
            elif n.endswith("reported_number"):
                status, detail = "FAIL", "want=Unimplemented_syscall_(8) out=Unimplemented_syscall_(-139544012)_"
            elif sec == "G" and n != "nr599_control_read_detected":
                status = "FAIL"
        if status == "FAIL":
            fails += 1
        out.append(f"X2 {sec} {n} {status} {detail}")
    for nr in (599, 600, 1000, 65535):
        fault = profile == "defect" or nr == 599
        out.append(f"X2_INFO G_nr{nr} nr={nr} table=0x{TABLE:08x} entry=0x{entry(nr):08x} guarded_page=0x0 in_dyld=1 "
                   f"status={77 if fault else 0} fault_addr=0x{entry(nr) if fault else 0:08x} fault_eip=0x1 eax=0")
    out.append(f"X2_SUMMARY checks=98 failures={fails} section_failures=I0:P0:S0:D0:G0:W0")
    out.append("X2_FINISHED_OK" if profile == "fixed" else "X2_FINISHED_WITH_FAILURES")
    err = [f"PREFLIGHT ns_kernel={kernel}", f"PREFLIGHT ns_dyld={dyld}"]
    meta = "host_mounts_before=41 darlingserver_before=0\nrc=0\nhost_mounts_after=41 darlingserver_after=0\nresidual_prefix_processes=0\n"
    rc = "0" if profile == "fixed" else "10"
    files = {"stdout": "\n".join(out) + "\n", "stderr": "\n".join(err) + "\n", "meta": meta, "rc": rc + "\n"}
    if edit:
        edit(files)
    (rec / "stdout.log").write_text(files["stdout"])
    (rec / "stderr.log").write_text(files["stderr"])
    (rec / "meta.txt").write_text(files["meta"])
    (rec / "rc").write_text(files["rc"])
    return rec


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def ok(self, rec, expect, dyld=DY_NEW):
        return v.verify(rec, expect, dyld, KE) == []

    def test_fixed_accepted(self):
        self.assertTrue(self.ok(make(self.root, "f", "fixed"), "fixed"))

    def test_fixed_rejected_as_defect(self):
        self.assertFalse(self.ok(make(self.root, "f", "fixed"), "defect"))

    def test_defect_accepted(self):
        self.assertTrue(self.ok(make(self.root, "d", "defect", dyld=DY_OLD), "defect", DY_OLD))

    def test_defect_rejected_as_fixed(self):
        self.assertFalse(self.ok(make(self.root, "d", "defect", dyld=DY_OLD), "fixed", DY_OLD))

    def test_wrong_namespace_dyld(self):
        rec = make(self.root, "f", "fixed", edit=lambda f: f.update(stderr=f["stderr"].replace(DY_NEW, DY_OLD)))
        self.assertFalse(self.ok(rec, "fixed"))

    def test_guest_hash_mismatch(self):
        rec = make(self.root, "f", "fixed", edit=lambda f: f.update(stdout=f["stdout"].replace(f"X2_DYLD_SHA256 {DY_NEW}", f"X2_DYLD_SHA256 {DY_OLD}")))
        self.assertFalse(self.ok(rec, "fixed"))

    def test_kernel_mismatch(self):
        self.assertNotEqual(v.verify(make(self.root, "f", "fixed", kernel="ab" * 32), "fixed", DY_NEW, KE), [])

    def test_single_fail_rejected(self):
        rec = make(self.root, "f", "fixed", edit=lambda f: f.update(stdout=f["stdout"].replace("X2 D nr600_raw PASS", "X2 D nr600_raw FAIL")))
        self.assertFalse(self.ok(rec, "fixed"))

    def test_missing_check_rejected(self):
        rec = make(self.root, "f", "fixed", edit=lambda f: f.update(stdout=f["stdout"].replace("X2 S nr65535_ret PASS x\n", "")))
        self.assertFalse(self.ok(rec, "fixed"))

    def test_identity_failure_rejects_defect(self):
        rec = make(self.root, "d", "defect", dyld=DY_OLD,
                   edit=lambda f: f.update(stdout=f["stdout"].replace("X2 I dyld_text_mapped_equals_file PASS", "X2 I dyld_text_mapped_equals_file FAIL")))
        self.assertFalse(self.ok(rec, "defect", DY_OLD))

    def test_dyld_path_failure_rejects_fixed(self):
        rec = make(self.root, "f", "fixed", edit=lambda f: f.update(stdout=f["stdout"].replace("X2 P libsystem_syscall_getpid_not_dyld PASS", "X2 P libsystem_syscall_getpid_not_dyld FAIL")))
        self.assertFalse(self.ok(rec, "fixed"))

    def test_defect_fault_elsewhere_rejected(self):
        bad = f"fault_addr=0x{entry(1000):08x}"
        rec = make(self.root, "d", "defect", dyld=DY_OLD,
                   edit=lambda f: f.update(stdout=f["stdout"].replace(bad, "fault_addr=0x00041900")))
        self.assertFalse(self.ok(rec, "defect", DY_OLD))

    def test_guard_control_missing_rejected(self):
        rec = make(self.root, "f", "fixed", edit=lambda f: f.update(stdout=f["stdout"].replace("X2 G nr599_control_read_detected PASS", "X2 G nr599_control_read_detected FAIL")))
        self.assertFalse(self.ok(rec, "fixed"))

    def test_mount_leak_rejected(self):
        rec = make(self.root, "f", "fixed", edit=lambda f: f.update(meta=f["meta"].replace("host_mounts_after=41", "host_mounts_after=42")))
        self.assertFalse(self.ok(rec, "fixed"))

    def test_residual_process_rejected(self):
        rec = make(self.root, "f", "fixed", edit=lambda f: f.update(meta=f["meta"].replace("residual_prefix_processes=0", "residual_prefix_processes=1")))
        self.assertFalse(self.ok(rec, "fixed"))

    def test_wrapper_failure_rejects_defect(self):
        rec = make(self.root, "d", "defect", dyld=DY_OLD,
                   edit=lambda f: f.update(stdout=f["stdout"].replace("X2 W lseek_2fffff001_ret PASS", "X2 W lseek_2fffff001_ret FAIL")))
        self.assertFalse(self.ok(rec, "defect", DY_OLD))

    def test_bound_absent_rejects_fixed(self):
        rec = make(self.root, "f", "fixed", edit=lambda f: f.update(stdout=f["stdout"].replace("bound_insn=present", "bound_insn=absent")))
        self.assertFalse(self.ok(rec, "fixed"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
