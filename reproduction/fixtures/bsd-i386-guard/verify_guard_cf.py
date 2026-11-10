#!/usr/bin/env python3
"""Fail-closed proof gate for isolated Darwin-i386 dispatcher/CF experiments.

This validates records, not a real XNU library or the guest execution itself.
The fixed no-CMC mutant has an independent, native x86 failure-count oracle.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys

CASES = ("positive", "mutant")
COUNT = 222
MUTANT_FAILURES = 71
MANIFEST_ITEMS = tuple(
    f"{case}.{suffix}"
    for case in CASES
    for suffix in ("stdout.log", "stderr.log", "exit-code.txt")
) + ("probe-positive", "probe-mutant")

EXPECTED_UNKNOWN = (8, 8 | (12 << 16), 598, 600, 65535, 0xFFFFFFFF, 600 | (53 << 16))
EXPECTED_KNOWN = (
    (33, 0), (33, 0x12345678), (33 | (20 << 16), 0xFFFFF000),
    (599, 0x80000000), (33, 0xFFFFEFFF), (33, 0xFFFFF001),
    (33, 0xFFFFFFB2), (33, 0xFFFFFFFE), (33, 0xFFFFFFFF),
)


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    if not root.is_dir():
        return ["missing result directory"]

    for case, expected_rc, expected_failures in (
        ("positive", 0, 0), ("mutant", 10, MUTANT_FAILURES)
    ):
        try:
            stdout = (root / f"{case}.stdout.log").read_text(encoding="utf-8")
            (root / f"{case}.stderr.log").read_bytes()
            exit_code = (root / f"{case}.exit-code.txt").read_text(encoding="ascii").strip()
        except (OSError, UnicodeError) as exc:
            errors.append(f"{case}: missing/undecodable evidence: {exc}")
            continue

        if exit_code != str(expected_rc):
            errors.append(f"{case}: exit code {exit_code!r} != {expected_rc}")
        lines = stdout.splitlines()
        for marker in ("B15_ACTIVE_HASHES=PASS", "GUARD_CF_BEGIN",
                       "GUARD_CF_FINISHED", f"GUARD_CF_EXIT={expected_rc}"):
            if lines.count(marker) != 1:
                errors.append(f"{case}: expected exactly one {marker!r}")

        summary_lines = [line for line in lines if line.startswith("GUARD_CF_CHECKS=")]
        summary = re.fullmatch(r"GUARD_CF_CHECKS=(\d+) FAILURES=(\d+)", summary_lines[0]) \
            if len(summary_lines) == 1 else None
        if summary is None:
            errors.append(f"{case}: missing/duplicate/invalid summary")
        else:
            checks, failures = map(int, summary.groups())
            if checks != COUNT or failures != expected_failures:
                errors.append(f"{case}: expected {COUNT} checks/{expected_failures} failures, "
                              f"got {checks}/{failures}")

        failures_logged = [line for line in lines if line.startswith("GUARD_CF_FAIL=")]
        if case == "positive" and failures_logged:
            errors.append("positive: contradictory failure record")
        if case == "mutant":
            if not failures_logged:
                errors.append("mutant: no failure record")
            if not any(line.startswith("GUARD_CF_FAIL=KNOWN_CHECKED_") for line in failures_logged):
                errors.append("mutant: no evidence of broken checked-return path")

        if any(line.startswith("GUARD_CF_EXIT=") and line != f"GUARD_CF_EXIT={expected_rc}"
               for line in lines):
            errors.append(f"{case}: contradictory guest exit marker")

        observed_known = [tuple(map(int, m.groups())) for line in lines
                          if (m := re.fullmatch(r"GUARD_CF_KNOWN=(\d+) RAW=(\d+)", line))]
        if observed_known != list(EXPECTED_KNOWN):
            errors.append(f"{case}: wrong known syscall coverage")
        observed_unknown = [tuple(map(int, m.groups())) for line in lines
                            if (m := re.fullmatch(r"GUARD_CF_UNKNOWN=(\d+) MASKED=(\d+)", line))]
        if observed_unknown != [(nr, nr & 0xFFFF) for nr in EXPECTED_UNKNOWN]:
            errors.append(f"{case}: wrong unknown syscall coverage")

    try:
        records = (root / "SHA256SUMS").read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as exc:
        return errors + [f"missing/unreadable SHA256SUMS: {exc}"]

    seen = set()
    expected = set(MANIFEST_ITEMS)
    for line in records:
        match = re.fullmatch(r"([a-f0-9]{64})  ([^/\s]+)", line)
        if match is None:
            errors.append("malformed SHA256SUMS entry")
            continue
        digest, name = match.groups()
        if name not in expected or name in seen:
            errors.append(f"unexpected/duplicate evidence entry: {name}")
            continue
        seen.add(name)
        target = root / name
        if target.is_symlink() or not target.is_file():
            errors.append(f"nonregular evidence file: {name}")
            continue
        try:
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
        except OSError as exc:
            errors.append(f"unreadable evidence file {name}: {exc}")
            continue
        if actual != digest:
            errors.append(f"SHA256 mismatch: {name}")
    if seen != expected:
        errors.append(f"manifest inventory mismatch, missing: {sorted(expected-seen)}")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: verify_guard_cf.py RESULT_DIRECTORY", file=sys.stderr)
        return 2
    root = Path(argv[1])
    errors = validate(root)
    print("GUARD_CF_RUNTIME=" + ("PASS_BOUNDED" if not errors else "NOT_QUALIFIED"))
    print(f"RESULT_DIR={root}")
    for error in errors:
        print(f"GUARD_CF_VERIFY_FAIL={error}", file=sys.stderr)
    return 0 if not errors else 10


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
