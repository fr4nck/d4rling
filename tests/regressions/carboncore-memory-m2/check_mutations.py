#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Kill contract-breaking M2 mutations in temporary source copies.

Only the real production translation unit is mutated; no installed Darling or
repository file is modified. A mutation passes only when its test fails for a
contract assertion (not a compiler error, missing tool or sanitizer crash).
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "src/frameworks/CoreServices/src/CarbonCore/MacMemory.cpp"
RUNNER = Path(__file__).with_name("run.sh")
MUTANTS = (
    ("EmptyHandle locked false success",
     "if (state->locked) { g_memoryError = memPurErr; return; }",
     "if (state->locked) { g_memoryError = noErr; return; }"),
    ("ReallocateHandle locked false success",
     "if (*handle && state->locked) { g_memoryError = memPurErr; return; }",
     "if (*handle && state->locked) { g_memoryError = noErr; return; }"),
    ("DisposePtr handle-owned false success",
     "if ((*slot)->owner) { g_memoryError = memAdrErr; return; }",
     "if ((*slot)->owner) { g_memoryError = noErr; return; }"),
    ("GetHandleSize forged owner accepted",
     "if (!record || record->owner != handle) { g_memoryError = memWZErr; return 0; }",
     "if (!record) { g_memoryError = memWZErr; return 0; }"),
    ("SetHandleSize empty false success",
     "if (newSize < 0) { g_memoryError = memFullErr; return; }\n    if (!*handle) { g_memoryError = nilHandleErr; return; }",
     "if (newSize < 0) { g_memoryError = memFullErr; return; }\n    if (!*handle) { g_memoryError = noErr; return; }"),
)


def main() -> int:
    compiler = sys.argv[1] if len(sys.argv) > 1 else "g++"
    real = SOURCE.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="d4-carbon-m2-mutants-") as temp:
        for number, (label, anchor, changed) in enumerate(MUTANTS, 1):
            if real.count(anchor) != 1:
                raise RuntimeError(f"mutation {number} anchor count != 1")
            mutant = Path(temp) / f"mutant-{number}.cpp"
            mutant.write_text(real.replace(anchor, changed, 1), encoding="utf-8")
            env = dict(os.environ, D4_M2_TEST_SOURCE=str(mutant))
            run = subprocess.run(
                ["bash", str(RUNNER), compiler],
                env=env, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False, timeout=60,
            )
            if run.returncode != 1 or "FAIL " not in run.stderr:
                raise RuntimeError(f"mutation {number} not killed by assertions: {label}\n"
                                   f"rc={run.returncode}\n{run.stdout[-1200:]}\n{run.stderr[-1500:]}")
            print(f"M2_MUTANT_{number}_KILLED: {label}")
    print(f"M2_MUTANTS: {len(MUTANTS)}/{len(MUTANTS)} killed by host contracts ({compiler})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("BLOCKED:", str(exc), file=sys.stderr)
        sys.exit(2)
