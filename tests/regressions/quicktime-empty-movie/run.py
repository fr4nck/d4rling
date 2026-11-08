#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile and run the real QuickTime empty-movie subset with MSVC already installed."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "baseline", "mac-types", "out", "vcvars"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    source, baseline, mac = args.source.resolve(), args.baseline.resolve(), args.mac_types.resolve()
    out, vcvars = args.out.resolve(), args.vcvars.resolve()
    here = Path(__file__).resolve().parent
    if not (mac / "MacTypes.h").is_file() or not vcvars.is_file():
        p.error("existing MacTypes.h/Visual Studio environment script required")
    out.mkdir(parents=True, exist_ok=False)
    # Process-local environment only; no installation or persistent changes.
    setup = subprocess.run(
        [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", "call",
         str(vcvars), ">nul", "&&", "set"],
        capture_output=True, timeout=30)
    if setup.returncode:
        raise RuntimeError("Visual Studio environment setup failed")
    env = dict(os.environ)
    for line in setup.stdout.decode("utf-8", "replace").splitlines():
        key, sep, value = line.partition("=")
        if sep and key:
            env[key.upper()] = value
    compiler = shutil.which("cl.exe", path=env.get("PATH"))
    if not compiler:
        raise RuntimeError("MSVC compiler not found in the configured environment")
    results = {}
    def run(name, command):
        if command[0] == "cl.exe":
            command[0] = compiler
        r = subprocess.run([str(x) for x in command], cwd=out, env=env,
                           capture_output=True, timeout=60)
        (out / (name + ".txt")).write_bytes(r.stdout + r.stderr)
        results[name] = {"exit": r.returncode}
        return r.returncode
    common = ["cl.exe", "/nologo", "/W4", "/WX", "/wd4505",
              "/D_CRT_SECURE_NO_WARNINGS"]
    def includes(root):
        return ["/I" + str(root / "src/frameworks/QuickTime/include"),
                "/I" + str(here / "host"), "/I" + str(mac)]
    src = "src/frameworks/QuickTime/src/QuickTime.c"
    # Before: original declaration rejected by typed C++ contracts.
    before_contract = run("before-contract", common + ["/std:c++17", "/EHsc", "/c"] +
        includes(baseline) + [here / "contracts.cpp", "/Fobefore-contract.obj"])
    # Before: NewMovie called with its ORIGINAL declaration, so no ABI-mismatched call.
    before_build = run("before-source", common + ["/std:c11", "/c",
        "/FI" + str(here / "host/baseline-adapter.h")] +
        includes(baseline) + [baseline / src, "/Fobefore.obj"])
    before_test_build = run("before-test", common + ["/std:c11", "/c"] +
        includes(baseline) + [here / "baseline.c", "/Fobefore-test.obj"])
    before_link = run("before-link", ["cl.exe", "/nologo", "before.obj",
        "before-test.obj", "/Febefore.exe", "/link", "/INCREMENTAL:NO"]) if not (before_build or before_test_build) else -1
    before_run = run("before-run", [out / "before.exe"]) if before_link == 0 else -1
    builds = [
        run("after-source", common + ["/std:c11", "/c",
            "/FI" + str(here / "host/production-adapter.h")] +
            includes(source) + [source / src, "/Foafter.obj"]),
        run("after-test", common + ["/std:c11", "/c"] +
            includes(source) + [here / "lifecycle.c", "/Fotest.obj"]),
        run("after-contract", common + ["/std:c++17", "/EHsc", "/c"] +
            includes(source) + [here / "contracts.cpp", "/Focontract.obj"])]
    after_link = run("after-link", ["cl.exe", "/nologo", "after.obj", "test.obj",
        "contract.obj", "/Feafter.exe", "/link", "/INCREMENTAL:NO"]) if not any(builds) else -1
    after_run = run("after-run", [out / "after.exe"]) if after_link == 0 else -1
    passed = before_contract != 0 and before_run == 1 and after_run == 0
    evidence = {"status": "PASS" if passed else "FAIL", "results": results,
                "scope": "Windows x64 host, real QuickTime.c/QuickTime.h and real MacTypes.h",
                "substitutions": ["ConditionalMacros.h", "Availability.h", "sys/types.h",
                    "constructor attribute omitted for STUB_VERBOSE only",
                    "malloc/free wrapped for allocation counting/failure injection"],
                "runtime_i386": "NOT TESTED"}
    (out / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence))
    if (out / "after-run.txt").is_file():
        print((out / "after-run.txt").read_text(errors="replace").strip())
    if not passed:
        for name in ("after-source", "after-test", "after-contract", "after-link"):
            if results.get(name, {}).get("exit"):
                print(name + ":\n" + (out / (name + ".txt")).read_text(errors="replace")[-6000:])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
