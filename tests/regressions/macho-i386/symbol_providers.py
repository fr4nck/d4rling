#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only inventory of candidate i386 providers for Mach-O linker errors.

This finds symbol definitions in build artifacts. A definition is NOT evidence
that the full archive/dylib graph is linkable or that any API works at runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

_UNDEFINED = re.compile(r'^\s*"([^"]+)", referenced from:', re.MULTILINE)
_SYMBOL_KINDS = frozenset("ABCDGIRSTVW")
_CANDIDATE_WORDS = (
    "system", "libc", "malloc", "platform", "pthread", "compiler",
    "dispatch", "syscall", "kernel", "dyld", "launch", "libmacho",
)


def parse_undefined(log_text: str) -> set[str]:
    """Parse unresolved Mach-O symbols from ld64-style diagnostics."""
    return set(_UNDEFINED.findall(log_text))


def parse_definitions(nm_text: str) -> set[str]:
    """Read global definitions from llvm-nm -g --defined-only output."""
    definitions: set[str] = set()
    for line in nm_text.splitlines():
        fields = line.split()
        if (len(fields) >= 2 and fields[-2] in _SYMBOL_KINDS
                and fields[-1].startswith("_")):
            definitions.add(fields[-1])
    return definitions


def discover_candidates(root: Path) -> list[Path]:
    base = root / "src"
    if not base.is_dir():
        raise ValueError("expected existing build/src directory")
    files = set()
    for suffix in ("*.a", "*.dylib"):
        for path in base.rglob(suffix):
            if path.is_file() and any(x in path.name.lower() for x in _CANDIDATE_WORDS):
                files.add(path)
    return sorted(files, key=lambda p: str(p.relative_to(root)))


def _run(argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout, check=False, env={**os.environ, "LC_ALL": "C"},
    )


def _definitions_for_i386(
    source: Path, lipo: str, nm: str, timeout: int
) -> tuple[set[str] | None, str]:
    """Return i386 definitions; None means slice absent or inspection failed."""
    try:
        arch_result = _run([lipo, "-archs", str(source)], timeout)
        if arch_result.returncode != 0:
            return None, "lipo-error"
        archs = arch_result.stdout.split()
        if "i386" not in archs:
            return None, "no-i386-slice"

        if len(archs) == 1:
            target = source
            result = _run([nm, "-g", "--defined-only", str(target)], timeout)
        else:
            with tempfile.TemporaryDirectory(prefix="d4rling-i386-symbols-") as tmp:
                target = Path(tmp) / "slice.a"
                thin_result = _run([
                    lipo, str(source), "-thin", "i386", "-output", str(target)
                ], timeout)
                if thin_result.returncode != 0:
                    return None, "thin-error"
                result = _run([nm, "-g", "--defined-only", str(target)], timeout)
        if result.returncode != 0:
            return None, "nm-error"
        return parse_definitions(result.stdout), "scanned"
    except (OSError, subprocess.TimeoutExpired):
        return None, "tool-unavailable-or-timeout"


def inventory(
    link_logs: list[Path], build_dir: Path,
    *, lipo: str = "llvm-lipo-19", nm: str = "llvm-nm-19",
    max_candidates: int = 200, timeout: int = 8,
) -> dict:
    if max_candidates < 1 or timeout < 1:
        raise ValueError("max-candidates and timeout must be positive")
    log_sources = []
    missing: set[str] = set()
    for path in link_logs:
        payload = path.read_bytes()
        log_sources.append({
            "name": path.name,
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
        missing.update(parse_undefined(payload.decode("utf-8", errors="replace")))
    if not missing:
        raise ValueError("no quoted ld64 unresolved symbols in supplied logs")

    libraries = discover_candidates(build_dir)
    selected = libraries[:max_candidates]
    providers: dict[str, list[str]] = {key: [] for key in sorted(missing)}
    counts = {"scanned": 0, "no-i386-slice": 0, "failed": 0}
    failures = []
    for path in selected:
        definitions, reason = _definitions_for_i386(path, lipo, nm, timeout)
        if reason == "scanned":
            counts["scanned"] += 1
        elif reason == "no-i386-slice":
            counts["no-i386-slice"] += 1
        else:
            counts["failed"] += 1
            failures.append({"path": str(path.relative_to(build_dir)), "reason": reason})
        if definitions is None:
            continue
        for symbol in providers:
            if symbol in definitions:
                providers[symbol].append(str(path.relative_to(build_dir)))

    return {
        "schema_version": 1,
        "architecture": "i386",
        "source_logs": log_sources,
        "missing_symbols": sorted(missing),
        "providers": providers,
        "not_found_in_scanned_candidates": [
            symbol for symbol, found in providers.items() if not found
        ],
        "candidates_found": len(libraries),
        "candidates_considered": len(selected),
        "truncated": len(libraries) > len(selected),
        "scan_counts": counts,
        "scan_failures": failures,
        "qualifier": "symbol definitions only; not proof of link or runtime compatibility",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--link-log", type=Path, action="append", required=True)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--lipo", default="llvm-lipo-19")
    parser.add_argument("--nm", default="llvm-nm-19")
    parser.add_argument("--max-candidates", type=int, default=200)
    parser.add_argument("--timeout", type=int, default=8)
    parser.add_argument("--output", type=Path, help="new output file (refuses to overwrite)")
    args = parser.parse_args()
    try:
        report = inventory(
            args.link_log, args.build_dir,
            lipo=args.lipo, nm=args.nm,
            max_candidates=args.max_candidates, timeout=args.timeout,
        )
        payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output is None:
            print(payload, end="")
        else:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(payload)
            print(f"REPORT={args.output}")
        return 0
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
