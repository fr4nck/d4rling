#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fetch six pinned public source files for an independent i386 CMake contract check.

This does not clone repositories, run downloaded code, modify a checkout,
invoke Darling, or write outside a new output directory. Git blob SHA-1s are
checked after download against the pin's original content object identifier.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import urllib.error
import urllib.request

MAX_SOURCE_BYTES = 256 * 1024
# (checkout-relative output, repo, submodule commit, source path, git blob SHA)
SOURCES = (
    (
        "src/external/xnu/darling/src/libsystem_kernel/CMakeLists.txt",
        "darlinghq/darling-xnu", "fa29287aa2f0115271e091f1031f53c9e024005d",
        "darling/src/libsystem_kernel/CMakeLists.txt", "e14e7ea9ddefba0a909d42891c34f45378c1dde6",
    ),
    (
        "src/external/xnu/libsyscall/CMakeLists.txt",
        "darlinghq/darling-xnu", "fa29287aa2f0115271e091f1031f53c9e024005d",
        "libsyscall/CMakeLists.txt", "57cebadf8741c99cad1badc0f9816eb37aa8f314",
    ),
    (
        "src/external/xnu/libsyscall/wrappers/_libkernel_init.c",
        "darlinghq/darling-xnu", "fa29287aa2f0115271e091f1031f53c9e024005d",
        "libsyscall/wrappers/_libkernel_init.c", "d3481895fd58a8f71351fd6097c68e3d1edaf798",
    ),
    (
        "src/external/libmalloc/CMakeLists.txt",
        "darlinghq/darling-libmalloc", "a57991e2651226a675654bd96e5d9ab6bec288c5",
        "CMakeLists.txt", "748420cabda3be9012b7ac876b2bfa4b29031c89",
    ),
    (
        "src/external/libmalloc/src/malloc.c",
        "darlinghq/darling-libmalloc", "a57991e2651226a675654bd96e5d9ab6bec288c5",
        "src/malloc.c", "c6c2a5a67e1fae38b3df9ba87afc36facd012533",
    ),
    (
        "src/external/libsystem/CMakeLists.txt",
        "darlinghq/darling-Libsystem", "08df454b6eb0df9400aa4c39839a7efd6efd2c3c",
        "CMakeLists.txt", "1bc702c87d25f29c10d06ad5277b302c771596d1",
    ),
)


class PinError(ValueError):
    pass


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "d4rling-qt112-pinned-source-check/1"})
    with urllib.request.urlopen(request, timeout=18) as response:
        data = response.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES:
        raise PinError("source exceeds size limit")
    return data


def fetch_pinned(root: Path, fetcher=fetch_bytes) -> list[dict]:
    # Reject a pre-existing directory, file, or symlink rather than silently
    # touching earlier qualification material.
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    evidence = []
    for relative, repo, commit, source_path, expected_blob in SOURCES:
        url = f"https://raw.githubusercontent.com/{repo}/{commit}/{source_path}"
        data = fetcher(url)
        if len(data) > MAX_SOURCE_BYTES:
            raise PinError(f"oversize source: {relative}")
        observed_blob = git_blob_sha(data)
        if observed_blob != expected_blob:
            raise PinError(f"pinned git blob mismatch: {relative} ({observed_blob})")
        target = root / relative
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        evidence.append({
            "path": relative, "repo": repo, "commit": commit,
            "git_blob_sha": observed_blob,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        })
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="new nonexisting output directory")
    args = parser.parse_args()
    try:
        info = fetch_pinned(args.output_dir)
        for row in info:
            print(f"VERIFIED={row['git_blob_sha']} {row['path']}")
        print(f"PINNED_FILES={len(info)} PASS")
        return 0
    except (OSError, PinError, urllib.error.URLError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
