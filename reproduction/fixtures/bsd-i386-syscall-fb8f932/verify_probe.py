#!/usr/bin/env python3
"""Check a run-guest.sh record of bsd-i386-probe against an expected verdict.

--expect fixed   every probe check passes (patched libsystem_kernel)
--expect defect  the unpatched darling-xnu fb8f932 signature: ordinary stubs
                 and 64-bit lseek pass (sections A and B), while syscall(2),
                 unknown numbers, the LDT wrappers and syscall(2) errno under
                 threads fail (sections C, D, E, F)

The bench itself must be clean in both cases: setgroups allowed and probed,
no residual process or darlingserver, host mount count unchanged.
Exit status 0 when the record matches, 1 otherwise.
"""
import argparse
import re
import sys
from pathlib import Path

A_NAMES = ["open_create", "access_ok", "access_ENOENT", "stat64_ok", "stat64_ENOENT",
           "lstat64_ok", "lstat64_ENOENT", "realpath_ok", "realpath_ENOENT",
           "getattrlist_ok", "getattrlist_ENOENT", "getattrlist_EINVAL"]
B_OFFSETS = ["1fffffffe", "2fffff001", "3fffff000", "7fffffff", "80000000"]
B_NAMES = [f"lseek64_{k}_{o}" for o in B_OFFSETS for k in ("set", "cur")] + ["lseek_EINVAL", "lseek_EBADF"]
C_NAMES = ["syscall_getpid", "syscall_access_ok", "syscall_access_ENOENT", "syscall_close_EBADF"]
UNKNOWN = [8, 599, 600, 1000, 65535]
D_NAMES = [n for nr in UNKNOWN for n in (f"unknown_{nr}", f"unknown_{nr}_reported_number")]
E_NAMES = ["i386_get_ldt_error", "i386_get_ldt_reported_trap", "i386_set_ldt_error", "i386_set_ldt_reported_trap"]
F_NAMES = ["threads_created", "threads_calls", "threads_errno_stubs", "threads_errno_syscall"]
ALL = {"A": A_NAMES, "B": B_NAMES, "C": C_NAMES, "D": D_NAMES, "E": E_NAMES, "F": F_NAMES}
LINE = re.compile(r"^BSDP ([A-F]) (\S+) (PASS|FAIL)(?: (.*))?$")


def parse(run: Path):
    out = (run / "stdout.log").read_text(errors="replace").splitlines()
    err = (run / "stderr.log").read_text(errors="replace").splitlines()
    meta = (run / "meta.txt").read_text(errors="replace").splitlines()
    rc = (run / "rc").read_text().strip()
    checks = {}
    dup = []
    for line in out:
        m = LINE.match(line)
        if m:
            key = (m.group(1), m.group(2))
            if key in checks:
                dup.append(key)
            checks[key] = (m.group(3), m.group(4) or "")
    return out, err, meta, rc, checks, dup


