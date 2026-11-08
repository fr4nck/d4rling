#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test the private QuickTime MOV header parser without touching the build tree."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True,
                        help="new empty result directory outside the repository")
    parser.add_argument("--cc", default="cc", help="already installed C compiler")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    source = root / "src/frameworks/QuickTime/src"
    out = args.out.resolve()
    if root == out or root in out.parents:
        parser.error("the result directory must be outside the source repository")
    if out.exists() or not out.parent.is_dir():
        parser.error("result must not exist and its parent directory must exist")
    compiler = shutil.which(args.cc)
    if not compiler:
        parser.error("compiler not installed")
    out.mkdir()
    results = {}

    def run(name: str, command: list[str]) -> bool:
        try:
            completed = subprocess.run(command, cwd=out, capture_output=True,
                                       text=True, timeout=45, check=False)
            (out / (name + ".log")).write_text(
                completed.stdout + completed.stderr, encoding="utf-8")
            results[name] = {"exit": completed.returncode}
            return completed.returncode == 0
        except (OSError, subprocess.TimeoutExpired) as error:
            (out / (name + ".log")).write_text(str(error), encoding="utf-8")
            results[name] = {"error": type(error).__name__}
            return False

    executable = out / "qt_mov_probe_test"
    build_ok = run("compile", [compiler, "-std=c11", "-O1", "-g", "-Wall",
        "-Wextra", "-Werror", "-Wpedantic", "-fsanitize=address,undefined",
        "-fno-omit-frame-pointer", "-I", str(source),
        str(source / "qt_mov_probe.c"), str(Path(__file__).with_name("test_mov_probe.c")),
        "-o", str(executable)])
    tests_ok = build_ok and run("synthetic", [str(executable)])
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg and tests_ok:
        sample = out / "pcm_025.mov"
        media_ok = run("generate-pcm", [ffmpeg, "-nostdin", "-n", "-hide_banner",
            "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=8000:cl=mono",
            "-t", "0.25", "-c:a", "pcm_s16le", "-f", "mov", str(sample)])
        tests_ok = media_ok and run("real-mov", [str(executable), str(sample)])
    elif tests_ok:
        results["real-mov"] = {"status": "SKIP_NO_FFMPEG"}
    evidence = {
        "status": "PASS" if tests_ok else "FAIL",
        "scope": "Standalone metadata parser on host C; no Mach-O or QuickTime runtime",
        "ffmpeg_sample": "tested" if "real-mov" in results and results["real-mov"].get("exit") == 0 else "not-tested",
        "results": results,
    }
    (out / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False))
    return 0 if tests_ok else 1


if __name__ == "__main__":
    sys.exit(main())
