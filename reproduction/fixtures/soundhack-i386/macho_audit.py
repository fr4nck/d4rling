#!/usr/bin/env python3
"""Bounded, read-only Mach-O i386 dependency and nlist symbol audit.

GPL-3.0-or-later. No Apple SDK and no third-party code incorporated.
This is a STATIC audit, not a dyld resolver or runtime compatibility test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

MAX_INPUT = 128 * 1024 * 1024
CPU_NAMES = {7: "i386", 0x01000007: "x86_64", 18: "ppc", 0x01000012: "ppc64", 12: "arm", 0x0100000c: "arm64"}
ARCH_CPUS = {v: k for k, v in CPU_NAMES.items()}
THIN_MAGICS = {b"\xce\xfa\xed\xfe": ("<", False), b"\xfe\xed\xfa\xce": (">", False),
               b"\xcf\xfa\xed\xfe": ("<", True), b"\xfe\xed\xfa\xcf": (">", True)}
FAT_MAGICS = {b"\xca\xfe\xba\xbe": (">", False), b"\xbe\xba\xfe\xca": ("<", False),
              b"\xca\xfe\xba\xbf": (">", True), b"\xbf\xba\xfe\xca": ("<", True)}
LC_SYMTAB = 0x2
MH_TWOLEVEL = 0x80
N_WEAK_REF = 0x0040
LC_DYLD_INFO = 0x22
LC_DYLD_INFO_ONLY = 0x80000022
LC_LOADS = {0xC: "load", 0x80000018: "weak", 0x8000001F: "reexport",
            0x20: "lazy", 0x80000023: "upward", 0xD: "id"}


class InvalidMachO(ValueError):
    """Malformed input or impossible bounded parse."""


def section(data: bytes, pos: int, size: int, start: int = 0, end: int | None = None) -> bytes:
    if end is None:
        end = len(data)
    if size < 0 or pos < start or pos > end or size > end - pos:
        raise InvalidMachO("out-of-bounds structure")
    return data[pos:pos + size]


def read_cstr(data: bytes, start: int, stop: int) -> str:
    s = section(data, start, stop - start)
    null = s.find(b"\0")
    if null < 0:
        raise InvalidMachO("unterminated string")
    return s[:null].decode("utf-8", errors="replace")


def read_thin(data: bytes, offset: int, length: int) -> dict:
    if length < 28:
        raise InvalidMachO("truncated Mach-O header")
    raw = section(data, offset, 4, offset, offset + length)
    if raw not in THIN_MAGICS:
        raise InvalidMachO("not a Mach-O slice")
    endian, is64 = THIN_MAGICS[raw]
    hsize = 32 if is64 else 28
    h = section(data, offset, hsize, offset, offset + length)
    cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = struct.unpack_from(endian + "iiIIII", h, 4)
    if is64:
        struct.unpack_from(endian + "I", h, 28)
    if sizeofcmds > length - hsize or ncmds > sizeofcmds // 8:
        raise InvalidMachO("invalid load command table size/count")
    pos = offset + hsize
    cmds_end = pos + sizeofcmds
    dylibs: list[dict] = []
    symtab = None
    has_dyld_info = False
    ordinal_libraries: list[str] = []
    install_name = None
    for _ in range(ncmds):
        cmd, size = struct.unpack(endian + "II", section(data, pos, 8, pos, cmds_end))
        if size < 8 or size > cmds_end - pos:
            raise InvalidMachO("invalid load command size")
        if cmd in LC_LOADS:
            if size < 24:
                raise InvalidMachO("truncated dylib command")
            pathoff = struct.unpack_from(endian + "I", data, pos + 8)[0]
            if pathoff < 24 or pathoff >= size:
                raise InvalidMachO("invalid dylib name offset")
            name = read_cstr(data, pos + pathoff, pos + size)
            dylibs.append({"kind": LC_LOADS[cmd], "name": name})
            if cmd == 0xD:  # LC_ID_DYLIB is not in the import ordinal table
                if filetype not in (0x6, 0x9):  # MH_DYLIB or MH_DYLIB_STUB
                    raise InvalidMachO("dylib install name on non-dylib image")
                if install_name is not None:
                    raise InvalidMachO("duplicate dylib install name")
                install_name = name
            else:
                ordinal_libraries.append(name)
        elif cmd == LC_SYMTAB:
            if symtab is not None or size < 24:
                raise InvalidMachO("duplicate or truncated symtab command")
            symtab = struct.unpack(endian + "IIII", section(data, pos + 8, 16, pos, pos + size))
        elif cmd in (LC_DYLD_INFO, LC_DYLD_INFO_ONLY):
            has_dyld_info = True
        pos += size
    if pos != cmds_end:
        raise InvalidMachO("load command byte count mismatch")
    imported: set[str] = set()
    exported: set[str] = set()
    imported_details: list[dict] = []
    symbol_caveats: list[str] = []
    two_level = bool(flags & MH_TWOLEVEL)
    if symtab:
        symoff, nsyms, stroff, strsize = symtab
        entry_size = 16 if is64 else 12
        if nsyms > length // entry_size:
            raise InvalidMachO("invalid symbol count")
        section(data, offset + symoff, nsyms * entry_size, offset, offset + length)
        section(data, offset + stroff, strsize, offset, offset + length)
        for index in range(nsyms):
            at = offset + symoff + index * entry_size
            nameoff, n_type, _n_sect, n_desc = struct.unpack_from(endian + "IBBH", data, at)
            n_value = struct.unpack_from(endian + ("Q" if is64 else "I"), data, at + 8)[0]
            if not (n_type & 0x01) or (n_type & 0xE0):  # private/static or STAB debug record
                continue
            if nameoff >= strsize:
                raise InvalidMachO("invalid symbol string offset")
            name = read_cstr(data, offset + stroff + nameoff, offset + stroff + strsize)
            if not name:
                continue
            kind = n_type & 0x0E
            if kind in (0x0, 0xC):  # N_UNDF, N_PBUD
                imported.add(name)
                ordinal = (n_desc >> 8) & 0xff if two_level else None
                # Historical 0xfe must be interpreted as ordinal 254 when
                # a binary contains at least that many load commands.
                if ordinal == 0xfe and len(ordinal_libraries) < 254:
                    lookup = "dynamic_lookup"
                    library = None
                elif ordinal == 0xff:
                    lookup = "main_executable"
                    library = None
                elif ordinal == 0:
                    lookup = "self" if two_level else "flat"
                    library = None
                elif ordinal is None:
                    lookup = "flat"
                    library = None
                else:
                    if ordinal > len(ordinal_libraries):
                        raise InvalidMachO("invalid library ordinal")
                    lookup = "library"
                    library = ordinal_libraries[ordinal - 1]
                imported_details.append({"name": name, "library_ordinal": ordinal,
                                         "library_name": library, "lookup": lookup,
                                         "weak_import": bool(n_desc & N_WEAK_REF),
                                         "common_or_prebound": bool(n_value) or kind == 0xC,
                                         "reference_to_weak": bool(n_desc & 0x0080)})
            elif kind in (0x2, 0xE):  # N_ABS, N_SECT
                exported.add(name)
            else:  # N_INDR and unknown types do not prove a defined address
                symbol_caveats.append(f"{name}: unsupported nlist type 0x{kind:x}")
    return {"arch": CPU_NAMES.get(cputype, f"cpu:{cputype}"), "cputype": cputype,
            "cpusubtype": cpusubtype, "bits": 64 if is64 else 32,
            "filetype": filetype, "dylibs": dylibs,
            "two_level_namespace": two_level, "install_name": install_name,
            "imports_nlist": sorted(imported), "exports_nlist": sorted(exported),
            "imports_detail": sorted(imported_details, key=lambda x: (x["name"], str(x["library_name"]))),
            "symbol_caveats": sorted(symbol_caveats),
            "has_symtab": symtab is not None, "has_dyld_info": has_dyld_info,
            "symbol_scope": "nlist with library ordinals only; dyld bind/reexport resolution not implemented"}


def parse(data: bytes, arch: str) -> dict:
    if len(data) < 4:
        raise InvalidMachO("truncated magic")
    m = data[:4]
    if m in THIN_MAGICS:
        result = read_thin(data, 0, len(data))
        if result["arch"] != arch:
            raise InvalidMachO(f"required architecture {arch} absent (found {result['arch']})")
        return result
    if m not in FAT_MAGICS:
        raise InvalidMachO("not Mach-O or universal binary")
    endian, fat64 = FAT_MAGICS[m]
    if len(data) < 8:
        raise InvalidMachO("truncated FAT header")
    count = struct.unpack_from(endian + "I", data, 4)[0]
    entry_size = 32 if fat64 else 20
    if count > (len(data) - 8) // entry_size:
        raise InvalidMachO("truncated FAT slice table")
    table_end = 8 + count * entry_size
    choices = []
    ranges = []
    for i in range(count):
        pos = 8 + i * entry_size
        cputype, cpusubtype = struct.unpack_from(endian + "ii", data, pos)
        if fat64:
            start, size = struct.unpack_from(endian + "QQ", data, pos + 8)
        else:
            start, size = struct.unpack_from(endian + "II", data, pos + 8)
        section(data, start, size, table_end)
        if size == 0:
            raise InvalidMachO("empty FAT slice")
        ranges.append((start, start + size))
        choices.append((cputype, cpusubtype, start, size))
    for a, b in zip(sorted(ranges), sorted(ranges)[1:]):
        if a[1] > b[0]:
            raise InvalidMachO("overlapping FAT slices")
    selected = [c for c in choices if c[0] == ARCH_CPUS[arch]]
    if not selected:
        raise InvalidMachO(f"required architecture {arch} absent in FAT")
    if len(selected) != 1:
        raise InvalidMachO(f"ambiguous multiple {arch} slices")
    cpu, subtype, start, size = selected[0]
    result = read_thin(data, start, size)
    if result["cputype"] != cpu or result["cpusubtype"] != subtype:
        raise InvalidMachO("FAT architecture does not match slice header")
    result["fat_slices"] = [{"arch": CPU_NAMES.get(c, f"cpu:{c}"), "offset": o, "size": n}
                            for c, _s, o, n in choices]
    return result


def inspect(path: Path, arch: str) -> dict:
    with path.open("rb") as stream:
        data = stream.read(MAX_INPUT + 1)
    if len(data) > MAX_INPUT:
        raise InvalidMachO(f"file exceeds {MAX_INPUT} byte inspection limit")
    entry = parse(data, arch)
    entry["file"] = str(path)
    entry["sha256"] = hashlib.sha256(data).hexdigest()
    return entry


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--consumer", type=Path, required=True, help="Mach-O application or library")
    p.add_argument("--provider", type=Path, action="append", default=[], help="Mach-O export provider (repeatable)")
    p.add_argument("--arch", choices=sorted(ARCH_CPUS), default="i386")
    p.add_argument("--strict", action="store_true", help="nonzero exit for unresolved names or inconclusive nlist")
    args = p.parse_args(argv)
    try:
        consumer = inspect(args.consumer, args.arch)
        providers = [inspect(path, args.arch) for path in args.provider]
    except (OSError, InvalidMachO) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, sort_keys=True))
        return 3
    report = {"status": "STATIC_INSPECTED", "arch": args.arch, "consumer": consumer, "providers": providers,
              "evidence": "STATIC nlist names and two-level ordinals; no execution, dyld binding, ABI or audio validated"}
    if providers:
        all_exports = set().union(*(set(p["exports_nlist"]) for p in providers))
        by_id: dict[str, list[dict]] = {}
        for provider in providers:
            if provider["install_name"]:
                by_id.setdefault(provider["install_name"], []).append(provider)
        resolved = []
        unresolved = []
        unknown = []
        optional_missing = []
        for imp in consumer["imports_detail"]:
            name = imp["name"]
            library = imp["library_name"]
            if not consumer["two_level_namespace"]:
                matches = name in all_exports
            elif imp["lookup"] != "library":
                unknown.append({"name": name, "reason": f"{imp['lookup']} not resolved statically"})
                continue
            elif not by_id.get(library):
                # A missing provider identity is not evidence that an API
                # is missing from the library at runtime.
                if any(not p["install_name"] for p in providers):
                    unknown.append({"name": name, "reason": f"no verified provider identity for {library}"})
                else:
                    unresolved.append({"name": name, "expected_library": library})
                continue
            elif len(by_id[library]) != 1:
                unknown.append({"name": name, "reason": f"ambiguous provider identity {library}"})
                continue
            else:
                matches = name in by_id[library][0]["exports_nlist"]
            if imp["common_or_prebound"] or imp["reference_to_weak"]:
                unknown.append({"name": name, "reason": "common/prebound or weak-reference indirection"})
            elif matches:
                resolved.append({"name": name, "expected_library": library})
            elif imp["weak_import"]:
                optional_missing.append({"name": name, "expected_library": library})
            else:
                unresolved.append({"name": name, "expected_library": library})
        report["resolved_nlist"] = sorted(set(x["name"] for x in resolved))
        report["unresolved_nlist"] = sorted(set(x["name"] for x in unresolved))
        report["resolved_nlist_detail"] = sorted(resolved, key=lambda x: (x["name"], str(x["expected_library"])))
        report["unresolved_nlist_detail"] = sorted(unresolved, key=lambda x: (x["name"], str(x["expected_library"])))
        report["optional_missing_nlist"] = sorted(optional_missing, key=lambda x: x["name"])
        report["inconclusive_nlist"] = sorted(unknown, key=lambda x: x["name"])
        inconclusive = (not consumer["has_symtab"] or consumer["has_dyld_info"]
                        or bool(consumer["symbol_caveats"]) or bool(unknown)
                        or any(not x["has_symtab"] or x["has_dyld_info"]
                               or x["symbol_caveats"] for x in providers))
        report["status"] = "STATIC_INCONCLUSIVE" if inconclusive else "STATIC_AUDIT"
    elif args.strict:
        report["status"] = "STATIC_INCONCLUSIVE"
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.strict and report["status"] == "STATIC_INCONCLUSIVE":
        return 3
    if args.strict and report.get("unresolved_nlist"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
