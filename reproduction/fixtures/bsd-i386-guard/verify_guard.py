#!/usr/bin/env python3
"""Validate bounded BSD i386 dispatcher fixtures without executing guests."""
from __future__ import annotations

import pathlib
import re
import sys

EXPECTED_KNOWN = (33, 33 | (20 << 16), 599)
EXPECTED_ORIGINAL = (8, 8 | (12 << 16), 598)
EXPECTED_CANDIDATE = EXPECTED_ORIGINAL + (
    600, 65535, 0xFFFFFFFF, 600 | (53 << 16)
)
EXPECTED_COUNTS = {"original": 34, "candidate": 61}


def validate_case(root: pathlib.Path, variant: str) -> list[str]:
    """Return problems, keeping the raw outputs for subsequent inspection."""
    if variant not in EXPECTED_COUNTS:
        raise ValueError(f"unknown variant: {variant}")
    errors = []
    log_path = root / f"{variant}.stdout.log"
    rc_path = root / f"{variant}.exit-code.txt"
    try:
        text = log_path.read_text(encoding="utf-8")
        rc_text = rc_path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError) as exc:
        return [f"missing/invalid output: {exc}"]
    if rc_text != "0":
        errors.append(f"guest exit code {rc_text!r} != 0")
    mode = variant.upper()
    for marker in ("B15_ACTIVE_HASHES=PASS", f"GUARD_RUNTIME_BEGIN MODE={mode}",
                   "GUARD_FINISHED", "FIXTURE_EXIT=0", "CASE=ARGUMENT_FORWARDING"):
        if text.splitlines().count(marker) != 1:
            errors.append(f"expected exactly one {marker!r}")
    matches = re.findall(r"^GUARD_CHECKS=(\d+) GUARD_FAILURES=(\d+)$", text, re.M)
    if matches != [(str(EXPECTED_COUNTS[variant]), "0")]:
        errors.append(f"incorrect GUARD_CHECKS/FAILURES {matches!r}")
    checks = re.findall(r"^CHECK ([A-Z0-9_]+)=(PASS|FAIL)$", text, re.M)
    if len(checks) != EXPECTED_COUNTS[variant] or any(status != "PASS" for _, status in checks):
        errors.append(f"expected {EXPECTED_COUNTS[variant]} PASS check lines, got {len(checks)}")
    known = [int(n) for n in re.findall(r"^CASE=KNOWN NR=(\d+)$", text, re.M)]
    if known != list(EXPECTED_KNOWN):
        errors.append(f"incorrect known cases: {known!r}")
    unknown = [(int(n), int(masked)) for n, masked in re.findall(
        r"^CASE=UNKNOWN NR=(\d+) MASKED=(\d+)$", text, re.M
    )]
    expected = EXPECTED_ORIGINAL if variant == "original" else EXPECTED_CANDIDATE
    if unknown != [(nr, nr & 0xFFFF) for nr in expected]:
        errors.append(f"incorrect unknown cases: {unknown!r}")
    expected_check_counts = {
        "I386_POINTER_SIZE": 1,
        "KNOWN_EAX": 3, "KNOWN_EDX": 3, "KNOWN_CF": 3,
        "KNOWN_STACK": 3, "KNOWN_HANDLER": 3,
        "FORWARD_14_ARGUMENTS": 1, "FORWARD_ALIGNMENT": 1,
        "FORWARD_STACK": 1,
        "UNKNOWN_HANDLER_CALLED": len(expected),
        "UNKNOWN_RAW_ENOSYS": len(expected),
        "UNKNOWN_RAW_CF": len(expected),
        "UNKNOWN_STACK": len(expected),
    }
    if variant == "original":
        expected_check_counts["ORIGINAL_NUMBER_BUG_REPRODUCED"] = len(expected)
    else:
        expected_check_counts["CORRECTED_NUMBER"] = len(expected)
        expected_check_counts["CORRECTED_CALL_ALIGNMENT"] = len(expected)
    actual_counts = {}
    for name, _ in checks:
        actual_counts[name] = actual_counts.get(name, 0) + 1
    if actual_counts != expected_check_counts:
        errors.append(f"incorrect check inventory: {actual_counts!r}")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: verify_guard.py RESULT_DIRECTORY", file=sys.stderr)
        return 2
    root = pathlib.Path(argv[1])
    all_ok = True
    for variant in ("original", "candidate"):
        problems = validate_case(root, variant)
        ok = not problems
        all_ok &= ok
        print(f"{variant.upper()}_RUNTIME={'PASS' if ok else 'FAIL_OR_BLOCKED'}")
        for problem in problems:
            print(f"{variant}: {problem}", file=sys.stderr)
    print(f"GUARD_RUNTIME={'PASS_BOUNDED' if all_ok else 'NOT_QUALIFIED'}")
    print(f"RESULT_DIR={root}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
