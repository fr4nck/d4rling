#!/usr/bin/env python3
"""D4rling/i5-10400 read-only preflight. No network, builds or file changes.

The 10400 has a protected historical checkout and build. This script NEVER
updates, resets or cleans those trees, and does not run any guest binary.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

XNU_REV = "ba34c8ac576190d1bbacb6ee6b1903204a576114"


def probe_git(path: Path, *args: str) -> tuple[bool, str]:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1",
           "GIT_TERMINAL_PROMPT": "0"}
    try:
        proc = subprocess.run(["git", "-C", str(path), *args], env=env,
                              text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, type(exc).__name__
    if proc.returncode:
        return False, "not available"
    return True, proc.stdout.strip()


def xnu_candidates(canon: Path, historical: Path) -> list[Path]:
    bases = [canon, historical]
    result = []
    names = ("src/external/darling-xnu", "src/external/xnu", "src/external/darling/src/external/darling-xnu",
             "src/external/darling/src/external/xnu", "src/external/darling-xnu/src",
             "src/external/darling-xnu/darling", "src/external/darling-xnu")
    for base in bases:
        for name in names:
            p = base / name
            if p.is_dir() and p not in result:
                result.append(p)
    # Check the source tree itself: some historical layouts use source/xnu.
    for base in bases:
        for name in ("xnu", "darling-xnu"):
            p = base / name
            if p.is_dir() and p not in result:
                result.append(p)
    return result


def inventory(home: Path) -> dict[str, str]:
    atelier = home / "atelier"
    canon = atelier / "d4rling"
    hist = atelier / "d4rling-10400" / "source"
    build = atelier / "d4rling-10400" / "build-core-i386"
    out = atelier / "d4rling-r4f-20261110-182414"
    flags: dict[str, str] = {}
    flags["HOST_ARCH"] = platform.machine()
    flags["WSL2"] = "PRESENT" if "microsoft" in (Path("/proc/version").read_text(errors="replace").lower() if Path("/proc/version").exists() else "") else "NOT_DETECTED"
    for label, path in (("CANON", canon), ("HIST", hist), ("BUILD", build), ("OUT_EXISTING", out)):
        flags[label] = "PRESENT" if path.is_dir() else "MISSING"
    flags["CANON_PATH"] = str(canon)
    flags["HIST_PATH"] = str(hist)
    flags["BUILD_PATH"] = str(build)
    flags["OUT_PATH"] = str(out)
    for tool in ("git", "python3", "clang-19", "clang", "llvm-objdump", "file", "sha256sum", "ld"):
        flags[f"TOOL_{tool.replace('-', '_')}"] = "PRESENT" if shutil.which(tool) else "MISSING"
    for label, path in (("CANON", canon), ("HIST", hist)):
        if not path.is_dir() or not shutil.which("git"):
            flags[f"{label}_HEAD"] = "NOT_AVAILABLE"
            flags[f"{label}_CHANGED_TRACKED"] = "NOT_AVAILABLE"
            continue
        ok, sha = probe_git(path, "rev-parse", "--verify", "HEAD")
        flags[f"{label}_HEAD"] = sha[:12] if ok else "NOT_AVAILABLE"
        ok, changes = probe_git(path, "status", "--porcelain", "--untracked-files=no")
        flags[f"{label}_CHANGED_TRACKED"] = str(len(changes.splitlines())) if ok and changes else ("0" if ok else "NOT_AVAILABLE")
    private = build / "private-install"
    for name, rel in (("DYLD", "libexec/darling/usr/lib/dyld"),
                      ("MLDR32", "libexec/darling/usr/libexec/darling/mldr32"),
                      ("LIBSYSTEM_FAT", "libexec/darling/usr/lib/libSystem.B.dylib"),
                      ("KERNEL_I386", "libexec/darling/usr/lib/system/libsystem_kernel.dylib")):
        flags[f"PRIVATE_{name}"] = "PRESENT" if (private / rel).is_file() else "MISSING_OR_OTHER_LAYOUT"
    found = False
    for path in xnu_candidates(canon, hist):
        ok, sha = probe_git(path, "rev-parse", f"{XNU_REV}^{{commit}}")
        if ok and sha == XNU_REV:
            flags["PINNED_XNU_OBJECTS"] = "PRESENT"
            flags["PINNED_XNU_PATH"] = str(path)
            found = True
            break
    if not found:
        flags["PINNED_XNU_OBJECTS"] = "NOT_FOUND_IN_KNOWN_PATHS"
    flags["SAFE_SCOPE"] = "READ_ONLY_NO_NETWORK_NO_INSTALL_NO_DELETE"
    return flags


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home(), help="home directory for inspection; no writes")
    args = parser.parse_args()
    report = inventory(args.home)
    for k, v in report.items():
        print(f"R6_10400_{k}={v}")
    ready = all(report[k] == "PRESENT" for k in ("CANON", "HIST", "BUILD", "OUT_EXISTING"))
    print("R6_10400_PREFLIGHT=" + ("PASS_LAYOUT" if ready else "PARTIAL_LAYOUT"))
    print("R6_10400_PINNED_SOURCE_REPLAY=" + ("READY" if report["PINNED_XNU_OBJECTS"] == "PRESENT" else "BLOCKED_SOURCE_NOT_LOCATED"))
    return 0  # Missing prerequisites are reported, never concealed or treated as a guest PASS.


if __name__ == "__main__":
    sys.exit(main())
