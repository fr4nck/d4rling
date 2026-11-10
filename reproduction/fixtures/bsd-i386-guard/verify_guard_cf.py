#!/usr/bin/env python3
"""Fail-closed verifier for bounded i386 dispatcher+CF guest and CF mutant.

The guest must use the B15 private overlay. This verifier only checks
records produced by the runner; it does not execute Darling itself.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys

CASES = ('positive', 'mutant')
MANIFEST_ITEMS = tuple(f'{case}.{extension}' for case in CASES for extension in
                       ('stdout.log', 'stderr.log')) + ('probe-positive', 'probe-mutant')
COUNT = 222


def validate(root: Path) -> list[str]:
    problems: list[str] = []
    if not root.is_dir():
        return ['missing result directory']
    for case, expected_rc in (('positive', 0), ('mutant', 10)):
        try:
            text = (root / f'{case}.stdout.log').read_text(encoding='utf-8')
            (root / f'{case}.stderr.log').read_bytes()
            rc = (root / f'{case}.exit-code.txt').read_text(encoding='ascii').strip()
        except (UnicodeError, OSError) as exc:
            problems.append(f'{case}: missing or undecodable evidence: {exc}')
            continue
        if rc != str(expected_rc):
            problems.append(f'{case}: return code {rc!r} instead of {expected_rc}')
        lines = text.splitlines()
        for marker in ('B15_ACTIVE_HASHES=PASS', 'GUARD_CF_BEGIN',
                       'GUARD_CF_FINISHED', f'GUARD_CF_EXIT={expected_rc}'):
            if lines.count(marker) != 1:
                problems.append(f'{case}: expected one {marker!r}')
        summary = [re.fullmatch(r'GUARD_CF_CHECKS=(\d+) FAILURES=(\d+)', line)
                   for line in lines if line.startswith('GUARD_CF_CHECKS=')]
        if len(summary) != 1 or summary[0] is None:
            problems.append(f'{case}: invalid or duplicate summary')
        else:
            checks, failures = map(int, summary[0].groups())
            if checks != COUNT:
                problems.append(f'{case}: expected {COUNT} checks, got {checks}')
            if case == 'positive' and failures != 0:
                problems.append(f'{case}: unexpected failures={failures}')
            if case == 'mutant' and failures < 1:
                problems.append(f'{case}: mutant was not detected')
            if case == 'mutant' and not any(line.startswith('GUARD_CF_FAIL=') for line in lines):
                problems.append(f'{case}: no failure witness')
        if any(line.startswith('GUARD_CF_EXIT=') and line != f'GUARD_CF_EXIT={expected_rc}'
               for line in lines):
            problems.append(f'{case}: contradictory exit marker')
        if case == 'positive' and any(line.startswith('GUARD_CF_FAIL=') for line in lines):
            problems.append('positive: contradictory failure record')
        expected_unknowns = [8, 8 | (12 << 16), 598, 600, 65535, 0xffffffff, 600 | (53 << 16)]
        unknowns = [tuple(map(int, m.groups())) for line in lines
                    if (m := re.fullmatch(r'GUARD_CF_UNKNOWN=(\d+) MASKED=(\d+)', line))]
        if unknowns != [(nr, nr & 0xffff) for nr in expected_unknowns]:
            problems.append(f'{case}: wrong unknown syscall coverage')
        knowns = [tuple(map(int, m.groups())) for line in lines
                  if (m := re.fullmatch(r'GUARD_CF_KNOWN=(\d+) RAW=(\d+)', line))]
        expected_known = [(33, 0), (33, 0x12345678), (33 | (20 << 16), 0xfffff000),
                          (599, 0x80000000), (33, 0xffffefff), (33, 0xfffff001),
                          (33, 0xffffffb2), (33, 0xfffffffe), (33, 0xffffffff)]
        if knowns != expected_known:
            problems.append(f'{case}: wrong known syscall coverage')
    try:
        entries = (root / 'SHA256SUMS').read_text(encoding='ascii').splitlines()
    except (UnicodeError, OSError) as exc:
        return problems + [f'no readable SHA256SUMS: {exc}']
    seen = set()
    expected = set(MANIFEST_ITEMS)
    for entry in entries:
        match = re.fullmatch(r'([a-f0-9]{64})  ([^/\s]+)', entry)
        if match is None:
            problems.append('malformed SHA256SUMS line')
            continue
        digest, name = match.groups()
        if name not in expected or name in seen:
            problems.append(f'unexpected or duplicate checksum file: {name}')
            continue
        seen.add(name)
        target = root / name
        if target.is_symlink() or not target.is_file():
            problems.append(f'not an ordinary evidence file: {name}')
            continue
        try:
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
        except OSError:
            problems.append(f'cannot read: {name}')
            continue
        if digest != actual:
            problems.append(f'checksum mismatch: {name}')
    if seen != expected:
        problems.append(f'missing manifest entries: {sorted(expected - seen)}')
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print('usage: verify_guard_cf.py RESULT_DIRECTORY', file=sys.stderr)
        return 2
    root = Path(argv[1])
    errors = validate(root)
    print('GUARD_CF_RUNTIME=' + ('PASS_BOUNDED' if not errors else 'NOT_QUALIFIED'))
    print(f'RESULT_DIR={root}')
    for error in errors:
        print(f'GUARD_CF_VERIFY_FAIL={error}', file=sys.stderr)
    return 0 if not errors else 10


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
