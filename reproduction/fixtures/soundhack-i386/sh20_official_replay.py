#!/usr/bin/env python3
"""SH20: authenticate and replay SoundHack 0.896 from its official ZIP.

One private output directory, no system installation, no Mac guest execution.
Real assets are fetched only under explicit CLI flags; every downloaded
asset is SHA-256 checked. The legacy HFS+ payload is selected with a pinned
7-Zip portable binary and CPIO extraction is strict and bounded.
GPL-3.0-or-later; this file contains no SoundHack or Apple binary.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request
import zipfile

ORIGINAL_ZIP_URL = "https://tre.ucsd.edu/wordpress/wp-content/uploads/2016/12/SH896.dmg_.zip"
SEVEN_URL = "https://github.com/ip7z/7zip/releases/download/26.06/7z2606-linux-x64.tar.xz"
PIN_ZIP = "47c9596bcf9d6aa8ae98c0dd4231accf05cb5bff555a9b95f0ba70bb7db504ae"
PIN_DMG = "269b0446d45e6ab155c96c53bd89c4e69d709e28b29fae8837e9643b06fb25ee"
PIN_PAX = "8896cf91dd4eab673f2b2d2fd1113aa6af260dd21ff70ccbc74c26cb37bca719"
PIN_BIN = "6fb11c708079ca3b8f91dc53ab0d8ae732fbb8be32f0e22e34114764b9be089c"
PIN_SEVEN = "2b539cf067b2ad48e1baa5093dbaa8818b73542d1222a0ffde9dc5f2922ea62e"
DMG_SIZE = 1361910
ZIP_LIMIT = 1500000
SEVEN_LIMIT = 2200000
ELF_LIMIT = 12000000
CPIO_LIMIT = 20000000
BUNDLE_LIMIT = 8000000
PAX_MEMBER = "SH896/SoundHack 0.896 - Universal Binary.pkg/Contents/Archive.pax.gz"


class Blocked(ValueError):
    """Stop with an explicit, non-PASS result; preserve all evidence."""


def step(message: str) -> None:
    print("SH20_STEP=" + message, flush=True)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def approved(data: bytes, expected: str, label: str) -> bytes:
    if digest(data) != expected:
        raise Blocked(label + " SHA-256 differs from official pin")
    return data


def exclusive(path: Path, data: bytes, mode: int = 0o600) -> None:
    if path.exists() or path.is_symlink():
        raise Blocked("would overwrite existing artifact: " + path.name)
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise Blocked("output parent missing or symlinked")
    with path.open("xb") as stream:
        stream.write(data)
    path.chmod(mode)


def fetch(url: str, label: str, limit: int) -> bytes:
    step("FETCH_" + label)
    req = urllib.request.Request(url, headers={"User-Agent": "D4rling-SoundHack-SH20/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            final_url = urllib.parse.urlsplit(response.geturl())
            if final_url.scheme != "https":
                raise Blocked(label + " redirected to non-HTTPS URL")
            content = response.read(limit + 1)
    except (OSError, ValueError) as exc:
        raise Blocked(label + " HTTPS fetch failed: " + type(exc).__name__) from exc
    if len(content) > limit:
        raise Blocked(label + " exceeds download budget")
    return content


def extract_dmg_from_zip(archive: bytes) -> bytes:
    step("EXTRACT_ZIP_MEMBER")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            matches = [m for m in z.infolist() if not m.is_dir() and m.filename == "SH896.dmg"]
            if len(matches) != 1 or matches[0].file_size != DMG_SIZE:
                raise Blocked("one authentic SH896.dmg member required")
            if z.testzip() is not None:
                raise Blocked("ZIP CRC mismatch")
            image = z.read(matches[0])
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise Blocked("ZIP cannot be read: " + type(exc).__name__) from exc
    if len(image) != DMG_SIZE or image[-512:-508] != b"koly":
        raise Blocked("original image size or UDIF signature mismatch")
    approved(image, PIN_DMG, "DMG")
    print("SH20_PIN_DMG=PASS", flush=True)
    return image


def get_7zz_from_tar(archive: bytes) -> bytes:
    step("EXTRACT_VERIFIED_PORTABLE_7ZZ")
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:xz") as t:
            files = [x for x in t.getmembers() if x.isfile() and x.name.lstrip("./") == "7zz"]
            if len(files) != 1 or not 100000 < files[0].size < ELF_LIMIT:
                raise Blocked("portable 7zz missing or oversized")
            binary = t.extractfile(files[0]).read()
    except (tarfile.TarError, EOFError) as exc:
        raise Blocked("7zz archive invalid: " + type(exc).__name__) from exc
    if (len(binary) < 20 or binary[:4] != b"\x7fELF" or
            binary[4] != 2 or binary[5] != 1 or struct.unpack_from("<H", binary, 18)[0] != 62):
        raise Blocked("portable 7zz is not x86_64 Linux ELF")
    return binary


def cpio_odc(data: bytes) -> list[tuple[str, int, bytes]]:
    """Parse old ASCII cpio, used by the SH18 installer, without host helpers."""
    step("PARSE_CPIO_ODC")
    records = []
    pos = 0
    for _ in range(500):
        header = data[pos:pos + 76]
        if len(header) != 76 or header[:6] != b"070707":
            raise Blocked("expected legacy CPIO-ODC at offset " + str(pos))
        try:
            mode = int(header[18:24], 8)
            name_len = int(header[59:65], 8)
            size = int(header[65:76], 8)
        except ValueError as exc:
            raise Blocked("non-octal CPIO header") from exc
        pos += 76
        if not 1 <= name_len <= 1024 or size > BUNDLE_LIMIT or pos + name_len + size > len(data):
            raise Blocked("CPIO length outside bounds")
        raw_name = data[pos:pos + name_len]
        if raw_name[-1] != 0:
            raise Blocked("CPIO name is not NUL-terminated")
        pos += name_len
        try:
            name = raw_name[:-1].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise Blocked("non-UTF8 CPIO name") from exc
        entry = data[pos:pos + size]
        pos += size
        if name == "TRAILER!!!":
            return records
        if (not name or name.startswith("/") or "\\" in name or "\x00" in name
                or ".." in name.split("/") or len(name) > 512
                or any(ord(char) < 32 for char in name)):
            raise Blocked("unsafe CPIO path")
        records.append((name, mode, entry))
    raise Blocked("no CPIO trailer before member limit")


def extract_app(records: list[tuple[str, int, bytes]], target: Path) -> tuple[int, int]:
    step("EXTRACT_SOUNDHACK_APP_FILES")
    found: list[tuple[Path, bytes, int]] = []
    visited: set[str] = set()
    total = 0
    app_names: set[str] = set()
    for name, mode, content in records:
        parts = PurePosixPath(name).parts
        apps = [n for n, segment in enumerate(parts) if segment.lower().endswith(".app")]
        if not apps:
            continue
        idx = apps[0]
        app_names.add(parts[idx])
        if parts[idx] != "SoundHack.app":
            raise Blocked("unexpected app bundle inside official archive")
        kind = stat.S_IFMT(mode)
        if kind == stat.S_IFDIR:
            continue
        if kind != stat.S_IFREG:
            raise Blocked("special file or symlink inside application")
        rel = Path(*parts[idx + 1:])
        if not rel.parts or rel.is_absolute():
            raise Blocked("invalid app member")
        key = rel.as_posix()
        if key in visited:
            raise Blocked("duplicate application member")
        visited.add(key)
        total += len(content)
        if total > BUNDLE_LIMIT or len(visited) > 128:
            raise Blocked("app extraction budget exceeded")
        found.append((rel, content, mode))
    if app_names != {"SoundHack.app"} or len(found) != 8:
        raise Blocked("unexpected SoundHack bundle or file count")
    binary = [body for rel, body, _ in found if rel.as_posix() == "Contents/MacOS/SoundHack"]
    if len(binary) != 1:
        raise Blocked("original app executable missing")
    approved(binary[0], PIN_BIN, "SOUNDHACK_EXECUTABLE")
    if not any(rel.as_posix() == "Contents/Info.plist" for rel, _, _ in found):
        raise Blocked("Info.plist missing from original CPIO")
    if target.exists() or target.is_symlink():
        raise Blocked("application output already exists")
    # Every file and every path is validated BEFORE any application is written.
    target.mkdir(mode=0o700)
    for rel, body, mode in found:
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        exclusive(dest, body, mode=0o700 if mode & 0o111 else 0o600)
    print("SH20_PIN_SOUNDHACK_EXECUTABLE=PASS", flush=True)
    return len(found), total


def portable_hfs_extract(seven: Path, dmg: Path, output: Path) -> Path:
    step("EXTRACT_SINGLE_HFS_PAYLOAD")
    output.mkdir(mode=0o700)
    command = [str(seven), "x", "-y", "-bd", "-bb0", "-aoa", "-o" + str(output), str(dmg), PAX_MEMBER]
    try:
        p = subprocess.run(command, capture_output=True, timeout=45, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Blocked("7zz HFS extraction unavailable: " + type(exc).__name__) from exc
    if p.returncode != 0:
        raise Blocked("7zz HFS extraction failed rc=" + str(p.returncode) + ": " + p.stderr[:160].decode("utf8", "replace"))
    pax = output / PAX_MEMBER
    if any(folder.is_symlink() for folder in [*pax.parents][:4]) or pax.is_symlink() or not pax.is_file():
        raise Blocked("HFS payload missing or symbolic")
    if pax.stat().st_size > 4000000:
        raise Blocked("HFS payload exceeds budget")
    approved(pax.read_bytes(), PIN_PAX, "PAX")
    print("SH20_PIN_PAX=PASS", flush=True)
    return pax


def run_static_gate(app: Path, sysroot: Path | None, audit_dir: Path, output: Path) -> dict:
    step("RUN_EXISTING_SH19_MACHO_GATE")
    tool = audit_dir / "sh19_app_gate.py"
    parser = audit_dir / "macho_audit.py"
    if not all(p.is_file() and not p.is_symlink() and p.stat().st_size < 100000 for p in (tool, parser)):
        raise Blocked("SH19 gate or existing macho_audit.py missing")
    command = [sys.executable, "-B", str(tool), "--app", str(app), "--output", str(output)]
    if sysroot is not None:
        command.extend(("--sysroot", str(sysroot)))
    try:
        r = subprocess.run(command, capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Blocked("SH19 tool unavailable: " + type(exc).__name__) from exc
    if r.returncode != 0 or not output.is_file() or output.stat().st_size > 65536:
        raise Blocked("SH19 real-app static gate failed rc=" + str(r.returncode) + ": " + r.stdout[:180].decode("utf8", "replace"))
    result = json.loads(output.read_text())
    if result.get("status") != "SH19_ORIGINAL_APP_STATIC_INSPECTED" or result.get("executable_sha256") != PIN_BIN:
        raise Blocked("SH19 report lacks pinned original evidence")
    return result


def replay(zip_data: bytes, seven_data: bytes, output: Path,
           audit_dir: Path, sysroot: Path | None) -> dict:
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        raise Blocked("private output directory exists or parent is unavailable")
    if not audit_dir.is_dir() or audit_dir.is_symlink():
        raise Blocked("SH19 audit directory absent or symbolic")
    if sysroot is not None and (not sysroot.is_dir() or sysroot.is_symlink()):
        raise Blocked("private Darling sysroot missing or symbolic")
    # Validate both input digests before creating any output.
    approved(zip_data, PIN_ZIP, "ZIP")
    approved(seven_data, PIN_SEVEN, "7ZZ")
    image = extract_dmg_from_zip(zip_data)
    exe = get_7zz_from_tar(seven_data)
    output.mkdir(mode=0o700)
    exclusive(output / "SH896.dmg_.zip", zip_data)
    exclusive(output / "7z2606-linux-x64.tar.xz", seven_data)
    seven = output / "7zz-26.06"
    exclusive(seven, exe, mode=0o700)
    dmg = output / "SH896-original.dmg"
    exclusive(dmg, image)
    pax = portable_hfs_extract(seven, dmg, output / "hfs-selected")
    try:
        with gzip.open(pax, "rb") as stream:
            raw = stream.read(CPIO_LIMIT + 1)
    except (OSError, EOFError) as exc:
        raise Blocked("PAX gzip decode failed: " + type(exc).__name__) from exc
    if len(raw) > CPIO_LIMIT or not raw:
        raise Blocked("PAX decoded size outside budget")
    records = cpio_odc(raw)
    app = output / "SoundHack.app"
    count, size = extract_app(records, app)
    sh19 = run_static_gate(app, sysroot, audit_dir, output / "SH19-report.json")
    result = {
        "status": "SH20_OFFICIAL_APP_REPLAY_STATIC_PASS",
        "execution": "NOT_RUN", "carbon_gui": "NOT_RUN", "audio": "NOT_RUN",
        "verified_sha256": PIN_BIN, "bundle_files": count, "bundle_bytes": size,
        "original_zip_sha256": PIN_ZIP, "dmg_sha256": PIN_DMG,
        "installer_pax_sha256": PIN_PAX, "portable_7zz_archive_sha256": PIN_SEVEN,
        "cpio_records": len(records), "private_sysroot_checked": sysroot is not None,
        "sh19_status": sh19["status"],
        "nlist_import_count": sh19["nlist_import_count"],
        "dyld_dependency_count": len(sh19["dyld_load_commands"]),
        "strong_dependencies_not_found_at_literal_prefix_paths": sh19["strong_dependencies_not_found_at_literal_prefix_paths"],
        "dependency_overview": [{"kind": d["load_kind"], "name": d["install_name"],
                                 "location": d["static_location"]} for d in sh19["dyld_load_commands"]],
        "resource_forks": "NOT_VERIFIED_BY_ARCHIVE_EXTRACTION",
    }
    exclusive(output / "SH20-summary.json", (json.dumps(result, indent=2, sort_keys=True) + "\n").encode())
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True, help="new directory under existing private validation folder")
    p.add_argument("--audit-dir", type=Path, required=True, help="existing checkout or verified SH19 tools")
    p.add_argument("--sysroot", type=Path, help="optional, existing private Darling sysroot")
    p.add_argument("--zip", type=Path, help="existing, exact official ZIP")
    p.add_argument("--seven-archive", type=Path, help="existing, exact official 7-Zip archive")
    p.add_argument("--fetch-zip", action="store_true", help="explicitly fetch official ZIP over HTTPS")
    p.add_argument("--fetch-seven", action="store_true", help="explicitly fetch 7-Zip 26.06 over HTTPS")
    args = p.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
            raise Blocked("output must be a new directory under an existing parent")
        # Downloads remain in memory until their SHA-256 pins are verified;
        # replay exclusively owns the private output directory.
        zip_data = (fetch(ORIGINAL_ZIP_URL, "ZIP", ZIP_LIMIT) if args.fetch_zip else
                    args.zip.read_bytes() if args.zip and args.zip.is_file() and not args.zip.is_symlink() and args.zip.stat().st_size <= ZIP_LIMIT else None)
        seven_data = (fetch(SEVEN_URL, "7ZZ", SEVEN_LIMIT) if args.fetch_seven else
                      args.seven_archive.read_bytes() if args.seven_archive and args.seven_archive.is_file() and not args.seven_archive.is_symlink() and args.seven_archive.stat().st_size <= SEVEN_LIMIT else None)
        if zip_data is None or seven_data is None:
            raise Blocked("both official ZIP and verified portable 7zz archive required")
        report = replay(zip_data, seven_data, args.output, args.audit_dir, args.sysroot)
        print("SH20_STATUS=" + report["status"])
        print("SH20_IMPORTED_SYMBOLS=" + str(report["nlist_import_count"]))
        print("SH20_DYLIB_COUNT=" + str(report["dyld_dependency_count"]))
        print("SH20_MISSING_LITERAL_STRONG=" + str(report["strong_dependencies_not_found_at_literal_prefix_paths"]))
        for dep in report["dependency_overview"]:
            print("SH20_DEPENDENCY=" + dep["kind"] + " " + dep["location"] + " " + dep["name"])
        print("SH20_REPORT=" + str(args.output / "SH20-summary.json"))
        return 0
    except (Blocked, OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        print("SH20_STATUS=BLOCKED " + str(exc)[:240])
        print("SH20_EXECUTION=NO")
        return 3


if __name__ == "__main__":
    sys.exit(main())
