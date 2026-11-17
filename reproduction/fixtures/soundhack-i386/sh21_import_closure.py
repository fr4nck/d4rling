#!/usr/bin/env python3
"""SoundHack SH21: read-only, evidence-limited i386 nlist import closure.

Matches the genuine 0.896 MH_EXECUTE nlist ordinals to the seven private
Mach-O providers. Does NOT execute dyld, Mac binaries, a GUI or audio.
Uses the existing pinned macho_audit.py; no independent Mach-O parser.
GPL-3.0-or-later. Never writes source/build/prefix and never installs.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

PIN_ORIGINAL = "6fb11c708079ca3b8f91dc53ab0d8ae732fbb8be32f0e22e34114764b9be089c"
PIN_PARSER_GIT_BLOB = "0ac6e95301ed563bfb12cadabb444fda520f3c09"
PIN_SH20_ZIP = "47c9596bcf9d6aa8ae98c0dd4231accf05cb5bff555a9b95f0ba70bb7db504ae"
MAX_EXE = 8 * 1024 * 1024
MAX_PROVIDER = 128 * 1024 * 1024
MAX_REPORT = 256 * 1024


class Blocked(ValueError):
    """A source or evidence precondition is not met."""


def hash_file(path: Path, limit: int) -> str:
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= limit:
        raise Blocked("missing, symbolic or oversized: " + path.name)
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def validate_bundle(app: Path, summary: Path, parser_file: Path) -> None:
    if not app.is_dir() or app.is_symlink() or app.name != "SoundHack.app":
        raise Blocked("expected original SoundHack.app directory")
    exe = app / "Contents" / "MacOS" / "SoundHack"
    if hash_file(exe, MAX_EXE) != PIN_ORIGINAL:
        raise Blocked("original 0.896 SoundHack SHA-256 mismatch")
    if summary.is_symlink() or not summary.is_file() or summary.stat().st_size > 65536:
        raise Blocked("SH20-summary.json is missing or untrusted")
    try:
        evidence = json.loads(summary.read_text("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise Blocked("invalid SH20-summary.json") from exc
    if (evidence.get("status") != "SH20_OFFICIAL_APP_REPLAY_STATIC_PASS"
            or evidence.get("verified_sha256") != PIN_ORIGINAL
            or evidence.get("original_zip_sha256") != PIN_SH20_ZIP
            or evidence.get("bundle_files") != 8
            or evidence.get("nlist_import_count") != 393):
        raise Blocked("SH20 real-app evidence values do not match")
    if (parser_file.is_symlink() or not parser_file.is_file()
            or parser_file.stat().st_size > 50000
            or git_blob(parser_file) != PIN_PARSER_GIT_BLOB):
        raise Blocked("existing macho_audit.py Git blob differs from verified parser")


def provider_record(name: str, sysroot: Path, macho) -> dict:
    """Only inspect a provider inside the existing private Darling prefix."""
    record = {"install_name_requested": name, "status": "NOT_INSPECTED",
              "nlist_defined_count": 0, "candidate_id": None,
              "dyld_info": None, "has_symtab": None}
    if not name.startswith("/"):
        record["status"] = "NON_ABSOLUTE_INSTALL_NAME"
        return record
    root = sysroot.resolve(strict=True)
    path = sysroot / name.lstrip("/")
    actual = path.resolve(strict=False)
    if not actual.is_relative_to(root):
        record["status"] = "SYMLINK_ESCAPE_BLOCKED"
        return record
    if not actual.is_file():
        record["status"] = "PROVIDER_NOT_A_FILE"
        return record
    if actual.stat().st_size > MAX_PROVIDER:
        record["status"] = "PROVIDER_OVERSIZED"
        return record
    try:
        parsed = macho.inspect(actual, "i386")
    except (macho.InvalidMachO, OSError, ValueError) as exc:
        record["status"] = "I386_MACHO_NOT_INSPECTABLE"
        record["error_type"] = type(exc).__name__
        return record
    if parsed.get("filetype") not in (6, 9) or parsed.get("bits") != 32:
        record["status"] = "PROVIDER_NOT_I386_DYLIB"
        return record
    if not parsed.get("has_symtab"):
        record["status"] = "I386_PROVIDER_NLIST_ABSENT"
        return record
    record["status"] = "I386_PROVIDER_PARSED"
    record["candidate_id"] = parsed.get("install_name")
    record["name_identity"] = ("EXACT" if parsed.get("install_name") == name else
                               "MISMATCH_OR_ABSENT")
    record["sha256"] = parsed["sha256"]
    record["has_symtab"] = parsed["has_symtab"]
    record["dyld_info"] = parsed["has_dyld_info"]
    record["symbol_caveats_count"] = len(parsed.get("symbol_caveats", []))
    record["reexports_recorded"] = [d["name"] for d in parsed["dylibs"]
                                    if d["kind"] == "reexport"]
    record["nlist_defined_count"] = len(parsed["exports_nlist"])
    record["nlist_defined"] = set(parsed["exports_nlist"])
    return record


def classify_import(item: dict, providers: dict[str, dict]) -> tuple[str, list[str]]:
    lookup = item.get("lookup")
    name = item.get("name", "")
    lib = item.get("library_name")
    if item.get("common_or_prebound") or item.get("reference_to_weak"):
        return "INCONCLUSIVE_NONSTANDARD_REFERENCE", []
    if lookup != "library" or not isinstance(lib, str) or not lib:
        return "INCONCLUSIVE_SPECIAL_LOOKUP", []
    p = providers.get(lib)
    if p is None:
        return "INCONCLUSIVE_UNLISTED_ORDINAL_LIBRARY", []
    if p["status"] != "I386_PROVIDER_PARSED":
        return "INCONCLUSIVE_PROVIDER_UNAVAILABLE", []
    if name in p["nlist_defined"]:
        if p["name_identity"] == "EXACT":
            return "NAME_DIRECT_IN_EXPECTED_LIBRARY", []
        return "NAME_PRESENT_IDENTITY_UNVERIFIED", []
    others = sorted(n for n, other in providers.items()
                    if n != lib and other["status"] == "I386_PROVIDER_PARSED"
                    and name in other["nlist_defined"])
    return ("NAME_ONLY_IN_OTHER_LOADED_LIBRARY" if others else
            "NAME_NOT_IN_DIRECT_PROVIDER_NLIST"), others


def analyze(consumer: dict, providers: dict[str, dict]) -> dict:
    if (consumer.get("arch") != "i386" or consumer.get("filetype") != 2
            or consumer.get("sha256") != PIN_ORIGINAL or consumer.get("bits") != 32):
        raise Blocked("actual consumer Mach-O no longer matches original app")
    if sorted(s["arch"] for s in consumer.get("fat_slices", [])) != ["i386", "ppc"]:
        raise Blocked("expected historical PPC+i386 universal executable")
    if len(consumer["imports_nlist"]) != 393:
        raise Blocked("original imported symbol count differs from SH20")
    # Do not collapse duplicate ordinal records into one name; preserve each.
    recs = consumer["imports_detail"]
    counts = Counter()
    by_lib = defaultdict(Counter)
    observations = []
    for entry in recs:
        name = entry["name"]
        state, other = classify_import(entry, providers)
        counts[state] += 1
        owner = entry.get("library_name") or "<special_lookup>"
        by_lib[owner][state] += 1
        observations.append({"symbol": name, "expected_library": entry.get("library_name"),
                             "lookup": entry.get("lookup"), "weak": bool(entry.get("weak_import")),
                             "classification": state, "other_direct_nlist_libraries": other})
    non_direct = [r for r in observations if r["classification"] != "NAME_DIRECT_IN_EXPECTED_LIBRARY"]
    report_providers = []
    for requested, info in providers.items():
        report_providers.append({k: v for k, v in info.items() if k != "nlist_defined"})
    return {
        "status": "SH21_STATIC_IMPORT_CLASSIFIED",
        "qualification": "NAMES_ONLY_NO_DYLD_BINDING_OR_RUNTIME",
        "app_sha256": PIN_ORIGINAL,
        "app_arch": "i386",
        "app_nlist_unique_imports": len(consumer["imports_nlist"]),
        "app_nlist_ordinal_records": len(recs),
        "two_level_namespace": consumer["two_level_namespace"],
        "consumer_has_dyld_info": consumer["has_dyld_info"],
        "provider_count": len(providers),
        "provider_i386_macho_parsed": sum(p["status"] == "I386_PROVIDER_PARSED" for p in providers.values()),
        "provider_id_exact": sum(p.get("name_identity") == "EXACT" for p in providers.values()),
        "classification_counts": dict(sorted(counts.items())),
        "per_library_counts": {lib: dict(sorted(c.items())) for lib, c in sorted(by_lib.items())},
        "providers": report_providers,
        "non_direct_import_samples": non_direct[:30],
        "imports": observations,
        "caveats": [
            "No dyld bind/reexport traversal, lazy lookup, ObjC registration or transitive dependencies verified.",
            "A missing direct nlist name is NOT proof the symbol cannot bind at runtime.",
            "A direct nlist name is NOT proof ABI, calling convention or functional behavior.",
            "The application, GUI, DSP and audio were NOT executed.",
        ],
        "guest_executed": False,
    }


def print_short(result: dict) -> None:
    print("SH21_STATUS=" + result["status"], flush=True)
    print("ORIGINAL_APP_PIN=PASS I386=PASS", flush=True)
    print("IMPORTS_UNIQUE=" + str(result["app_nlist_unique_imports"]), flush=True)
    print("IMPORT_RECORDS=" + str(result["app_nlist_ordinal_records"]), flush=True)
    print("PROVIDERS_PARSED=%d/%d" % (result["provider_i386_macho_parsed"], result["provider_count"]), flush=True)
    print("PROVIDER_IDENTITIES_EXACT=%d/%d" % (result["provider_id_exact"], result["provider_count"]), flush=True)
    for status, count in result["classification_counts"].items():
        print("IMPORT_CLASS=" + status + ":" + str(count), flush=True)
    for lib, kinds in sorted(result["per_library_counts"].items()):
        direct = kinds.get("NAME_DIRECT_IN_EXPECTED_LIBRARY", 0)
        remaining = sum(kinds.values()) - direct
        print("IMPORT_LIBRARY=" + lib.rsplit("/", 1)[-1] +
              " DIRECT=%d OTHER=%d" % (direct, remaining), flush=True)
    for item in result["non_direct_import_samples"][:3]:
        print("IMPORT_TO_REVIEW=" + item["classification"] + " " + item["symbol"] +
              " LIB=" + str(item["expected_library"]), flush=True)
    print("DYLD_RUNTIME=NOT_TESTED APP_EXECUTED=NO AUDIO=NO", flush=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--app", required=True, type=Path)
    p.add_argument("--summary", required=True, type=Path)
    p.add_argument("--sysroot", required=True, type=Path)
    p.add_argument("--parser", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args(argv)
    try:
        if (not a.sysroot.is_dir() or a.sysroot.is_symlink()
                or not a.output.parent.is_dir() or a.output.parent.is_symlink()
                or a.output.exists() or a.output.is_symlink()):
            raise Blocked("sysroot or exclusive report destination unavailable")
        validate_bundle(a.app, a.summary, a.parser)
        sys.path.insert(0, str(a.parser.parent))
        import macho_audit as macho
        print("SH21_STEP=1/3 ORIGINAL_APP_AND_PINS_PASS", flush=True)
        app_info = macho.inspect(a.app / "Contents" / "MacOS" / "SoundHack", "i386")
        expected = [entry["name"] for entry in app_info["dylibs"]]
        if len(expected) != 7 or len(set(expected)) != 7 or not app_info["two_level_namespace"]:
            raise Blocked("not the seven two-level SoundHack 0.896 load commands")
        providers = {}
        for i, name in enumerate(expected, 1):
            print("SH21_STEP=2/3 PROVIDER_%d_OF_7=%s" % (i, name.rsplit("/", 1)[-1]), flush=True)
            providers[name] = provider_record(name, a.sysroot, macho)
        report = analyze(app_info, providers)
        content = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
        if len(content) > MAX_REPORT:
            raise Blocked("report exceeds maximum 256 KiB")
        with a.output.open("xb") as stream:
            stream.write(content)
        print("SH21_STEP=3/3 REPORT_RECORDED", flush=True)
        print_short(report)
        print("SH21_REPORT=" + str(a.output), flush=True)
        return 0
    except (Blocked, OSError, ValueError, KeyError, TypeError) as exc:
        # Never echo arbitrary JSON payloads or user secrets into a chat report.
        print("SH21_STATUS=BLOCKED", flush=True)
        print("SH21_REASON=" + type(exc).__name__ + ":" + str(exc)[:160], flush=True)
        print("DYLD_RUNTIME=NOT_TESTED", flush=True)
        return 3


if __name__ == "__main__":
    sys.exit(main())
