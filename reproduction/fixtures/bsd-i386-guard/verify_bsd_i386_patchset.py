#!/usr/bin/env python3
"""D4rling BSD+variadic syscall i386: verify pinned XNU sources and patch hunks.

Read-only. Does not build, modify a checkout, fetch from network, or claim an
actual Darling runtime qualification. Can run on the i5-10400 via Debian WSL2.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

REV = "ba34c8ac576190d1bbacb6ee6b1903204a576114"
PINNED = {
    "darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/bsd_syscall_table.h": "a52497e33703b8cecfd41796bb498f1f5bbdc78c",
    "darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/bsd_syscall.S": "99b599cd9e854db3b0dc7250f5cf15a6ce4e2fab",
    "darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/bsd_syscall_table.c": "aa250999e06f68d082e41a1290a86b6410e04da4",
    "gen/bsdsyscalls/___syscall.S": "969b5847c4336fb16fa6a73fc06d9dc9ca38fe62",
    "libsyscall/custom/__syscall.S": "8d0c718312942ba3522c8ee9cdffb1c9dc472c4b",
}
PATCHES = {
    "bsd-i386-dispatch-guard-nosys-ba34c8ac.patch": {
        "blob": "15fe7c455313a2160120f8193d69892824e1e4d9",
        "files": tuple(list(PINNED)[:3]),
        "hunks": 5,
    },
    "bsd-i386-syscall-varargs-cf-ba34c8ac.patch": {
        "blob": "ecaf90a0bae2b445dcabd8dc55257cc1225edca8",
        "files": tuple(list(PINNED)[3:]),
        "hunks": 2,
    },
}


class GateError(Exception):
    pass


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def verify_pinned_content(path: str, data: bytes) -> str:
    if path not in PINNED:
        raise GateError(f"UNEXPECTED_SOURCE_PATH {path}")
    observed = git_blob(data)
    if observed != PINNED[path]:
        raise GateError(f"PINNED_BLOB_MISMATCH {path} {observed}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateError(f"SOURCE_NOT_UTF8 {path}") from exc


def git_read(repo: Path, *args: str) -> bytes:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1",
           "GIT_TERMINAL_PROMPT": "0"}
    try:
        return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE,
                                       env=env, timeout=15)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise GateError(f"GIT_OBJECT_UNAVAILABLE: {args[0]}") from exc


def load_xnu(repo: Path) -> dict[str, str]:
    commit = git_read(repo, "rev-parse", f"{REV}^{{commit}}").decode("ascii").strip()
    if commit != REV:
        raise GateError("WRONG_XNU_COMMIT")
    result = {}
    for path, oid in PINNED.items():
        actual = git_read(repo, "rev-parse", f"{REV}:{path}").decode("ascii").strip()
        if actual != oid:
            raise GateError(f"XNU_REVISION_PATH_MISMATCH {path}")
        result[path] = verify_pinned_content(path, git_read(repo, "cat-file", "blob", oid))
    return result


def load_pinned_dir(root: Path) -> dict[str, str]:
    result = {}
    for path in PINNED:
        target = root / path
        # Reject symlinked content and ancestor directories inside the pinned root.
        if target.is_symlink() or any(ancestor.is_symlink() for ancestor in target.parents if ancestor != root and root in ancestor.parents) or not target.is_file():
            raise GateError(f"MISSING_OR_SYMLINK_SOURCE {path}")
        try:
            data = target.read_bytes()
        except OSError as exc:
            raise GateError(f"UNREADABLE_SOURCE {path}") from exc
        result[path] = verify_pinned_content(path, data)
    return result


def split_patch(patch: str) -> list[tuple[str, list[dict]]]:
    """Parse a strict unified Git patch, rejecting unsupported operations."""
    files: list[tuple[str, list[dict]]] = []
    file_name = None
    hunks: list[dict] = []
    hunk = None
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            m = re.fullmatch(r"diff --git a/([^\s]+) b/([^\s]+)", line)
            if not m or m[1] != m[2] or m[1].startswith("/") or ".." in m[1].split("/"):
                raise GateError("BAD_PATCH_PATH")
            if file_name is not None:
                files.append((file_name, hunks))
            file_name, hunks, hunk = m[1], [], None
        elif line.startswith(("--- ", "+++ ")):
            if file_name is None or line[4:] != ("a/" if line.startswith("--- ") else "b/") + file_name:
                raise GateError("PATCH_PATH_DISAGREEMENT")
        elif line.startswith("@@ "):
            if file_name is None:
                raise GateError("HUNK_BEFORE_PATH")
            m = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if not m:
                raise GateError("BAD_HUNK_HEADER")
            hunk = {"old": int(m[1]), "old_count": int(m[2] or "1"),
                    "new": int(m[3]), "new_count": int(m[4] or "1"), "lines": []}
            hunks.append(hunk)
        elif hunk is not None and line and line[0] in " +-":
            hunk["lines"].append(line)
        elif line and line != "\\ No newline at end of file":
            raise GateError("UNEXPECTED_PATCH_DIRECTIVE")
    if file_name is not None:
        files.append((file_name, hunks))
    if not files or len({x[0] for x in files}) != len(files):
        raise GateError("EMPTY_OR_DUPLICATE_PATCH_PATHS")
    return files


def apply_hunks(source: str, hunks: list[dict]) -> str:
    original = source.splitlines(keepends=True)
    if not source.endswith("\n"):
        raise GateError("SOURCE_MISSING_FINAL_LF")
    lines = original[:]
    offset = 0
    last_old_end = 0
    for h in hunks:
        old_lines = [line[1:] + "\n" for line in h["lines"] if line[0] != "+"]
        new_lines = [line[1:] + "\n" for line in h["lines"] if line[0] != "-"]
        if len(old_lines) != h["old_count"] or len(new_lines) != h["new_count"]:
            raise GateError("HUNK_COUNT_MISMATCH")
        if h["old"] <= last_old_end:
            raise GateError("OVERLAPPING_HUNKS")
        start = h["old"] - 1 + offset
        if start < 0 or lines[start:start + len(old_lines)] != old_lines:
            raise GateError(f"SOURCE_HUNK_MISMATCH line={h['old']}")
        lines[start:start + len(old_lines)] = new_lines
        last_old_end = h["old"] + len(old_lines) - 1
        offset += len(new_lines) - len(old_lines)
    return "".join(lines)


def verify_patches(sources: dict[str, str], root: Path) -> tuple[int, int]:
    changed = sources.copy()
    checked = 0
    files_count = 0
    for name, spec in PATCHES.items():
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise GateError(f"MISSING_PATCH {name}")
        data = path.read_bytes()
        if git_blob(data) != spec["blob"]:
            raise GateError(f"PATCH_BLOB_MISMATCH {name}")
        structure = split_patch(data.decode("utf-8"))
        if set(f for f, _ in structure) != set(spec["files"]):
            raise GateError(f"PATCH_SCOPE_MISMATCH {name}")
        if sum(len(hunks) for _, hunks in structure) != spec["hunks"]:
            raise GateError(f"PATCH_HUNKS_MISMATCH {name}")
        for file_name, hunks in structure:
            if file_name not in changed:
                raise GateError(f"SOURCE_MISSING {file_name}")
            candidate = apply_hunks(changed[file_name], hunks)
            if candidate == changed[file_name]:
                raise GateError(f"UNCHANGED_SOURCE {file_name}")
            changed[file_name] = candidate
            checked += len(hunks)
            files_count += 1
    # Guard against unexpected variant behavior from genuine sources.
    bsd = changed["darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/bsd_syscall.S"]
    syscalls = [changed[p] for p in list(PINNED)[3:]]
    if "cmpl\t$BSD_SYSCALL_TABLE_SIZE, %eax" not in bsd or "movl\t%edx, (%esp)" not in bsd:
        raise GateError("BSD_GUARD_SEMANTICS_MISSING")
    if any(s.count("DARLING_SYSCALL_RESULT_TO_CF") != 1 for s in syscalls):
        raise GateError("SYSCALL_CF_GUARD_SEMANTICS_MISSING")
    return checked, files_count


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--xnu", type=Path, help="existing pinned Git source repository")
    group.add_argument("--pinned-dir", type=Path, help="preexisting files, checked by Git blob hash")
    args = p.parse_args()
    # Never uses any network or modifies originals. Patch paths are bundled with the checkout.
    patch_root = Path(__file__).resolve().parents[1] / "patches"
    try:
        sources = load_xnu(args.xnu) if args.xnu else load_pinned_dir(args.pinned_dir)
        count, files = verify_patches(sources, patch_root)
    except (GateError, UnicodeError, OSError) as exc:
        print(f"BSD_R6_SOURCE_GATE=BLOCKED_OR_FAIL {exc}")
        return 3
    print("BSD_R6_SOURCE_GATE=PASS_PINNED_HUNKS")
    print(f"BSD_R6_HUNKS={count}/7")
    print(f"BSD_R6_FILES={files}/5")
    print("BSD_R6_GIT_REVISION=" + (REV if args.xnu else "NOT_ESTABLISHED_BY_PINNED_DIR"))
    print("BSD_R6_COMPILE=OPEN")
    print("BSD_R6_DARLING_GUEST=OPEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
