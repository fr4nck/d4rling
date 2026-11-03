#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""D4RLING dyld i386: pinned @loader_path / @rpath comparison.

No network, installs, source edits, Ninja/CMake, or existing prefix writes.
Default: build and inspect in a NEW private directory only.
Optional --run: invoke the already committed namespace-guarded guest runner.
Requires the reproduction/ directory from the merged project-recovery kit.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
MARKER = "D4RLING-CARBON-EVENT-I386-OK"
LIBRARY = "libD4CarbonEvents.dylib"
BUILDER_BLOB = "90e5001a37aa27105ed5bd2c9ff4e74f47771787"
RUNNER_BLOB = "7b654180dae2184433b799e81ec06ff60146a180"
FIXTURE_BLOB = "67857751a333cbf1bb0f8ff1a8fd3ea101b239ab"
ATOMIC_BLOB = "eec3c84883b37ffbf6f976b4f92d37ccca762bff"


def stop(message):
    raise SystemExit("BLOCKED: " + message)


def git_blob(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\x00" + data).hexdigest()


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def check_tool(name):
    p = shutil.which(name)
    if not p:
        stop("tool not installed (no installation attempted): " + name)
    return p


def command(args, logfile, timeout=180):
    with logfile.open("w", encoding="utf-8") as log:
        log.write("ARGV=" + json.dumps([str(a) for a in args]) + "\n")
        log.flush()
        try:
            run = subprocess.run(
                [str(a) for a in args], stdout=log, stderr=subprocess.STDOUT,
                timeout=timeout, check=False
            )
        except subprocess.TimeoutExpired:
            stop("command timed out: " + str(logfile))
    if run.returncode:
        stop("command failed (exit " + str(run.returncode) + "): " + str(logfile))


def inspect(tool, path, mode, expected, logfile):
    result = subprocess.run(
        [tool, "-arch", "i386", mode, str(path)],
        text=True, capture_output=True, timeout=30
    )
    logfile.write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode or expected not in result.stdout:
        stop("Mach-O " + mode + " contract not met: " + str(logfile))
    return result.stdout


def verify_program(tool, lipo, folder, reference, has_rpath, logdir):
    lib = folder / LIBRARY
    exe = folder / "carbon-dynamic-i386"
    for path in (lib, exe):
        if path.is_symlink() or not path.is_file():
            stop("missing or symlinked candidate: " + str(path))
        arch = subprocess.run(
            [lipo, "-archs", str(path)],
            text=True, capture_output=True, timeout=20
        )
        if arch.returncode or "i386" not in arch.stdout.split():
            stop("missing i386 Mach-O slice: " + str(path))
    inspect(tool, lib, "-L", reference, logdir / (folder.name + "-dylib-L.log"))
    inspect(tool, exe, "-L", reference, logdir / (folder.name + "-exec-L.log"))
    cmds = inspect(tool, exe, "-l", "LC_LOAD_DYLIB", logdir / (folder.name + "-exec-loads.log"))
    chunks = re.split(r"(?=Load command \d+\s*\n)", cmds)
    rpaths = []
    for chunk in chunks:
        if re.search(r"^\s*cmd\s+LC_RPATH\s*$", chunk, flags=re.M):
            match = re.search(r"^\s*path\s+(\S+)", chunk, flags=re.M)
            if match:
                rpaths.append(match.group(1))
    if has_rpath and rpaths != ["@executable_path"]:
        stop("expected exactly one @executable_path LC_RPATH in " + folder.name
             + " (observed: " + repr(rpaths) + ")")
    if not has_rpath and rpaths:
        stop("unexpected LC_RPATH in " + folder.name + ": " + repr(rpaths))
    print("STATIC_" + folder.name.upper() + "=PASS", flush=True)


def run_guest(runner, installation, program, mode, timeout_seconds, logfile):
    p = subprocess.run(
        ["bash", str(runner), str(installation), str(program), mode,
         str(timeout_seconds)],
        text=True, capture_output=True, timeout=timeout_seconds + 20
    )
    logfile.write_text(p.stdout + p.stderr, encoding="utf-8")
    match = re.search(r"^REPORT=(\S+)$", p.stdout, flags=re.M)
    if not match:
        stop("guest namespace wrapper returned no report: " + str(logfile))
    report = Path(match.group(1))
    # Runner creates a fresh separate private /tmp directory.
    guest_out = (report / "stdout.log").read_text(errors="replace")
    guest_err = (report / "stderr.log").read_text(errors="replace")
    (logfile.parent / (logfile.stem + "-guest.stdout")).write_text(guest_out)
    (logfile.parent / (logfile.stem + "-guest.stderr")).write_text(guest_err)
    marker = MARKER in guest_out.splitlines()
    return {"exit": p.returncode, "marker": marker, "stderr": guest_err,
            "report": str(report)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "build", "installation", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--run", action="store_true",
                        help="Explicit permission to invoke the private guest runner")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    if os.geteuid() == 0:
        stop("run as unprivileged Debian user, never sudo")
    if "microsoft" not in platform.release().lower():
        stop("this qualification expects Debian WSL2")
    distro = Path("/etc/os-release").read_text()
    if not re.search(r"^ID=debian$", distro, flags=re.M) or not re.search(
        r'^VERSION_ID="?13"?$', distro, flags=re.M
    ):
        stop("this qualification expects Debian 13")

    root = Path("/home/Deniel").resolve()
    source, build, inst, output = (
        args.source.resolve(), args.build.resolve(),
        args.installation.resolve(), args.output.resolve()
    )
    if output.exists() or output.is_symlink():
        stop("REFUSE_EXISTING_OUTPUT: " + str(output))
    if root not in output.parents:
        stop("output must be a new private child directory of /home/Deniel")
    for name, parent in (("source", source), ("build", build), ("installation", inst)):
        if not parent.is_dir():
            stop(name + " directory missing: " + str(parent))
        if output == parent or parent in output.parents:
            stop("output overlaps protected " + name + " directory")
    if inst == Path("/usr/local") or inst == Path("/opt") or (
        Path("/usr") in inst.parents or Path("/opt") in inst.parents
    ):
        stop("no global Darling installation is allowed")
    if not 5 <= args.timeout <= 40:
        stop("timeout must be between 5 and 40 seconds")

    clang = check_tool("clang-19")
    lipo = check_tool("llvm-lipo-19")
    otool = check_tool("llvm-otool-19")
    check_tool("bash")
    if args.run:
        for tool in ("unshare", "timeout", "mount", "realpath", "readlink"):
            check_tool(tool)

    fixed = {
        HERE / "build-carbon-probe.py": BUILDER_BLOB,
        HERE / "run-guest.sh": RUNNER_BLOB,
        HERE / "fixtures/carbon-event.c": FIXTURE_BLOB,
        HERE / "fixtures/atomic-bridge.h": ATOMIC_BLOB,
    }
    for path, expected in fixed.items():
        if not path.is_file() or git_blob(path) != expected:
            stop("pinned reproduction input mismatch: " + str(path))

    private_root = inst / "libexec/darling"
    linker = build / "src/external/cctools-port/cctools/ld64/src/x86_64-apple-darwin20-ld"
    cf = private_root / "System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
    libsystem = private_root / "usr/lib/libSystem.B.dylib"
    carbon = source / "src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c"
    native = [
        inst / "bin/darling",
        inst / "bin/darlingserver",
        private_root / "usr/libexec/darling/mldr",
        private_root / "usr/libexec/darling/mldr32",
    ]
    inputs = [linker, cf, libsystem, carbon] + native
    for path in inputs:
        if not path.is_file():
            stop("missing pinned local input: " + str(path))
    for path in (cf, libsystem):
        archs = subprocess.run([lipo, "-archs", str(path)],
                               capture_output=True, text=True, timeout=20)
        if archs.returncode or "i386" not in archs.stdout.split():
            stop("installed reference is not i386-capable: " + str(path))
    if args.run:
        # Do not accidentally launch a global server/loader: Darling embeds
        # absolute helper paths, unlike a simple relocatable ELF application.
        server_path = str(native[1]).encode()
        loader_path = str(native[2]).encode()
        if server_path not in native[0].read_bytes():
            stop("cannot prove private darlingserver path embedded in darling")
        if loader_path not in native[1].read_bytes():
            stop("cannot prove private mldr path embedded in darlingserver")

    before = {str(path): sha256(path) for path in inputs}
    output.mkdir(mode=0o700)
    results = {"schema": "d4rling.dyld-rpath-qualification.v1",
               "runtime_requested": args.run, "runtime_executed": False,
               "run_cases": {}, "protected_inputs_sha256": before}
    try:
        print("WORKDIR=" + str(output), flush=True)
        base = output / "loaderpath"
        command([sys.executable, HERE / "build-carbon-probe.py",
                 "--source", source, "--build", build,
                 "--installation", inst, "--output", base],
                output / "build-loaderpath.log")

        common = [linker, "-arch", "i386", "-macosx_version_min", "10.9",
                  "-syslibroot", private_root, "-L", private_root / "usr/lib",
                  "-F", private_root / "System/Library/Frameworks"]
        core_obj = base / "CarbonEventsCore.o"
        probe_obj = base / "carbon-event.o"
        cases = {
            "rpath": ("@rpath/" + LIBRARY, True),
            "rpath_no_lc": ("@rpath/" + LIBRARY, False),
        }
        for label, (identity, add_rpath) in cases.items():
            folder = output / label
            folder.mkdir(mode=0o700)
            dylib = folder / LIBRARY
            executable = folder / "carbon-dynamic-i386"
            command([*common, "-dylib", "-install_name", identity,
                     "-compatibility_version", "1.0.0",
                     "-current_version", "1.0.0",
                     "-o", dylib, core_obj, cf, libsystem],
                    output / ("link-" + label + "-dylib.log"))
            link_args = [*common, "-pie", "-e", "_main"]
            if add_rpath:
                link_args.extend(["-rpath", "@executable_path"])
            command([*link_args, "-o", executable, probe_obj, dylib, libsystem],
                    output / ("link-" + label + "-exe.log"))
            executable.chmod(0o700)
            dylib.chmod(0o700)

        verify_program(otool, lipo, base, "@loader_path/" + LIBRARY, False, output)
        verify_program(otool, lipo, output / "rpath", "@rpath/" + LIBRARY, True, output)
        verify_program(otool, lipo, output / "rpath_no_lc", "@rpath/" + LIBRARY, False, output)
        results["static"] = "PASS"
        print("DYLD_RPATH_STATIC=PASS", flush=True)

        if args.run:
            runner = HERE / "run-guest.sh"
            ordered = [
                ("loader_normal", base, "normal", True),
                ("loader_bypass", base, "bypass", True),
                ("rpath_normal", output / "rpath", "normal", True),
                ("rpath_bypass", output / "rpath", "bypass", True),
                ("rpath_no_lc_negative", output / "rpath_no_lc", "normal", False),
            ]
            for label, folder, mode, must_succeed in ordered:
                results["runtime_executed"] = True
                observed = run_guest(runner, inst, folder / "carbon-dynamic-i386",
                                     mode, args.timeout, output / (label + ".log"))
                results["run_cases"][label] = {
                    "exit": observed["exit"], "marker": observed["marker"],
                    "report": observed["report"]
                }
                if must_succeed:
                    passed = observed["exit"] == 0 and observed["marker"]
                else:
                    passed = (observed["exit"] == 1 and not observed["marker"]
                              and "@rpath/" + LIBRARY in observed["stderr"]
                              and "Library not loaded" in observed["stderr"])
                results["run_cases"][label]["passed"] = passed
                print(label.upper() + ("=PASS" if passed else "=FAIL"), flush=True)
                # Baseline failed => environment invalid, not an @rpath result.
                if not passed:
                    if label.startswith("loader_"):
                        results["runtime_status"] = "BLOCKED_BASELINE"
                    elif label.startswith("rpath_"):
                        results["runtime_status"] = "FAIL_RPATH_DIAGNOSTIC"
                    break
            else:
                results["runtime_status"] = "PASS_POSITIVE_AND_NEGATIVE"
                print("DYLD_RPATH_RUNTIME=PASS", flush=True)
        else:
            results["runtime_status"] = "NOT_EXECUTED_BUILD_ONLY"
            print("DARLING_GUEST_RUNTIME=NOT_EXECUTED", flush=True)
    finally:
        after = {str(path): sha256(path) for path in inputs}
        results["protected_inputs_unchanged"] = before == after
        (output / "result.json").write_text(json.dumps(results, indent=2) + "\n",
                                             encoding="utf-8")
        print("INPUT_INTEGRITY=" + ("PASS" if before == after else "FAIL"), flush=True)
        print("REPORT=" + str(output / "result.json"), flush=True)
        if before != after:
            stop("protected input changed during experiment")
    if results["runtime_status"].startswith(("BLOCKED", "FAIL")):
        raise SystemExit(5)


if __name__ == "__main__":
    main()
