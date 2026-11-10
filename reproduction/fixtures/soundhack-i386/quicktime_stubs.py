#!/usr/bin/env python3
"""Read-only source witness for SoundHack 0.896's QuickTime playback path.

The report identifies explicit STUB markers; absence of a marker is NOT a
functional or ABI compatibility claim. GPL-3.0-or-later.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

# Calls from tomerbe/SoundHack@df6f0bc, SoundFile/Play.c (Start/Update/StopQTPlay).
PLAY_CALLS = (
    "OpenMovieFile", "NewMovieFromFile", "CloseMovieFile", "GetMovieTimeScale",
    "SetMovieActiveSegment", "NewMovieController", "MCDoAction", "StartMovie",
    "MoviesTask", "IsMovieDone", "GetMovieTime", "StopMovie",
    "DisposeMovieController", "DisposeMovie",
)


def status(source: str, name: str) -> str:
    regex = re.compile(r"(?m)^[ \t]*[\w*][\w\s*]*\b" + re.escape(name)
                       + r"[ \t]*\([^;{}]*\)[ \t\r\n]*\{")
    matches = list(regex.finditer(source))
    if len(matches) != 1:
        return "ABSENT_OR_AMBIGUOUS"
    begin = matches[0].end()
    # Markers occur at the beginning of the *explicit* generated stubs; no C parser
    # is claimed here. Never classify an unmarked function as implemented.
    sample = source[begin:begin + 300]
    marker = re.search(r'\bSTUB:[ \t]*' + re.escape(name) + r'[ \t]+called\b', sample)
    return "EXPLICIT_STUB" if marker else "NO_EXPLICIT_STUB_MARKER"


def audit(source: str) -> dict:
    api = {name: status(source, name) for name in PLAY_CALLS}
    return {"apis": api, "explicit_stubs": sorted(k for k, v in api.items() if v == "EXPLICIT_STUB"),
            "unknown": sorted(k for k, v in api.items() if v == "ABSENT_OR_AMBIGUOUS"),
            "scope": "Source-pattern witness only. No runtime or ABI test."}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quicktime-source", type=Path, required=True)
    ap.add_argument("--strict", action="store_true", help="fail when explicit stubs or unknown functions remain")
    args = ap.parse_args(argv)
    try:
        data = args.quicktime_source.read_bytes()
        if len(data) > 8 * 1024 * 1024:
            raise ValueError("source over 8 MiB limit")
        source = data.decode("utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, sort_keys=True))
        return 3
    report = audit(source)
    report["source_sha256"] = hashlib.sha256(data).hexdigest()
    report["status"] = ("STATIC_BLOCKED" if report["explicit_stubs"] else
                        "STATIC_INCONCLUSIVE" if report["unknown"] else "STATIC_UNMARKED")
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.strict:
        return 2 if report["explicit_stubs"] else 3 if report["unknown"] else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
