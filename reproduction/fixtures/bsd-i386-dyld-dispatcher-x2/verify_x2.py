#!/usr/bin/env python3
"""Mechanical verdict for one run record of dyld-dispatcher-probe (lot X2).

A record is the directory written by run-guest.sh: meta.txt, stdout.log,
stderr.log, rc.

  verify_x2.py RECORD --expect fixed  --dyld-sha SHA --kernel-sha SHA
  verify_x2.py RECORD --expect defect --dyld-sha SHA --kernel-sha SHA

Both profiles require: the dyld and libsystem_kernel hashes seen in the
namespace (PREFLIGHT) and computed by the probe inside the guest equal the
given ones; every identity (I), dyld-path (P) and dyld-wrapper (W) check
passed (the wrappers already convert -errno on fb8f932); the table-read
guard detected the in-table control read (G nr599); no residual mount,
darlingserver or prefix process.

fixed:  all 98 checks present and PASS, exit code 0, bound instruction
        present in the mapped dispatcher.
defect: (dispatcher before darling-xnu#102) exit code 10, bound absent,
        out-of-range numbers read the table entry they index (fault at the
        exact entry address), dyld's syscall(2) stub returns raw -errno,
        .no_sys reports something other than the requested number.
Exit status 0 when the record matches the expected profile, 1 otherwise.
"""
import argparse
import re
import sys
from pathlib import Path

UNKNOWN = ["nr8", "nr599", "nr600", "nr1000", "nr65535"]
VALID = ["getpid", "access_ok", "access_enoent", "close_ebadf"]
WRAPPERS = ["stat64_ok", "stat64_enoent", "lstat64_enoent", "access_enoent", "getattrlist_ok",
            "getattrlist_enoent", "getattrlist_einval", "lseek_1fffffffe", "lseek_2fffff001",
            "lseek_3fffff000", "lseek_einval", "lseek_ebadf"]

EXPECTED = (
    [("I", n) for n in (
        "sha256_selftest", "all_image_infos", "dyld_header", "dyld_symbols",
        "all_image_infos_owned_by_dyld", "dyld_symbols_private", "dyld_file_i386_slice",
        "dyld_uuid_mapped_equals_file", "dyld_text_mapped_equals_file",
        "dyld_dispatcher_bytes_equal_file", "libsystem_kernel_dispatcher_distinct")]
    + [("P", n) for n in (
        "dlopen_absent_enters_dyld_dispatcher", "dlopen_libz_enters_dyld_dispatcher",
        "libsystem_syscall_getpid_not_dyld", "libsystem_syscall_65535_not_dyld")]
    + [("S", f"{v}_{s}") for v in VALID for s in ("ret", "via_dyld_dispatcher")]
    + [("S", f"{u}_{s}") for u in UNKNOWN for s in ("ret", "via_dyld_dispatcher", "reported_number")]
    + [("D", f"{v}_{s}") for v in VALID for s in ("raw", "entry", "registers")]
    + [("D", f"{u}_{s}") for u in UNKNOWN for s in ("raw", "entry", "registers", "reported_number")]
    + [("G", "nr599_control_read_detected")]
    + [("G", f"{u}_no_table_read") for u in ("nr600", "nr1000", "nr65535")]
    + [("W", f"{w}_{s}") for w in WRAPPERS for s in ("ret", "via_dyld_dispatcher")]
)
assert len(EXPECTED) == 98

CHECK_RE = re.compile(r"^X2 ([IPSDGW]) (\S+) (PASS|FAIL) ?(.*)$")
GUARD_RE = re.compile(r"^X2_INFO G_(nr\d+) .*\bentry=(0x[0-9a-f]+) .*\bstatus=(-?\d+) fault_addr=(0x[0-9a-f]+)")


