#!/usr/bin/env python3
"""QT-B11E-R1 independent oracle for one run of b11e-r1-native.

  verify_r1.py RUN_DIR

RUN_DIR holds stdout.log, stderr.log, rc and the files written by the
witness (mov-N.mov, pcm-N.bin, pcm-5-bitflip.bin).

The expected PCM is computed here in Python from the B11E-R0 definitions and
must also equal the SHA-256 published in docs/evidence (B11E-R0 table), so the
oracle does not depend on the C witness. The MOV files are checked against
the R0 contract: 761 bytes, 200 PCM bytes at offset 44, all six identical
outside the samples. A 1-bit mutant of the extracted PCM must be rejected.
"""
import hashlib
import re
import struct
import sys
from pathlib import Path

R0_SHA256 = [
    "6d9c54dee5660c46886f32d80e57e9dd0ffa57ee0cd2a762b036d9c8e0c3a33a",
    "c6e3eb0c609db9a2ba21081313aeade0e232c7d5bda0856aeb3ce0e9f0eb98a0",
    "757822aae431f8297c566874401a9d6fe2051e8aea48250c706102ada66b46b6",
    "cd2a71d1d9498dd51998c76bb6f513a074eefbb19fc5598c4ab3b2e4c7886fdd",
    "f63ecff3fad32efde29bacdeef6b0ad65187ebc143455fa372edd314cf94644f",
    "c27c294c4100eb436c07d5da79fed4c7f1a214e14803512431f25ea94cec1f18",
]
MOV_LEN, PCM_OFF, PCM_LEN = 761, 44, 200


def sample(mode, i):
    return [0, -1 if i & 1 else 1, 32767 if i == 0 else 0, -32768 if i & 1 else 32767,
            -32768 + (i * 65535) // 99, ((i * 7919 + i * i * 17 + 12345) & 65535) - 32768][mode]


def vector(mode):
    return b"".join(struct.pack(">h", sample(mode, i)) for i in range(100))


def verify(run: Path):
    problems = []

    def need(cond, what):
        if not cond:
            problems.append(what)

    out = (run / "stdout.log").read_text(errors="replace")
    err = (run / "stderr.log").read_text(errors="replace")
    rc = (run / "rc").read_text().strip()
    need(rc == "0", f"rc={rc}")
    need("B11E_R1_WITNESS_OK" in out, "witness marker missing")
    need(re.search(r"^R1_SUMMARY checks=\d+ failures=0$", out, re.M) is not None, "R1 summary not 0 failures")
    need(re.search(r"^checks=\d+ failures=0$", out, re.M) is not None, "E1 regression not 0 failures")
    need(re.search(r"^E1_RC=0$", out, re.M) is not None, "E1 rc")
    need(not re.search(r"^R1 .* FAIL ", out, re.M), "a R1 check failed")
    need(not re.search(r"ERROR: (Address|Leak)Sanitizer|runtime error", err), "sanitizer report")
    movs = []
    for v in range(6):
        ref = vector(v)
        need(hashlib.sha256(ref).hexdigest() == R0_SHA256[v], f"python oracle v{v} != R0 table")
        pcm = (run / f"pcm-{v}.bin").read_bytes() if (run / f"pcm-{v}.bin").exists() else b""
        need(hashlib.sha256(pcm).hexdigest() == R0_SHA256[v], f"extracted pcm v{v} sha mismatch")
        mov = (run / f"mov-{v}.mov").read_bytes() if (run / f"mov-{v}.mov").exists() else b""
        need(len(mov) == MOV_LEN, f"mov v{v} length {len(mov)}")
        need(mov[PCM_OFF:PCM_OFF + PCM_LEN] == ref, f"mov v{v} samples not at offset 44")
        need(mov[PCM_OFF - 16:PCM_OFF] == bytes(16) and mov[PCM_OFF + PCM_LEN:PCM_OFF + PCM_LEN + 16] == bytes(16),
             f"mov v{v} guard bytes")
        need(mov[24:28] == b"mdat" and struct.unpack(">I", mov[20:24])[0] == 8 + 16 + PCM_LEN + 16,
             f"mov v{v} mdat header")
        stco = mov.find(b"stco")
        need(stco > 0 and struct.unpack(">I", mov[stco + 12:stco + 16])[0] == PCM_OFF, f"mov v{v} stco")
        movs.append(mov)
    for v in range(1, 6):
        need(movs[v][:PCM_OFF] == movs[0][:PCM_OFF] and
             movs[v][PCM_OFF + PCM_LEN:] == movs[0][PCM_OFF + PCM_LEN:], f"mov v{v} metadata differs from v0")
    flip = run / "pcm-5-bitflip.bin"
    need(flip.exists() and hashlib.sha256(flip.read_bytes()).hexdigest() != R0_SHA256[5],
         "1-bit PCM mutant not rejected by the oracle")
    if flip.exists():
        diff = [i for i, (a, b) in enumerate(zip(flip.read_bytes(), vector(5))) if a != b]
        need(diff == [37] and bin(flip.read_bytes()[37] ^ vector(5)[37]).count("1") == 1, "mutant is not one bit")
    return problems


def main():
    run = Path(sys.argv[1])
    problems = verify(run)
    print(f"VERIFY_R1 {run.name} {'FAIL' if problems else 'PASS'}")
    for p in problems:
        print("  -", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
