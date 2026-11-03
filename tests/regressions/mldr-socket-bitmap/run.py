#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Host-only bitmap test from actual mldr.c helpers. No network/build-tree writes.
Usage: python3 run.py [--source /path/to/mldr.c] [--expect-blob GIT_SHA1]
"""
import argparse
import hashlib
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import tempfile


def error(msg):
    raise SystemExit("FAIL: " + msg)


def run():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, help="Existing, unchanged mldr.c to inspect")
    p.add_argument("--expect-blob", help="Expected git blob SHA-1 of mldr.c")
    p.add_argument("--cc", default=None, help="Existing clang compiler (no install)")
    args = p.parse_args()
    root = Path(__file__).resolve().parents[3]
    source = args.source if args.source else root / "src/startup/mldr/mldr.c"
    if not source.is_file():
        error(f"source not found: {source}")
    raw = source.read_bytes()
    got = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    print("SOURCE=" + str(source), flush=True)
    print("SOURCE_GIT_BLOB=" + got, flush=True)
    print("SOURCE_SHA256=" + hashlib.sha256(raw).hexdigest(), flush=True)
    if args.expect_blob and got != args.expect_blob.lower():
        error(f"source mismatch: expected {args.expect_blob}, got {got}")
    try:
        data = raw.decode("utf-8")
    except UnicodeDecodeError as ex:
        error(f"source is not UTF-8: {ex}")
    types = re.search(r"typedef struct socket_bitmap \{.*?(?=static int socket_bitmap_get)", data, flags=re.S)
    helpers = re.search(r"static int socket_bitmap_get.*?^static void socket_bitmap_put.*?^};\s*$", data, flags=re.S | re.M)
    if not types or not helpers:
        error("cannot extract bitmap types and functions from actual source")
    template = (Path(__file__).parent / "probe.c.in").read_text(encoding="utf-8")
    for marker in ("@@BITMAP_TYPES@@", "@@BITMAP_FUNCS@@"):
        if template.count(marker) != 1:
            error(f"template marker must occur exactly once: {marker}")
    harness = template.replace("@@BITMAP_TYPES@@", types.group(0)).replace("@@BITMAP_FUNCS@@", helpers.group(0))
    if "@@BITMAP_" in harness:
        error("unexpanded marker in C harness")
    cc = args.cc or shutil.which("clang-19") or shutil.which("clang")
    if not cc or not shutil.which(cc):
        error("clang unavailable; no download or install attempted")
    print("COMPILER=" + str(cc), flush=True)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    with tempfile.TemporaryDirectory(prefix="pr6-bitmap-") as temp:
        src = Path(temp) / "probe.c"
        exe = Path(temp) / "probe"
        src.write_text(harness, encoding="utf-8")
        print("HARNESS_SHA256=" + hashlib.sha256(harness.encode()).hexdigest(), flush=True)
        cmd = [str(cc), "-pthread", "-g", "-O1", "-std=gnu11", "-Wall", "-Wextra",
               "-fno-omit-frame-pointer", "-fsanitize=address,undefined",
               "-fno-sanitize-recover=all", str(src), "-o", str(exe)]
        try:
            compiled = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        except subprocess.TimeoutExpired:
            error("compiler timed out")
        if compiled.stdout or compiled.stderr:
            print(compiled.stdout + compiled.stderr, end="", flush=True)
        if compiled.returncode:
            error(f"Clang compile failed, exit={compiled.returncode}")
        print("COMPILE=PASS", flush=True)
        env = dict(os.environ)
        env["ASAN_OPTIONS"] = "detect_leaks=1:halt_on_error=1:abort_on_error=1"
        env["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
        try:
            tested = subprocess.run([str(exe)], capture_output=True, text=True, timeout=90, env=env)
        except subprocess.TimeoutExpired:
            error("bitmap execution timed out")
        if tested.stdout or tested.stderr:
            print(tested.stdout + tested.stderr, end="", flush=True)
        print("TEST_EXIT=" + str(tested.returncode), flush=True)
        if tested.returncode != 0 or "PASS: deterministic mldr bitmap regression" not in tested.stdout:
            error("bitmap invariant or sanitizer failure")
        print("MLDR_PR6_DETERMINISTIC=PASS", flush=True)


if __name__ == "__main__":
    run()
