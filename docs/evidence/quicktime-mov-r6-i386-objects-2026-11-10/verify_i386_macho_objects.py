#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Strict read-only *object* gate for D4rling's private QuickTime MOV C sources.

Does not inspect dylibs or evaluate runtime functionality, ABI compatibility,
linking, CoreServices/CarbonCore, audio, or Logic Studio 8.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

MAGIC32 = 0xFEEDFACE
CPU_I386 = 7
MH_OBJECT = 1
LC_SYMTAB = 2
N_EXT = 0x01
N_PEXT = 0x10
N_TYPE = 0x0E
N_SECT = 0x0E

EXPECTED = {
    "pcm": {
        "defined": {
            "_d4rl_qt_mov_extract_pcm",
            "_d4rl_qt_mov_find_pcm",
            "_d4rl_qt_mov_list_tracks",
        },
        "undefined": {
            "_d4rl_qt_mov_probe", "_memcmp", "_memcpy", "_memset",
        },
    },
    "probe": {
        "defined": {"_d4rl_qt_mov_probe"},
        "undefined": {"_memcmp"},
    },
}


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def inspect(path: Path, kind: str) -> dict:
    body = path.read_bytes()
    require(len(body) >= 28, "not a complete Mach-O 32-bit header")
    magic, cpu, subtype, filetype, ncmds, sizeofcmds, flags = struct.unpack_from("<IiiIIII", body)
    require(magic == MAGIC32, "not a little-endian Mach-O 32-bit object")
    require(cpu == CPU_I386, "not CPU_TYPE_I386")
    require(filetype == MH_OBJECT, "not MH_OBJECT")
    require(ncmds <= 4096 and sizeofcmds <= len(body) - 28, "invalid load commands")
    pos = 28
    symtable = None
    for _ in range(ncmds):
        require(pos + 8 <= 28 + sizeofcmds, "truncated load command")
        cmd, size = struct.unpack_from("<II", body, pos)
        require(size >= 8 and pos + size <= 28 + sizeofcmds, "malformed load command")
        if cmd == LC_SYMTAB:
            require(symtable is None and size >= 24, "ambiguous LC_SYMTAB")
            symtable = struct.unpack_from("<IIII", body, pos + 8)
        pos += size
    require(pos == 28 + sizeofcmds, "load commands length mismatch")
    require(symtable is not None, "no LC_SYMTAB")
    symoff, nsyms, stroff, strsize = symtable
    require(nsyms <= len(body) // 12, "bad symbol count")
    require(symoff + nsyms * 12 <= len(body), "symbol table out of bounds")
    require(stroff + strsize <= len(body), "string table out of bounds")
    names_defined: set[str] = set()
    names_undefined: set[str] = set()
    for i in range(nsyms):
        off, n_type, n_sect, n_desc, n_value = struct.unpack_from("<IBBHI", body, symoff + i * 12)
        require(off < strsize, "bad string offset")
        start = stroff + off
        stop = body.find(b"\0", start, stroff + strsize)
        require(stop >= 0, "unterminated symbol")
        name = body[start:stop].decode("ascii", errors="strict")
        if (n_type & N_EXT) == 0:
            continue
        if (n_type & N_TYPE) == N_SECT:
            require(bool(n_type & N_PEXT), f"defined external not private: {name}")
            require(name not in names_defined, f"duplicate definition: {name}")
            names_defined.add(name)
        elif (n_type & N_TYPE) == 0:
            require(name not in names_undefined, f"duplicate undefined: {name}")
            names_undefined.add(name)
        else:
            raise ValueError(f"unexpected nlist type for {name}: 0x{n_type:02x}")
    contract = EXPECTED[kind]
    require(names_defined == contract["defined"],
            f"unexpected defined symbols: {sorted(names_defined ^ contract['defined'])}")
    require(names_undefined == contract["undefined"],
            f"unexpected undefined symbols: {sorted(names_undefined ^ contract['undefined'])}")
    return {
        "kind": kind,
        "sha256": hashlib.sha256(body).hexdigest(),
        "size": len(body),
        "cputype": cpu,
        "filetype": filetype,
        "private_defined": sorted(names_defined),
        "undefined": sorted(names_undefined),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pcm", type=Path, required=True)
    ap.add_argument("--probe", type=Path, required=True)
    ap.add_argument("--elf-negative", type=Path, required=True)
    ap.add_argument("--x64-negative", type=Path, required=True)
    args = ap.parse_args(argv)
    checks = []
    try:
        checks.extend((inspect(args.pcm, "pcm"), inspect(args.probe, "probe")))
        for path, label in ((args.elf_negative, "ELF"), (args.x64_negative, "Mach-O x86_64")):
            try:
                inspect(path, "pcm")
            except ValueError as exc:
                checks.append({"negative": label, "status": "REJECTED", "reason": str(exc)})
            else:
                raise ValueError(f"negative {label} accepted unexpectedly")
    except (OSError, ValueError, UnicodeError, struct.error) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({"status": "STATIC_OBJECT_PASS", "checks": checks,
                      "limitations": ["no SDK or Darwin headers used; test-only C declarations",
                                      "MH_OBJECT only; no ld64, dylib, dyld, guest or ABI runtime",
                                      "does not validate C4 Memory Manager or Logic Studio 8"]},
                     sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