def parse(record: Path):
    out = (record / "stdout.log").read_text(errors="replace").splitlines()
    err = (record / "stderr.log").read_text(errors="replace").splitlines()
    meta = (record / "meta.txt").read_text(errors="replace")
    rc = (record / "rc").read_text().strip()
    checks = {}
    for line in out:
        m = CHECK_RE.match(line)
        if m:
            checks[(m.group(1), m.group(2))] = (m.group(3), m.group(4))
    guards = {}
    for line in out:
        m = GUARD_RE.match(line)
        if m:
            guards[m.group(1)] = (int(m.group(2), 16), int(m.group(3)), int(m.group(4), 16))
    pre = {}
    for line in err:
        m = re.match(r"^PREFLIGHT (ns_kernel|ns_dyld)=([0-9a-f]{64})$", line)
        if m:
            pre[m.group(1)] = m.group(2)
    guest = {}
    for line in out:
        m = re.match(r"^X2_(DYLD|KERNEL)_SHA256 ([0-9a-f]{64})$", line)
        if m:
            guest[m.group(1)] = m.group(2)
    bound = None
    for line in out:
        m = re.match(r"^X2_INFO dyld_dispatcher bound_insn=(present|absent)", line)
        if m:
            bound = m.group(1)
    return out, meta, rc, checks, guards, pre, guest, bound


def verify(record: Path, expect: str, dyld_sha: str, kernel_sha: str):
    problems = []
    out, meta, rc, checks, guards, pre, guest, bound = parse(record)

    def need(cond, what):
        if not cond:
            problems.append(what)

    need(pre.get("ns_dyld") == dyld_sha, f"namespace dyld {pre.get('ns_dyld')} != {dyld_sha}")
    need(guest.get("DYLD") == dyld_sha, f"guest-computed dyld {guest.get('DYLD')} != {dyld_sha}")
    need(pre.get("ns_kernel") == kernel_sha, f"namespace kernel {pre.get('ns_kernel')} != {kernel_sha}")
    need(guest.get("KERNEL") == kernel_sha, f"guest-computed kernel {guest.get('KERNEL')} != {kernel_sha}")
    for key in EXPECTED:
        if key[0] in "IPW":
            need(checks.get(key, ("MISSING",))[0] == "PASS", f"{key[0]} {key[1]} not PASS")
    need(checks.get(("G", "nr599_control_read_detected"), ("MISSING",))[0] == "PASS",
         "guard control (nr599) did not detect the table read")
    m = re.search(r"host_mounts_before=(\d+)", meta)
    m2 = re.search(r"host_mounts_after=(\d+)", meta)
    need(m and m2 and m.group(1) == m2.group(1), "host mount count changed")
    need("darlingserver_after=0" in meta, "darlingserver left running")
    need("residual_prefix_processes=0" in meta, "residual prefix processes")

    if expect == "fixed":
        need(rc == "0", f"rc={rc}")
        need("X2_FINISHED_OK" in out, "X2_FINISHED_OK missing")
        need(any(l.startswith("X2_SUMMARY checks=98 failures=0 ") for l in out), "summary not 98/0")
        need(bound == "present", f"bound instruction {bound}")
        for key in EXPECTED:
            need(checks.get(key, ("MISSING",))[0] == "PASS", f"{key[0]} {key[1]} not PASS")
        need(set(checks) == set(EXPECTED), "unexpected or missing check names")
    else:
        need(rc == "10", f"rc={rc}")
        need(bound == "absent", f"bound instruction {bound}")
        reads = 0
        for nr in ("nr600", "nr1000", "nr65535"):
            g = guards.get(nr)
            if g and g[1] == 77 and g[2] == g[0]:
                reads += 1
        need(reads == 3, f"out-of-range table reads observed {reads}/3")
        st = checks.get(("S", "access_enoent_ret"), ("MISSING", ""))
        need(st[0] == "FAIL" and "ret=-2 errno=0" in st[1], "dyld syscall(2) stub did not return raw -ENOENT")
        rn = checks.get(("D", "nr8_reported_number"), ("MISSING", ""))
        need(rn[0] == "FAIL" and "Unimplemented_syscall_(" in rn[1], ".no_sys reported number not replaced")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record", type=Path)
    ap.add_argument("--expect", choices=("fixed", "defect"), required=True)
    ap.add_argument("--dyld-sha", required=True)
    ap.add_argument("--kernel-sha", required=True)
    a = ap.parse_args(argv)
    problems = verify(a.record, a.expect, a.dyld_sha, a.kernel_sha)
    name = a.record.name
    if problems:
        print(f"VERIFY {name} expect={a.expect} FAIL")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"VERIFY {name} expect={a.expect} PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
