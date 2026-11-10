#!/usr/bin/env python3
"""SH09: bound the i386 Mach-O object linker inputs, then try the real linker.

Static qualification only. Not a dyld, runtime, audio, or i386 guest check.
Copyright (C) 2026 D4rling contributors. GPL-3.0-or-later.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from macho_audit import InvalidMachO, parse as parse_macho

MAX_INPUT = 1024 * 1024
EXPECTED_SH08_SHA256 = "c5e059e4ce39e2f1b95a925d0eebcac09ded0c36748db0e422b1bca3b7ee1409"
EXPECTED_DEFS = {"_FFT", "_RealFFT", "_InitFFTTable", "_bitreverse", "_gOmegaPiImag", "_gOmegaPiReal"}
EXPECTED_UNDEFS = {"_Pi", "_twoPi", "_sin", "_sinf"}
EXPECTED_GLOBAL_DEFS = {"_Pi", "_twoPi"}
DYNAMIC_MATH = {"_sin", "_sinf"}
INSTALL_NAME = "@rpath/libSH09OriginalFFT.dylib"
# Test-only values equal to SoundHack's initialization of Pi and twoPi.
# No substitute implementation of mathematical functions is provided.
GLOBAL_SOURCE = "float Pi = 3.14159265358979323846f;\nfloat twoPi = 6.28318530717958647692f;\n"
RELOC_HEADER = re.compile(r"^Relocation information \(([^)]+)\) (\d+) entries$")
RELOC_ROW = re.compile(r"^\s*(?:(?P<addr>[a-fA-F0-9]{8})\s+)?"
    r"(?P<pcrel>True|False)\s+(?P<width>long|word|byte)\s+"
    r"(?P<external>True|False|n/a)\s+(?P<kind>[A-Z]+)\s+"
    r"(?P<scattered>True|False)\s+(?P<symbol>\S.*)$")
ALLOWED_RELOCS = {"VANILLA", "SECTDIF", "LOCSDIF", "PAIR"}


class Inconclusive(Exception):
    """Could not run a necessary verifier or linker; never a PASS."""


class ContractFailure(Exception):
    """Observed contradiction in target object/linker result."""


def command(argv):
    try:
        r = subprocess.run(argv, timeout=20, text=True, capture_output=True, check=False)
    except (OSError, subprocess.TimeoutExpired) as err:
        raise Inconclusive("tool invocation unavailable: " + str(err)) from err
    if len(r.stdout) > 100000 or len(r.stderr) > 100000:
        raise Inconclusive("tool output oversized")
    return r


def executable(tool):
    result = shutil.which(tool)
    if not result:
        raise Inconclusive("tool not installed: " + tool)
    return result


def inspect_macho(path, expected_sha):
    path = Path(path)
    if not path.is_file():
        raise Inconclusive("Mach-O object absent: " + str(path))
    if path.stat().st_size < 32 or path.stat().st_size > MAX_INPUT:
        raise Inconclusive("Mach-O object outside allowed size")
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if expected_sha is not None and sha.lower() != expected_sha.lower():
        raise Inconclusive("SHA-256 mismatch; do not trust a different source object")
    try:
        info = parse_macho(raw, "i386")
    except InvalidMachO as err:
        raise ContractFailure("Mach-O target parse failed: " + str(err)) from err
    if info["filetype"] != 1 or info["bits"] != 32 or info["dylibs"] or info["has_dyld_info"]:
        raise ContractFailure("input must be one i386 MH_OBJECT without load libraries or dyld info")
    if not info["has_symtab"] or info["symbol_caveats"]:
        raise Inconclusive("object nlist unavailable or caveated")
    defs, undefs = set(info["exports_nlist"]), set(info["imports_nlist"])
    if defs != EXPECTED_DEFS or undefs != EXPECTED_UNDEFS:
        raise ContractFailure("unexpected original FFT symbols: " + repr({"defined": sorted(defs), "undefined": sorted(undefs)}))
    return {"sha256": sha, "size": len(raw), "arch": info["arch"],
            "defined": sorted(defs), "undefined": sorted(undefs)}


def inspect_relocations(text, pinned=False):
    """Parse llvm-objdump relocation *text*; no secondary Mach-O parser."""
    rows, groups, current = [], [], None
    for line in text.splitlines():
        h = RELOC_HEADER.match(line)
        if h:
            if current is not None:
                raise Inconclusive("multiple relocation sections unsupported")
            current = (h.group(1), int(h.group(2)))
            groups.append(current)
            continue
        if current is not None:
            if not line.strip() or line.startswith("address  "):
                continue
            m = RELOC_ROW.match(line)
            if not m:
                raise Inconclusive("unrecognized relocation record: " + line[:80])
            rows.append(m.groupdict())
    if len(groups) != 1 or groups[0][0] != "__TEXT,__text":
        raise Inconclusive("expected one __TEXT,__text relocation section")
    if groups[0][1] != len(rows) or not rows or len(rows) > 1024:
        raise ContractFailure("relocation header does not match entries")
    kinds = Counter(row["kind"] for row in rows)
    if kinds.keys() - ALLOWED_RELOCS:
        raise Inconclusive("unsupported i386 relocation types: " + repr(sorted(kinds.keys() - ALLOWED_RELOCS)))
    externals = Counter()
    for i, row in enumerate(rows):
        kind = row["kind"]
        if kind == "PAIR":
            if i == 0 or rows[i-1]["kind"] not in ("LOCSDIF", "SECTDIF") or row["addr"] is not None:
                raise ContractFailure("orphan or malformed PAIR relocation")
        elif kind in ("LOCSDIF", "SECTDIF"):
            if i+1 == len(rows) or rows[i+1]["kind"] != "PAIR":
                raise ContractFailure("sectdiff relocation missing adjacent PAIR")
        if kind != "PAIR" and row["addr"] is None:
            raise ContractFailure("relocation has no offset")
        if row["external"] == "True":
            if kind != "VANILLA" or row["symbol"] not in DYNAMIC_MATH:
                raise ContractFailure("unrecognized external relocation: " + row["symbol"])
            externals[row["symbol"]] += 1
    if set(externals) != DYNAMIC_MATH:
        raise ContractFailure("sin and sinf must both have external call relocations")
    if pinned and len(rows) != 48:
        raise ContractFailure("pinned SH08 relocation count differs from reference")
    return {"section": groups[0][0], "count": len(rows), "types": dict(kinds),
            "external_math_calls": dict(externals), "paired_sectdiff": kinds["PAIR"]}


def compile_globals(clang, dest):
    # This tiny original-app data-contract object intentionally does not define sin/sinf.
    source = dest / "fft_globals.c"
    source.write_text(GLOBAL_SOURCE, encoding="ascii")
    result = dest / "fft_globals.o"
    r = command([executable(clang), "-target", "i386-apple-darwin9", "-nostdinc",
                 "-std=c99", "-fno-stack-protector", "-c", str(source), "-o", str(result)])
    if r.returncode:
        raise Inconclusive("i386 globals compilation failed: " + r.stderr[-400:])
    image = parse_macho(result.read_bytes(), "i386")
    if (image["filetype"] != 1 or image["bits"] != 32
            or set(image["exports_nlist"]) != EXPECTED_GLOBAL_DEFS
            or image["imports_nlist"] or image["symbol_caveats"]):
        raise ContractFailure("target globals object has unexpected nlist/ABI")
    return result


def verify_linked(path):
    data = path.read_bytes()
    if not data or len(data) > MAX_INPUT:
        raise ContractFailure("linked candidate empty or oversized")
    try:
        image = parse_macho(data, "i386")
    except InvalidMachO as err:
        raise ContractFailure("linker output is not valid i386 Mach-O: " + str(err)) from err
    if image["bits"] != 32 or image["filetype"] != 6:
        raise ContractFailure("linker did not produce MH_DYLIB i386")
    if image["install_name"] != INSTALL_NAME:
        raise ContractFailure("linked dylib install name mismatch")
    if image["has_dyld_info"]:
        raise Inconclusive("linked dylib contains unparsed dyld bind/export opcodes")
    if not image["has_symtab"] or image["symbol_caveats"]:
        raise Inconclusive("linked dylib nlist incomplete")
    exports = set(image["exports_nlist"])
    if not (EXPECTED_DEFS | EXPECTED_GLOBAL_DEFS) <= exports:
        raise ContractFailure("linked dylib missing expected FFT/globals symbols")
    if set(image["imports_nlist"]) != DYNAMIC_MATH:
        raise ContractFailure("linked dylib imports differ from expected external sin/sinf")
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
            "install_name": image["install_name"], "defined": sorted(exports),
            "undefined": image["imports_nlist"]}


def attempt_link(ld64, input_object, globals_object, folder):
    dest = folder / "libSH09OriginalFFT.dylib"
    executable_path = executable(ld64)
    # The LLD Mach-O driver requires -platform_version; older cctools ld64
    # accepts the historical -macosx_version_min option for a 10.5/i386 image.
    version_flags = (["-platform_version", "macos", "10.5", "10.5"]
                     if Path(executable_path).name == "ld64.lld"
                     else ["-macosx_version_min", "10.5"])
    r = command([executable_path, "-arch", "i386", "-dylib", *version_flags,
                 "-undefined", "dynamic_lookup", "-install_name", INSTALL_NAME,
                 "-o", str(dest), str(input_object), str(globals_object)])
    if r.returncode:
        # An unavailable backend and a link error are NOT a negative FFT result.
        return {"status": "LINK_TOOLCHAIN_BLOCKED", "linker_returncode": r.returncode,
                "linker_message": r.stderr.strip()[-500:]}, None
    if not dest.is_file():
        raise ContractFailure("linker reported success but produced no dylib")
    return {"status": "LINK_STRUCTURE_PASS", "linked": verify_linked(dest)}, dest


def qualify(object_path, expected_sha=EXPECTED_SH08_SHA256, clang="clang", objdump="llvm-objdump",
            linker="ld64.lld", try_link=True):
    obj = inspect_macho(object_path, expected_sha)
    proc = command([executable(objdump), "--macho", "--reloc", str(object_path)])
    if proc.returncode:
        raise Inconclusive("llvm-objdump failed: " + proc.stderr[-400:])
    relocation = inspect_relocations(proc.stdout, pinned=(obj["sha256"] == EXPECTED_SH08_SHA256))
    with tempfile.TemporaryDirectory(prefix="d4rl-sh09-") as tmp:
        folder = Path(tmp)
        globals_obj = compile_globals(clang, folder)
        status = {"status": "LINK_INPUTS_READY", "object": obj, "relocations": relocation,
                  "companion_defined": sorted(EXPECTED_GLOBAL_DEFS),
                  "requires_external_math": sorted(DYNAMIC_MATH),
                  "scope": "static i386 link-input qualification only; no guest/audio"}
        if try_link:
            linked, _ = attempt_link(linker, object_path, globals_obj, folder)
            status["link_attempt"] = linked
            status["status"] = linked["status"]
        return status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--object", required=True, help="previously built legitimate SH08 Mach-O i386 .o")
    parser.add_argument("--expected-sha256", default=EXPECTED_SH08_SHA256)
    parser.add_argument("--clang", default="clang")
    parser.add_argument("--llvm-objdump", default="llvm-objdump")
    parser.add_argument("--ld64", default="ld64.lld")
    parser.add_argument("--no-link", action="store_true", help="check inputs and relocations without calling any linker")
    args = parser.parse_args(argv)
    try:
        result = qualify(args.object, args.expected_sha256, args.clang, args.llvm_objdump,
                         args.ld64, try_link=not args.no_link)
    except ContractFailure as err:
        result, code = {"status": "TARGET_CONTRACT_FAIL", "error": str(err)}, 2
    except (Inconclusive, InvalidMachO, OSError, ValueError) as err:
        result, code = {"status": "INCONCLUSIVE", "error": str(err)}, 3
    else:
        code = 0 if result["status"] in ("LINK_INPUTS_READY", "LINK_STRUCTURE_PASS") else 3
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
