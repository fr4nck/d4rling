#!/usr/bin/env python3
"""Host-only SoundHack 0.896 startup gate witness against real D4rling Gestalt.cpp.

No vendor binary, SDK, guest, display, user installation or audio. GPL-3.0-or-later.
The source function is extracted verbatim and compiled with test-only selectors,
sysctl and status definitions. It never changes the source or project build.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

MAX_SOURCE = 1 << 20
PINNED_BLOB = "dffdd4cb26c7f191c6e2b5fc97298c79a8d75dff"


class InvalidSource(ValueError):
    pass


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def extract(source: str) -> str:
    """Extract one function using braces, rejecting absent/ambiguous declarations."""
    pat = re.compile(r"\bOSStatus\s+Gestalt\s*\(\s*uint32_t\s+type\s*,\s*int\s*\*\s*value\s*\)\s*\{")
    hits = list(pat.finditer(source))
    if len(hits) != 1:
        raise InvalidSource("expected exactly one Gestalt(uint32_t,int*) definition")
    begin = hits[0].start()
    at = hits[0].end() - 1
    depth = 0
    for index in range(at, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[begin:index + 1]
    raise InvalidSource("unterminated Gestalt definition")


HARNESS_PRELUDE = r'''
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstddef>
using OSStatus = int;
static constexpr int unimpErr = -4;
static constexpr uint32_t gestaltCarbonVersion = 0x63626f6eu; // 'cbon'
static constexpr uint32_t gestaltSystemVersion = 0x73797376u; // 'sysv'
static constexpr uint32_t gestaltSystemVersionMajor = 0x73797331u;
static constexpr uint32_t gestaltSystemVersionMinor = 0x73797332u;
static constexpr uint32_t gestaltSystemVersionPatch = 0x73797333u;
static constexpr uint32_t gestaltSysArchitecture = 0x73797361u; // 'sysa'
static constexpr int gestaltPowerPC = 2;
static constexpr int gestaltIntel = 10;
static constexpr int CTL_KERN = 1;
static constexpr int KERN_OSRELEASE = 2;
static int sysctl(const int*, unsigned, void* buf, size_t* out_size, const void*, size_t) {
    constexpr const char* mock = "20.4.0";
    if (*out_size < std::strlen(mock) + 1) return -1;
    std::memcpy(buf, mock, std::strlen(mock) + 1);
    *out_size = std::strlen(mock) + 1;
    return 0;
}
'''
HARNESS_MAIN = r'''
int main() {
    int carbonValue = 777;
    int carbonError = Gestalt(gestaltCarbonVersion, &carbonValue);
    int systemValue = 777;
    int systemError = Gestalt(gestaltSystemVersion, &systemValue);
    int archValue = 777;
    int archError = Gestalt(gestaltSysArchitecture, &archValue);
    std::printf("%d %d %d %d %d %d\n", carbonError, carbonValue,
                systemError, systemValue, archError, archValue);
    return 0;
}
'''


def run_probe(source: Path, compiler: str, expected_blob: str | None = None) -> tuple[int, dict]:
    try:
        with source.open("rb") as f:
            data = f.read(MAX_SOURCE + 1)
        if len(data) > MAX_SOURCE:
            raise InvalidSource("source exceeds bound")
        blob = git_blob(data)
        if expected_blob and blob != expected_blob:
            raise InvalidSource(f"source blob mismatch: {blob} != {expected_blob}")
        function = extract(data.decode("utf-8"))
        cc = shutil.which(compiler)
        if cc is None:
            raise InvalidSource(f"missing host C++ compiler: {compiler}")
        with tempfile.TemporaryDirectory(prefix="d4-sh05-") as folder:
            src = Path(folder) / "gate.cpp"
            output = Path(folder) / "gate"
            src.write_text(HARNESS_PRELUDE + function + "\n" + HARNESS_MAIN, encoding="utf-8")
            built = subprocess.run([cc, "-std=c++17", "-O0", "-Wall", "-Wextra", "-Wno-implicit-fallthrough", str(src), "-o", str(output)],
                                   capture_output=True, text=True, timeout=15, check=False)
            if built.returncode != 0:
                raise InvalidSource("host C++ compile failed: " + built.stderr[:1000])
            ran = subprocess.run([str(output)], capture_output=True, text=True, timeout=5, check=False)
            if ran.returncode != 0 or ran.stderr:
                raise InvalidSource("host C++ probe failed: " + ran.stderr[:400])
        tokens = ran.stdout.strip().split()
        if len(tokens) != 6:
            raise InvalidSource("expected six host probe fields")
        carbon_err, carbon_val, system_err, system_val, arch_err, arch_val = map(int, tokens)
        # This check mirrors only the *two specific* startup requirements
        # observed in SoundHack's CapabilityCheck(), not application execution.
        carbon_blocks = carbon_err != 0 or carbon_val <= 0x100
        system_blocks = system_err != 0 or system_val < 0x0860
        report = {
            "status": "HOST_STARTUP_GATE_BLOCKED" if carbon_blocks or system_blocks else "HOST_STARTUP_GATE_ELIGIBLE",
            "source_git_blob": blob,
            "source_path": str(source),
            "carbon_selector": {"code": "cbon", "error": carbon_err, "value": carbon_val, "blocks_soundhack": carbon_blocks},
            "system_selector": {"code": "sysv", "error": system_err, "value": system_val,
                                "expected_mock_pre_fallthrough": 0x1440, "blocks_soundhack": system_blocks},
            "architecture_selector": {"code": "sysa", "error": arch_err, "value": arch_val},
            "level": "HOST C++ execution of extracted D4rling Gestalt() with mock sysctl; not guest runtime or audio",
        }
        return (2 if carbon_blocks or system_blocks else 0), report
    except (OSError, UnicodeError, InvalidSource, subprocess.TimeoutExpired) as exc:
        return 3, {"status": "BLOCKED", "error": str(exc)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gestalt-source", type=Path, required=True)
    p.add_argument("--expected-blob", help="optional exact SHA-1 Git blob of expected source")
    p.add_argument("--compiler", default="c++", help="existing host C++ compiler (never installed)")
    args = p.parse_args(argv)
    code, report = run_probe(args.gestalt_source, args.compiler, args.expected_blob)
    print(json.dumps(report, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
