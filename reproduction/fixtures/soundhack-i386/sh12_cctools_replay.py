#!/usr/bin/env python3
"""SH12: resume SoundHack i386 link from the verified SH10 package.

Only an existing local cctools-port ELF linker is considered. No installs,
network, downloads, SDK, guest or audio. Not a proof of app compatibility.
GPL-3.0-or-later (C) 2026 D4rling contributors.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

from i386_link_gate import (EXPECTED_SH08_SHA256, inspect_macho,
                            Inconclusive as LinkInconclusive,
                            ContractFailure as LinkContractFailure)
from darwin_archive_gate import qualify as qualify_link

ARCHIVE_SHA256 = "c11833539630b5aa70d6d63a44d4063eb11a12f0f316884094b0b64f38707169"
ARCHIVE_BYTES = 4000
OBJECT_BYTES = 3236
ARCHIVE_NAME = "libSoundHackFFT_i386.a"
PACKAGE_ITEMS = frozenset({ARCHIVE_NAME, "NOTICE.txt", "LICENSE-MIT-SoundHack.txt",
                           "qualification.json", "SH10-darwin-static-archive.md"})
MAX_PACKAGE_BYTES = 1024 * 1024
MAX_UNPACKED_BYTES = 2 * 1024 * 1024
MAX_LINKER_BYTES = 256 * 1024 * 1024
CANDIDATE_FOLDERS = (
    "src/external/cctools-port/cctools/ld64/src",
    "cctools-port/cctools/ld64/src",
    "cctools/ld64/src",
    "ld64/src",
)
LD_NAME = re.compile(r"^(?:ld|ld64|(?:i386|x86_64|aarch64)-apple-darwin\d+-ld)$")
MACHINE = {"x86_64": 62, "amd64": 62, "aarch64": 183, "arm64": 183}


class Inconclusive(Exception):
    pass


class ContractFailure(Exception):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_tool(args: list[str], timeout: int = 25) -> subprocess.CompletedProcess:
    try:
        res = subprocess.run(args, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Inconclusive(f"tool not available or timed out: {args[0]}") from exc
    if len(res.stdout) > MAX_UNPACKED_BYTES or len(res.stderr) > 100000:
        raise Inconclusive("oversized tool output")
    return res


def read_sh10_package(package: Path, temp: Path, ar: str = "llvm-ar") -> dict:
    """Verify the actual SH10 archive, extract only the SHA-pinned FFT object."""
    if package.is_symlink() or not package.is_file() or not 0 < package.stat().st_size <= MAX_PACKAGE_BYTES:
        raise Inconclusive("SH10 ZIP missing, symlinked or oversized")
    try:
        with zipfile.ZipFile(package) as zipped:
            entries = zipped.infolist()
            names = [entry.filename for entry in entries]
            if len(entries) != len(PACKAGE_ITEMS) or set(names) != PACKAGE_ITEMS:
                raise ContractFailure("unexpected or duplicate ZIP entry names")
            if any(entry.flag_bits & 1 or entry.is_dir() or entry.file_size > MAX_UNPACKED_BYTES
                   for entry in entries) or sum(entry.file_size for entry in entries) > MAX_UNPACKED_BYTES:
                raise ContractFailure("encrypted, directory, or oversized ZIP content")
            if zipped.testzip() is not None:
                raise ContractFailure("ZIP entry CRC mismatch")
            archive_bytes = zipped.read(ARCHIVE_NAME)
            notice = zipped.read("LICENSE-MIT-SoundHack.txt")
            meta = json.loads(zipped.read("qualification.json"))
    except (zipfile.BadZipFile, OSError, EOFError, KeyError, json.JSONDecodeError) as exc:
        raise Inconclusive("SH10 ZIP unreadable") from exc
    if (len(archive_bytes) != ARCHIVE_BYTES or digest(archive_bytes) != ARCHIVE_SHA256):
        raise ContractFailure("SH10 Darwin archive digest differs from canonical SH10")
    if not (b"MIT License" in notice and b"Tom Erbe" in notice):
        raise ContractFailure("SoundHack MIT license notice absent")
    if (not isinstance(meta, dict) or not isinstance(meta.get("archive"), dict)
            or not isinstance(meta.get("source_object"), dict)
            or meta["archive"].get("sha256") != ARCHIVE_SHA256
            or meta["source_object"].get("sha256") != EXPECTED_SH08_SHA256):
        raise ContractFailure("SH10 package manifest does not match archive/object digests")
    command = shutil.which(ar)
    if not command:
        raise Inconclusive("llvm-ar not installed")
    archive_path = temp / ARCHIVE_NAME
    archive_path.write_bytes(archive_bytes)
    names_result = run_tool([command, "t", str(archive_path)])
    if names_result.returncode or names_result.stdout.splitlines() != [b"fft.o", b"globals.o"]:
        raise ContractFailure("unexpected Darwin archive members/order")
    member = run_tool([command, "p", str(archive_path), "fft.o"])
    if member.returncode:
        raise Inconclusive("llvm-ar could not read FFT member")
    if len(member.stdout) != OBJECT_BYTES + 4 or member.stdout[OBJECT_BYTES:] != b"\n" * 4:
        raise ContractFailure("SH10 FFT member padding differs from Darwin alignment")
    source = member.stdout[:OBJECT_BYTES]
    if digest(source) != EXPECTED_SH08_SHA256:
        raise ContractFailure("SH08 FFT object digest mismatch after archive read")
    object_path = temp / "original-sh08-target.o"
    object_path.write_bytes(source)
    obj_info = inspect_macho(object_path, EXPECTED_SH08_SHA256)
    return {"package_sha256": digest(package.read_bytes()),
            "archive_sha256": ARCHIVE_SHA256,
            "object_sha256": obj_info["sha256"],
            "object_path": object_path}


def linker_identity(path: Path, root: Path) -> dict:
    """Conservatively identify an executable ELF inside a cctools-port build."""
    if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
        raise Inconclusive("linker candidate is not an executable regular file")
    canonical = path.resolve()
    if not canonical.is_relative_to(root.resolve()) or "cctools-port" not in canonical.parts:
        raise Inconclusive("linker candidate outside canonical cctools-port build tree")
    if path.name == "ld64.lld" or not LD_NAME.fullmatch(path.name):
        raise Inconclusive("not a cctools-port ld64 candidate name")
    size = path.stat().st_size
    if not 64 <= size <= MAX_LINKER_BYTES:
        raise Inconclusive("linker binary outside bounded size")
    with path.open("rb") as f:
        header = f.read(64)
    expected_machine = MACHINE.get(platform.machine().lower())
    if (expected_machine is None or header[:4] != b"\x7fELF" or header[4] != 2 or header[5] != 1
            or struct.unpack_from("<H", header, 16)[0] not in (2, 3)
            or struct.unpack_from("<H", header, 18)[0] != expected_machine):
        raise Inconclusive("candidate is not a native host ELF64 linker")
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    if path.stat().st_size != size:
        raise Inconclusive("linker changed during hashing")
    return {"path": str(canonical), "sha256": sha.hexdigest(), "bytes": size,
            "identity_scope": "native ELF + path + SHA-256; source provenance NOT proved"}


def find_linkers(build_root: Path) -> list[dict]:
    if build_root.is_symlink() or not build_root.is_dir():
        raise Inconclusive("build root missing or symlinked")
    root = build_root.resolve()
    files = set()
    for relative in CANDIDATE_FOLDERS:
        parent = root / relative
        if not parent.is_dir() or parent.is_symlink():
            continue
        for path in parent.iterdir():
            if LD_NAME.fullmatch(path.name) and "cctools-port" in path.resolve().parts:
                files.add(path)
    candidates = []
    for path in sorted(files):
        try:
            candidates.append(linker_identity(path, root))
        except Inconclusive:
            # A non-executable or incompatible candidate can never become a PASS.
            continue
    return candidates


def qualify(package: Path, build_root: Path | None, output: Path | None = None,
            ar: str = "llvm-ar") -> dict:
    with tempfile.TemporaryDirectory(prefix="d4rl-sh12-") as folder:
        temp = Path(folder)
        source = read_sh10_package(package, temp, ar=ar)
        base = {"status": "LINKER_ABSENT", "scope": "real pinned SH10 package; no GUI/guest/audio",
                "package_sha256": source["package_sha256"],
                "archive_sha256": source["archive_sha256"],
                "object_sha256": source["object_sha256"]}
        if build_root is None:
            base["reason"] = "D4RLING_BUILD_ROOT or --build-root is required"
            return base
        candidates = find_linkers(build_root)
        base["linker_candidates"] = candidates
        if not candidates:
            base["reason"] = "no native cctools-port ld64 ELF in bounded build paths"
            return base
        if len(candidates) != 1:
            base["status"] = "LINKER_AMBIGUOUS"
            base["reason"] = "multiple cctools linkers; refuse automatic selection"
            return base
        found = candidates[0]
        # Reuse SH11's archive, linker SHA verification and fail-closed dylib checks.
        result = qualify_link(source["object_path"],
                              linker=found["path"], linker_sha256=found["sha256"],
                              linked_output=output)
        base["status"] = result["status"]
        base["link_attempt"] = result.get("link_attempt")
        base["linker"] = found
        if output is not None and result["status"] == "LINK_STRUCTURE_PASS":
            base["linked_output"] = str(output)
        return base


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sh10-package", required=True, type=Path,
                        help="existing, unmodified SH10 ZIP from this project")
    parser.add_argument("--build-root", type=Path,
                        default=Path(os.environ["D4RLING_BUILD_ROOT"]) if os.environ.get("D4RLING_BUILD_ROOT") else None,
                        help="one already existing canonical build root; no recursive home scan")
    parser.add_argument("--linked-output", type=Path,
                        help="optional new-only output path, used only if linked dylib checks pass")
    parser.add_argument("--llvm-ar", default="llvm-ar", help="already-installed LLVM ar")
    args = parser.parse_args(argv)
    try:
        result = qualify(args.sh10_package, args.build_root, args.linked_output, args.llvm_ar)
    except (ContractFailure, LinkContractFailure) as exc:
        result, status = {"status": "TARGET_CONTRACT_FAIL", "error": str(exc)}, 2
    except (Inconclusive, LinkInconclusive, OSError, ValueError) as exc:
        result, status = {"status": "INCONCLUSIVE", "error": str(exc)}, 3
    else:
        status = 0 if result["status"] == "LINK_STRUCTURE_PASS" else 3
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return status


if __name__ == "__main__":
    sys.exit(main())
