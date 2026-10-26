#!/usr/bin/env python3
"""Offline CA-10 source and Mach-O artifact qualification (read-only).

The generated pulse_vars.h is optional: wrapgen writes it only if ELF
exports include global data symbols. This program neither builds nor fetches.
"""

import argparse
from pathlib import Path
import struct


OBJECT_RELATIVE = Path("src/CoreAudio/CMakeFiles/pulse.dir/pulse.c.o")
SOURCE_RELATIVE = Path("src/CoreAudio/pulse.c")
HEADER_RELATIVE = Path("src/CoreAudio/pulse_vars.h")


def read_text(path):
    return path.read_text(encoding="utf-8", errors="replace")


def verify_contract(source_tree):
    """Check the actual wrapgen/CMake contract without assuming output #2."""
    paths = {
        "cmake": source_tree / "cmake/wrap_elf.cmake",
        "generator": source_tree / "src/libelfloader/wrapgen/wrapgen.cpp",
        "audio": source_tree / "src/CoreAudio/CMakeLists.txt",
    }
    try:
        src = {name: read_text(path) for name, path in paths.items()}
    except OSError as exc:
        return "FAIL", str(exc)

    if "wrap_elf(pulse libpulse.so)" not in src["audio"]:
        return "FAIL", "PulseAudio wrap_elf mapping missing"
    if "function(wrap_elf name elfname)" not in src["cmake"]:
        return "FAIL", "wrap_elf CMake function missing"

    custom = src["cmake"].split("add_custom_command(", 1)
    if len(custom) != 2 or "OUTPUT" not in custom[1] or "COMMAND" not in custom[1]:
        return "FAIL", "CMake generation command not recognized"
    outputs = custom[1].split("OUTPUT", 1)[1].split("COMMAND", 1)[0]
    if "${name}.c" not in outputs or "${name}_vars.h" in outputs:
        return "FAIL", "CMake mandatory outputs have changed"
    if "if (!vars.empty())" not in src["generator"]:
        return "FAIL", "wrapgen conditional variable header missing"
    if "std::ofstream outputHeader(argv[3])" not in src["generator"]:
        return "FAIL", "wrapgen header output path missing"
    return "PASS", "conditional header contract verified in source"


def verify_generated_source(source):
    if not source.is_file():
        return "FAIL", "pulse.c missing"
    if source.stat().st_size == 0:
        return "FAIL", "pulse.c is empty"
    body = read_text(source)
    expected = ("#include <elfcalls.h>", ".symbol_resolver", "___elfname", "libpulse.so")
    if not all(fragment in body for fragment in expected):
        return "FAIL", "pulse.c is not a recognized PulseAudio wrapper"
    return "PASS", f"pulse.c bytes={source.stat().st_size}"


def verify_optional_header(header, source):
    if not header.exists():
        if source.is_file() and '#include "pulse_vars.h"' in read_text(source):
            return "FAIL", "pulse.c requires missing pulse_vars.h"
        return "SKIP_OPTIONAL", "no ELF global variables require pulse_vars.h"
    if not header.is_file() or header.stat().st_size == 0:
        return "FAIL", "pulse_vars.h present but invalid"
    return "PASS", f"optional header bytes={header.stat().st_size}"


def verify_macho_object(path):
    try:
        with path.open("rb") as obj:
            header = obj.read(16)
    except OSError as exc:
        return "FAIL", str(exc)
    if len(header) < 16:
        return "FAIL", "Mach-O header too short"
    magic, cpu_type, _cpu_subtype, file_type = struct.unpack("<IIII", header)
    if magic != 0xFEEDFACF:
        return "FAIL", "not little-endian Mach-O 64-bit"
    if cpu_type != 0x01000007:
        return "FAIL", "Mach-O architecture is not x86_64"
    if file_type != 1:
        return "FAIL", "Mach-O is not a relocatable object"
    return "PASS", "Mach-O 64-bit x86_64 MH_OBJECT"


def run(source_tree, build_tree=None):
    checks = {"CONTRACT": verify_contract(source_tree)}
    if build_tree is None:
        for name in ("PULSE_C", "PULSE_VARS", "OBJECT_MACHO"):
            checks[name] = "SKIP", "no --build-tree supplied"
    else:
        generated = build_tree / SOURCE_RELATIVE
        checks["PULSE_C"] = verify_generated_source(generated)
        checks["PULSE_VARS"] = verify_optional_header(build_tree / HEADER_RELATIVE, generated)
        checks["OBJECT_MACHO"] = verify_macho_object(build_tree / OBJECT_RELATIVE)
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-tree", type=Path,
                        default=Path(__file__).resolve().parents[3])
    parser.add_argument("--build-tree", type=Path,
                        help="Existing CoreAudio build tree; never modified")
    args = parser.parse_args()

    checks = run(args.source_tree, args.build_tree)
    for key, (status, detail) in checks.items():
        print(f"CA10_{key}={status}: {detail}")
    failed = any(status == "FAIL" for status, _ in checks.values())
    print("CA10_VERDICT=" + ("FAIL" if failed else
                           ("PASS" if args.build_tree else "SOURCE_ONLY")))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
