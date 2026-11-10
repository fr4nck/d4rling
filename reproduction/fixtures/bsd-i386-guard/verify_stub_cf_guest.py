#!/usr/bin/env python3
"""Validate the bounded Darling i386 CF guest run and its local evidence.

This verifies the result contract; it does not execute the guest or prove
that the mirrored assembly is the actual upstream XNU stub.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys

EXPECTED_FILES = ('stub-cf-guest', 'guest.stdout.log', 'guest.stderr.log')
EXPECTED_MARKERS = (
    'B15_ACTIVE_HASHES=PASS',
    'STUB_CF_GUEST_BEGIN',
    'STUB_CF_GUEST_CHECKS=12 FAILURES=0',
    'STUB_CF_GUEST_FINISHED',
    'STUB_CF_GUEST_EXIT=0',
)


def validate_result(directory: Path) -> list[str]:
    """List validation failures, never removing or altering the evidence."""
    problems: list[str] = []
    if not directory.is_dir():
        return [f'result directory is missing: {directory}']
    try:
        stdout = (directory / 'guest.stdout.log').read_text(encoding='utf-8')
        (directory / 'guest.stderr.log').read_bytes()
        rc = (directory / 'guest.exit-code.txt').read_text(encoding='ascii').strip()
    except (OSError, UnicodeError) as exc:
        return [f'missing or unreadable evidence: {exc}']

    if rc != '0':
        problems.append(f'guest return code must be 0, got {rc!r}')
    lines = stdout.splitlines()
    for marker in EXPECTED_MARKERS:
        if lines.count(marker) != 1:
            problems.append(f'expected one exact marker {marker!r}, found {lines.count(marker)}')
    if any(re.match(r'^STUB_CF_GUEST_CASE=\d+\s+FAIL\b', line) for line in lines):
        problems.append('guest reported a failed case')
    count_lines = [line for line in lines if line.startswith('STUB_CF_GUEST_CHECKS=')]
    if count_lines != ['STUB_CF_GUEST_CHECKS=12 FAILURES=0']:
        problems.append(f'unexpected checks summary: {count_lines!r}')
    if any(line.startswith('STUB_CF_GUEST_EXIT=') and line != 'STUB_CF_GUEST_EXIT=0' for line in lines):
        problems.append('contradictory guest exit marker')

    manifest = directory / 'SHA256SUMS'
    try:
        records = manifest.read_text(encoding='ascii').splitlines()
    except (OSError, UnicodeError) as exc:
        return problems + [f'missing or unreadable checksum manifest: {exc}']
    expected = {str(directory / filename): filename for filename in EXPECTED_FILES}
    seen: set[str] = set()
    for record in records:
        match = re.fullmatch(r'([a-f0-9]{64})  (.+)', record)
        if not match:
            problems.append('malformed SHA-256 record')
            continue
        digest, path = match.groups()
        if path not in expected or path in seen:
            problems.append(f'unexpected or duplicate manifest path {path!r}')
            continue
        seen.add(path)
        entry = Path(path)
        if entry.is_symlink() or not entry.is_file():
            problems.append(f'not a regular evidence file: {path}')
            continue
        try:
            data_digest = hashlib.sha256(entry.read_bytes()).hexdigest()
        except OSError as exc:
            problems.append(f'unreadable evidence file {path}: {exc}')
            continue
        if digest != data_digest:
            problems.append(f'checksum mismatch: {path}')
    if seen != set(expected):
        problems.append('SHA256SUMS does not enumerate exactly the three expected files')
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print('usage: verify_stub_cf_guest.py RESULT_DIR', file=sys.stderr)
        return 2
    directory = Path(argv[1])
    problems = validate_result(directory)
    print('STUB_CF_GUEST_RUNTIME=' + ('PASS_BOUNDED' if not problems else 'NOT_QUALIFIED'))
    print(f'RESULT_DIR={directory}')
    for problem in problems:
        print(f'STUB_CF_GUEST_VERIFY_FAIL={problem}', file=sys.stderr)
    return 0 if not problems else 10


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