def verify(run: Path, expect: str, kernel_sha: str = None):
    problems = []
    try:
        out, err, meta, rc, checks, dup = parse(run)
    except (OSError, UnicodeError) as exc:
        return [f"unreadable record: {exc}"]
    if dup:
        problems.append(f"duplicate checks: {dup}")
    kv = {}
    for line in meta:
        for part in line.split():
            if "=" in part:
                k, v = part.split("=", 1)
                kv.setdefault(k, v)
    if "PREFLIGHT setgroups=allow" not in err or "PREFLIGHT probe=OK" not in err:
        problems.append("setgroups preflight missing or not allowed")
    if kv.get("residual_prefix_processes") != "0":
        problems.append(f"residual processes: {kv.get('residual_prefix_processes')}")
    if kv.get("darlingserver_after") not in ("0", ""):
        problems.append(f"darlingserver left running: {kv.get('darlingserver_after')}")
    if kv.get("host_mounts_before") != kv.get("host_mounts_after"):
        problems.append("host mount count changed")
    if kernel_sha:
        seen = [l.split("=", 1)[1] for l in err if l.startswith("PREFLIGHT ns_kernel=")]
        if seen != [kernel_sha]:
            problems.append(f"namespace kernel {seen} != expected {kernel_sha}")
    if not any(l.startswith("BSDP_STARTED") for l in out):
        problems.append("probe did not start")

    expected = [(s, n) for s, names in ALL.items() for n in names]
    missing = [k for k in expected if k not in checks]
    extra = [k for k in checks if k not in expected]
    if extra:
        problems.append(f"unexpected checks: {extra}")

    def status(s, n):
        return checks.get((s, n), (None, ""))[0]

    if expect == "fixed":
        if missing:
            problems.append(f"missing checks: {missing}")
        fails = [k for k, v in checks.items() if v[0] != "PASS"]
        if fails:
            problems.append(f"failed checks: {fails}")
        if rc != "0":
            problems.append(f"rc={rc}, expected 0")
        if f"BSDP_SUMMARY checks={len(expected)} failures=0" not in "\n".join(out):
            problems.append("summary is not all-pass")
        if "BSDP_FINISHED_OK" not in out:
            problems.append("no BSDP_FINISHED_OK")
    elif expect == "defect":
        # A crashing unknown-number child yields one check instead of two.
        core_missing = [k for k in missing if not (k[0] == "D" and k[1].endswith("_reported_number"))]
        if core_missing:
            problems.append(f"missing checks: {core_missing}")
        for s in ("A", "B"):
            bad = [n for n in ALL[s] if status(s, n) != "PASS"]
            if bad:
                problems.append(f"section {s} must pass on fb8f932: {bad}")
        for name, want in (("syscall_access_ENOENT", "ret=-2 errno=0"), ("syscall_close_EBADF", "ret=-9 errno=0")):
            st, detail = checks.get(("C", name), (None, ""))
            if st != "FAIL" or want not in detail:
                problems.append(f"C {name}: expected raw -errno FAIL ({want}), got {st} {detail}")
        for n in ("syscall_getpid", "syscall_access_ok"):
            if status("C", n) != "PASS":
                problems.append(f"C {n} should pass")
        # Empty slots inside the table go to .no_sys: raw -ENOSYS, errno untouched.
        for nr in (n for n in UNKNOWN if n < 600):
            st, detail = checks.get(("D", f"unknown_{nr}"), (None, ""))
            if st != "FAIL" or "ret=-78 errno=0" not in detail:
                problems.append(f"D unknown_{nr}: expected raw -ENOSYS, got {st} {detail}")
        # Numbers >= 600 read past the table: the outcome depends on the memory
        # found there (raw -ENOSYS, a crash, or an unrelated handler), but never
        # the documented -1/ENOSYS.
        for nr in (n for n in UNKNOWN if n >= 600):
            st, detail = checks.get(("D", f"unknown_{nr}"), (None, ""))
            if st != "FAIL":
                problems.append(f"D unknown_{nr}: expected a failure past the table, got {st} {detail}")
        for n in ("i386_get_ldt_error", "i386_set_ldt_error"):
            st, detail = checks.get(("E", n), (None, ""))
            if st != "FAIL" or "ret=-78 errno=0" not in detail:
                problems.append(f"E {n}: expected raw -78, got {st} {detail}")
        for n in ("i386_get_ldt_reported_trap", "i386_set_ldt_reported_trap"):
            if status("E", n) != "FAIL":
                problems.append(f"E {n} should fail (table address reported)")
        if status("F", "threads_errno_syscall") != "FAIL":
            problems.append("F threads_errno_syscall should fail")
        for n in ("threads_created", "threads_calls", "threads_errno_stubs"):
            if status("F", n) != "PASS":
                problems.append(f"F {n} should pass")
        if rc != "10":
            problems.append(f"rc={rc}, expected 10")
    else:
        problems.append(f"unknown expectation {expect}")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("--expect", required=True, choices=["fixed", "defect"])
    ap.add_argument("--kernel-sha", help="SHA-256 the namespace must report for libsystem_kernel.dylib")
    args = ap.parse_args(argv)
    problems = verify(args.run, args.expect, args.kernel_sha)
    if problems:
        print(f"VERIFY FAIL {args.run.name} expect={args.expect}")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"VERIFY PASS {args.run.name} expect={args.expect}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
