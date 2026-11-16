#!/usr/bin/env python3
"""SH19: evidence-bounded, OFFLINE inspection of SoundHack 0.896 Universal app.

Uses the existing macho_audit.py parser; never executes a guest, installs
software, modifies a prefix, or claims Carbon/QuickTime/audio compatibility.
GPL-3.0-or-later, D4rling-only wrapper; contains no Apple/SoundHack binaries.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import sys

ORIGINAL_SHA256 = "6fb11c708079ca3b8f91dc53ab0d8ae732fbb8be32f0e22e34114764b9be089c"
MAX_BUNDLE_FILES = 128
MAX_BUNDLE_BYTES = 32 * 1024 * 1024
MAX_PLIST_BYTES = 256 * 1024
MAX_REPORT_BYTES = 64 * 1024


class Blocked(ValueError):
    """Untrusted input or an unsatisfied invariant; no app compatibility PASS."""


def regular(path: Path, max_bytes: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise Blocked("missing, special or symbolic file: " + path.name)
    size = path.stat().st_size
    if size > max_bytes or size < 1:
        raise Blocked("unexpected file size: " + path.name)
    return path.read_bytes()


def bundle_inventory(bundle: Path) -> list[dict]:
    """List actual regular files; fail closed on symlinks and out-of-budget trees."""
    if not bundle.is_dir() or bundle.is_symlink() or bundle.name != "SoundHack.app":
        raise Blocked("SoundHack.app bundle missing or symlinked")
    files = []
    total = 0
    for directory, dirs, names in os.walk(bundle, followlinks=False):
        for d in dirs:
            if (Path(directory) / d).is_symlink():
                raise Blocked("symbolic directory in application")
        for name in names:
            p = Path(directory) / name
            if not p.is_file() or p.is_symlink():
                raise Blocked("non-regular file in application")
            size = p.stat().st_size
            total += size
            if total > MAX_BUNDLE_BYTES or len(files) >= MAX_BUNDLE_FILES:
                raise Blocked("bundle size/file budget exceeded")
            files.append({"path": p.relative_to(bundle).as_posix(), "bytes": size})
    return sorted(files, key=lambda f: f["path"])


def dependency_status(name: str, bundle: Path, binary: Path, prefix: Path | None) -> tuple[str, str]:
    """On-disk locator, NOT dyld binding: no loader or install-name simulation."""
    scope: Path | None
    if name.startswith("/") and prefix is not None:
        scope = prefix
        candidate = prefix / name.lstrip("/")
    elif name.startswith("@loader_path/") or name.startswith("@executable_path/"):
        scope = bundle
        candidate = binary.parent / name.split("/", 1)[1]
    else:
        return "NOT_RESOLVED_STATICALLY", ""

    resolved_scope = scope.resolve(strict=True)
    resolved_file = candidate.resolve(strict=False)
    if not resolved_file.is_relative_to(resolved_scope):
        return "OUTSIDE_AUTHORIZED_ROOT", ""
    if not candidate.exists():
        return "NOT_FOUND_AT_LITERAL_PATH", ""
    if not candidate.is_file():
        return "NOT_A_REGULAR_FILE", ""
    # A file's presence does NOT prove correct architecture, symbol binding,
    # framework version, nested dylib closure, or loader accessibility.
    return "FILE_PRESENT_NOT_LOAD_VERIFIED", str(candidate.relative_to(scope))


def audit_app(bundle: Path, prefix: Path | None = None,
              expected_sha: str = ORIGINAL_SHA256) -> dict:
    bundle = Path(bundle)
    file_inventory = bundle_inventory(bundle)
    binary = bundle / "Contents" / "MacOS" / "SoundHack"
    original = regular(binary, 8 * 1024 * 1024)
    digest = hashlib.sha256(original).hexdigest()
    if digest != expected_sha:
        raise Blocked("original SoundHack executable SHA-256 mismatch")
    plist = bundle / "Contents" / "Info.plist"
    info = plistlib.loads(regular(plist, MAX_PLIST_BYTES))
    if not isinstance(info, dict):
        raise Blocked("Info.plist is not a dictionary")
    if info.get("CFBundleExecutable") != "SoundHack":
        raise Blocked("Info.plist executable disagrees with pinned binary")
    if prefix is not None:
        prefix = Path(prefix)
        if not prefix.is_dir() or prefix.is_symlink():
            raise Blocked("private Darling sysroot missing or symlinked")
    from macho_audit import InvalidMachO, inspect  # existing tested parser
    try:
        parsed = inspect(binary, "i386")
    except (OSError, InvalidMachO) as exc:
        raise Blocked("Mach-O parser rejected binary: " + type(exc).__name__) from exc
    if (parsed["arch"] != "i386" or parsed["bits"] != 32 or parsed["filetype"] != 2):
        raise Blocked("required i386 MH_EXECUTE absent")
    slices = parsed.get("fat_slices", [])
    if sorted(s["arch"] for s in slices) != ["i386", "ppc"]:
        raise Blocked("original Universal Binary architecture table differs")
    if parsed["sha256"] != digest:
        raise Blocked("Mach-O parser and package hash disagree")
    dependencies = []
    missing_strong = 0
    for d in parsed["dylibs"]:
        if d["kind"] == "id":
            raise Blocked("unexpected dylib install name in MH_EXECUTE")
        location, located = dependency_status(d["name"], bundle, binary, prefix)
        dependencies.append({"load_kind": d["kind"], "install_name": d["name"],
                             "static_location": location, "relative_location": located})
        if prefix is not None and d["kind"] not in ("weak", "lazy") and location == "NOT_FOUND_AT_LITERAL_PATH":
            missing_strong += 1
    resource_files = [f["path"] for f in file_inventory if f["path"].startswith("Contents/Resources/")]
    return {
        "status": "SH19_ORIGINAL_APP_STATIC_INSPECTED",
        "app": "SoundHack 0.896 (official Universal Binary)",
        "evidence_level": "STATIC_ONLY_NOT_SH_LOAD",
        "executable_sha256": digest,
        "arch": "i386", "filetype": "MH_EXECUTE",
        "fat_arches": [s["arch"] for s in slices],
        "bundle_files": file_inventory, "bundle_file_count": len(file_inventory),
        "resource_files": resource_files,
        "resource_forks": "NOT_VERIFIED_IN_LEGACY_CPIO_EXTRACTION",
        "bundle_identifier": str(info.get("CFBundleIdentifier", "NOT_DECLARED"))[:160],
        "minimum_os": str(info.get("LSMinimumSystemVersion", "NOT_DECLARED"))[:32],
        "dyld_load_commands": dependencies,
        "nlist_import_count": len(parsed["imports_nlist"]),
        "nlist_ordinal_detail_count": len(parsed["imports_detail"]),
        "symtab_present": parsed["has_symtab"],
        "dyld_info_present": parsed["has_dyld_info"],
        "two_level_namespace": parsed["two_level_namespace"],
        "strong_dependencies_not_found_at_literal_prefix_paths": missing_strong,
        "private_sysroot_checked": prefix is not None,
        "execution": "NOT_RUN", "carbon_gui": "NOT_RUN", "audio": "NOT_RUN",
        "caveat": "Literal on-disk presence is not a dyld/ABI resolution or SoundHack launch PASS.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True,
                        help="existing SoundHack.app extracted from authentic 0.896 CPIO")
    parser.add_argument("--sysroot", type=Path,
                        help="existing private libexec/darling root; strictly read-only")
    parser.add_argument("--output", type=Path,
                        help="exclusive-create JSON report in approved validation area")
    args = parser.parse_args(argv)
    try:
        result = audit_app(args.app, args.sysroot)
        output = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()
        if len(output) > MAX_REPORT_BYTES:
            raise Blocked("report exceeds 64 KiB")
        if args.output is not None:
            if args.output.is_symlink() or args.output.exists() or not args.output.parent.is_dir():
                raise Blocked("output must be a new file in an existing directory")
            with args.output.open("xb") as stream:
                stream.write(output)
        sys.stdout.buffer.write(output)
        return 0
    except (OSError, ValueError, plistlib.InvalidFileException) as exc:
        print(json.dumps({"status": "SH19_BLOCKED", "reason": str(exc)[:240]},
                         sort_keys=True))
        return 3


if __name__ == "__main__":
    sys.exit(main())
