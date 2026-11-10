#!/usr/bin/env python3
"""SH08: cross-compile unchanged SoundHack FFT.c to a Darwin i386 Mach-O object.

The result is *only* a target object and a static symbol/width contract check.
No link, Apple SDK, i386 guest, binary redistribution or audio playback.
Copyright (C) 2026 D4rling contributors. GPL-3.0-or-later.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from fft_host_probe import (Inconclusive, SOURCE_SHA, HEADER_SHA, require_pinned)
from macho_audit import InvalidMachO, parse as parse_macho

TARGET = "i386-apple-darwin9"  # clang resolves this to macOS 10.5 i386
MAX_OBJECT_BYTES = 1024 * 1024
# This is a prototype-only replacement for system <math.h> at *compile time*.
# No math implementation is supplied or linked; upstream FFT.c is untouched.
MATH_DECLARATIONS = ("#ifndef D4RL_SH08_MATH_PROTOTYPES_H\n"
                     "#define D4RL_SH08_MATH_PROTOTYPES_H\n"
                     "double sin(double);\n"
                     "float sinf(float);\n"
                     "#endif\n")
EXPECTED_DEFINITIONS = frozenset({"_FFT", "_RealFFT", "_InitFFTTable", "_bitreverse",
                                   "_gOmegaPiImag", "_gOmegaPiReal"})
EXPECTED_UNDEFINED = frozenset({"_Pi", "_twoPi", "_sin", "_sinf"})
EXPECTED_MACROS = {"__APPLE__": "1", "__MACH__": "1", "__i386__": "1",
                   "__ILP32__": "1", "__SIZEOF_POINTER__": "4",
                   "__SIZEOF_LONG__": "4", "__SIZEOF_INT__": "4",
                   "__SIZEOF_SHORT__": "2"}


def check_macros(text):
    """Verify Clang's target data model; do not substitute the host's widths."""
    defines = {}
    for line in text.splitlines():
        fields = line.split(None, 2)
        if len(fields) == 3 and fields[0] == "#define":
            defines[fields[1]] = fields[2]
    problems = []
    for key, want in EXPECTED_MACROS.items():
        if defines.get(key) != want:
            problems.append(f"target {key} expected {want}, got {defines.get(key, 'absent')}")
    if "__LP64__" in defines:
        problems.append("target unexpectedly defines __LP64__")
    return problems


def check_object(content):
    """Use the project's existing bounded Mach-O reader, not a second parser."""
    if not content or len(content) > MAX_OBJECT_BYTES:
        raise Inconclusive("empty or oversized target object")
    try:
        image = parse_macho(content, "i386")
    except InvalidMachO as exc:
        raise Inconclusive(f"unparseable Mach-O object: {exc}") from exc
    problems = []
    for attr, expected in (("arch", "i386"), ("bits", 32), ("filetype", 1),
                           ("has_symtab", True), ("has_dyld_info", False),
                           ("two_level_namespace", False)):
        if image.get(attr) != expected:
            problems.append(f"Mach-O {attr}: expected {expected}, got {image.get(attr)}")
    if image.get("dylibs"):
        problems.append("relocatable object unexpectedly declares linked dylibs")
    defined = set(image.get("exports_nlist", []))
    undefined = set(image.get("imports_nlist", []))
    if defined != EXPECTED_DEFINITIONS:
        problems.append("defined symbol mismatch: missing=" + repr(sorted(EXPECTED_DEFINITIONS - defined))
                        + ", unexpected=" + repr(sorted(defined - EXPECTED_DEFINITIONS)))
    if undefined != EXPECTED_UNDEFINED:
        problems.append("undefined symbol mismatch: missing=" + repr(sorted(EXPECTED_UNDEFINED - undefined))
                        + ", unexpected=" + repr(sorted(undefined - EXPECTED_UNDEFINED)))
    if image.get("symbol_caveats"):
        problems.append("symbol caveats: " + repr(image["symbol_caveats"]))
    return {"problems": problems, "arch": image.get("arch"),
            "filetype": image.get("filetype"), "bits": image.get("bits"),
            "defined_nlist": sorted(defined), "undefined_nlist": sorted(undefined),
            "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}


def installed_clang(compiler):
    name = compiler or "clang"
    binary = shutil.which(name)
    if not binary:
        raise Inconclusive(f"no installed Clang executable: {name}")
    return binary


def invoke(args, stdin=None):
    try:
        result = subprocess.run(args, input=stdin, text=True, capture_output=True,
                                timeout=25, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Inconclusive("Clang invocation failed: " + str(exc)) from exc
    if result.returncode:
        raise Inconclusive("Clang failed: " + result.stderr[-600:])
    return result.stdout


def qualify(source_dir, clang=None, output=None):
    source_dir = Path(source_dir)
    c_source = source_dir / "FFT.c"
    h_source = source_dir / "FFT.h"
    require_pinned(c_source, SOURCE_SHA)
    require_pinned(h_source, HEADER_SHA)
    binary = installed_clang(clang)
    with tempfile.TemporaryDirectory(prefix="d4rl-sh08-") as tmp:
        folder = Path(tmp)
        (folder / "math.h").write_text(MATH_DECLARATIONS, encoding="ascii")
        target = folder / "fft-macho-i386.o"
        macros = invoke([binary, "-target", TARGET, "-nostdinc", "-dM", "-E", "-x", "c", "-"], stdin="")
        width_problems = check_macros(macros)
        # Fail before even attempting to build an object under the wrong target ABI.
        if width_problems:
            return {"status": "TARGET_CONTRACT_FAIL", "phase": "data_model",
                    "problems": width_problems}
        invoke([binary, "-target", TARGET, "-nostdinc", "-std=c99", "-O1",
                "-fno-stack-protector", "-Werror=implicit-function-declaration",
                "-I", str(folder), "-c", str(c_source), "-o", str(target)])
        content = target.read_bytes()
        witness = check_object(content)
        ok = not witness["problems"]
        result = {"status": "TARGET_OBJECT_PASS" if ok else "TARGET_CONTRACT_FAIL",
                  "scope": "unaltered SoundHack FFT.c -> MH_OBJECT i386; not a runnable program",
                  "target": TARGET, "source_blob": SOURCE_SHA,
                  "header_blob": HEADER_SHA, "target_data_model": "ILP32 (32-bit long/pointer)",
                  "object": witness}
        if output is not None and ok:
            # Exclusive creation. Does not overwrite an existing file or symlink.
            dest = Path(output)
            try:
                with dest.open("xb") as stream:
                    stream.write(content)
            except OSError as exc:
                raise Inconclusive("cannot exclusively create object output: " + str(exc)) from exc
            result["saved_object"] = str(dest)
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, help="authorized upstream SoundHack/Math directory")
    parser.add_argument("--clang", default=None, help="already installed clang command")
    parser.add_argument("--output", default=None, help="optional object path (must not exist)")
    args = parser.parse_args(argv)
    try:
        result = qualify(args.source_dir, args.clang, args.output)
    except (Inconclusive, OSError, ValueError) as exc:
        result = {"status": "INCONCLUSIVE", "error": str(exc)}
        exit_code = 3
    else:
        exit_code = 0 if result["status"] == "TARGET_OBJECT_PASS" else 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
