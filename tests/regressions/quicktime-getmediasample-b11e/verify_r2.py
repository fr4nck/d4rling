#!/usr/bin/env python3
"""QT-B11E-R2 independent oracle for one GetMediaSample witness record.

  verify_r2.py RECORD OUT_DIR MOV_DIR [--guest INSTALL_ROOT]

RECORD has stdout.log, stderr.log, rc (and meta.txt for a guest run).
OUT_DIR holds gms-N.bin / gms-chunked-N.bin written by the witness.
MOV_DIR holds the six input MOV files (their SHA-256 must equal the ones the
witness computed in-process). The expected PCM is recomputed here in Python
from the B11E-R0 definitions and checked against the R0 SHA-256 table.
With --guest, the images reported by dladdr must be the QuickTime and
CarbonCore frameworks of INSTALL_ROOT (libexec/darling), and the record must
show no residual mount, darlingserver or prefix process.
"""
import argparse
import hashlib
import re
import struct
from pathlib import Path

R0_SHA256 = [
    "6d9c54dee5660c46886f32d80e57e9dd0ffa57ee0cd2a762b036d9c8e0c3a33a",
    "c6e3eb0c609db9a2ba21081313aeade0e232c7d5bda0856aeb3ce0e9f0eb98a0",
    "757822aae431f8297c566874401a9d6fe2051e8aea48250c706102ada66b46b6",
    "cd2a71d1d9498dd51998c76bb6f513a074eefbb19fc5598c4ab3b2e4c7886fdd",
    "f63ecff3fad32efde29bacdeef6b0ad65187ebc143455fa372edd314cf94644f",
    "c27c294c4100eb436c07d5da79fed4c7f1a214e14803512431f25ea94cec1f18",
]


def sample(mode, i):
    return [0, -1 if i & 1 else 1, 32767 if i == 0 else 0, -32768 if i & 1 else 32767,
            -32768 + (i * 65535) // 99, ((i * 7919 + i * i * 17 + 12345) & 65535) - 32768][mode]


def vector(mode):
    return b"".join(struct.pack(">h", sample(mode, i)) for i in range(100))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def verify(record, out_dir, mov_dir, guest=None, min_checks=137):
    problems = []

    def need(cond, what):
        if not cond:
            problems.append(what)

    out = (record / "stdout.log").read_text(errors="replace")
    err = (record / "stderr.log").read_text(errors="replace")
    rc = (record / "rc").read_text().strip()
    need(rc == "0", f"rc={rc}")
    m = re.search(r"^R2_SUMMARY checks=(\d+) failures=(\d+)$", out, re.M)
    need(m is not None and m.group(2) == "0" and int(m.group(1)) >= min_checks, f"summary {m.group(0) if m else None}")
    need("B11E_R2_WITNESS_OK" in out, "marker missing")
    need(not re.search(r"^R2 .* FAIL", out, re.M), "a check failed")
    need(not re.search(r"ERROR: (Address|Leak)Sanitizer|runtime error", err), "sanitizer report")
    for v in range(6):
        ref = vector(v)
        need(sha(ref) == R0_SHA256[v], f"python oracle v{v} != R0")
        for name in (f"gms-{v}.bin", f"gms-chunked-{v}.bin"):
            p = out_dir / name
            need(p.exists() and sha(p.read_bytes()) == R0_SHA256[v], f"{name} sha mismatch")
        mov = (mov_dir / f"mov-{v}.mov").read_bytes()
        need(re.search(rf"^R2_MOV v{v} bytes={len(mov)} sha256={sha(mov)}$", out, re.M) is not None,
             f"in-process MOV v{v} hash differs from the input file")
    if guest is not None:
        meta = (record / "meta.txt").read_text(errors="replace")
        a = re.search(r"host_mounts_before=(\d+)", meta)
        b = re.search(r"host_mounts_after=(\d+)", meta)
        need(a and b and a.group(1) == b.group(1), "host mount count changed")
        need("darlingserver_after=0" in meta, "darlingserver left running")
        need("residual_prefix_processes=0" in meta, "residual prefix processes")
        fw = guest / "System/Library/Frameworks"
        for sym, rel in (("GetMediaSample", "QuickTime.framework/Versions/A/QuickTime"),
                         ("GetHandleSize", "CoreServices.framework/Versions/A/Frameworks/CarbonCore.framework/Versions/A/CarbonCore")):
            mm = re.search(rf"^R2_IMAGE {sym} (\S+)$", out, re.M)
            need(mm is not None and mm.group(1).endswith("/" + rel), f"{sym} image {mm.group(1) if mm else None}")
            need((fw / rel).exists(), f"installed {rel} missing")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("record", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("mov_dir", type=Path)
    ap.add_argument("--guest", type=Path)
    a = ap.parse_args()
    problems = verify(a.record, a.out_dir, a.mov_dir, a.guest)
    print(f"VERIFY_R2 {a.record.name} {'FAIL' if problems else 'PASS'}")
    for p in problems:
        print("  -", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
