#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""C4-D: verify an archived CMake-only proposal, without touching production."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PATCH = HERE / "c4d-cmake-proposal.patch"
SOURCES = {
    "cmake/darling_parse_components.cmake": "7605a01569f6634d0cf4c0a948c3c4acd893dde9",
    "src/frameworks/CMakeLists.txt": "ea2f9c07e83e2520de3fbce792ef7c429d11dc5a",
    "src/frameworks/QuickTime/CMakeLists.txt": "5c6d8ddd44341653be1e837133d5473c4d04ef6d",
}
PATCH_SHA256 = "1f6caa834c45f43228602d4f76adaa177a92d6a5fa700aab4e15a3a149eed434"


def require(test: bool, name: str) -> None:
    if not test:
        raise RuntimeError("FAIL: " + name)


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False, timeout=15)


def cmake_check(script: Path, harness: Path, profile: str, seed: bool = False) -> bool:
    args = ["cmake", "-DSCRIPT=" + str(script), "-DPROFILE=" + profile]
    if seed:
        args.append("-DSEED_QUICKTIME=ON")
    return run(args + ["-P", str(harness)], harness.parent).returncode == 0


def main() -> None:
    require(PATCH.is_file(), "proposal missing")
    require(hashlib.sha256(PATCH.read_bytes()).hexdigest() == PATCH_SHA256, "proposal SHA256")
    for relative, expected in SOURCES.items():
        raw = (ROOT / relative).read_bytes()
        require(git_blob_sha(raw) == expected, "base blob " + relative)
    print("PASS: 3/3 source blobs and proposal SHA256")

    cs = (ROOT / "src/frameworks/CoreServices/CMakeLists.txt").read_text()
    cc = (ROOT / "src/frameworks/CoreServices/src/CarbonCore/CMakeLists.txt").read_text()
    macros = (ROOT / "cmake/darling_framework.cmake").read_text()
    ld = (ROOT / "cmake/use_ld64.cmake").read_text()
    framework_root = (ROOT / "src/frameworks/CMakeLists.txt").read_text()
    src_root = (ROOT / "src/CMakeLists.txt").read_text()
    require("reexport(CoreServices CarbonCore ${CarbonCore_BUILD})" in cs, "CarbonCore reexport")
    require("-reexport_library" in ld and "add_dependencies(${reexporter} ${reexportee})" in ld, "reexport macro")
    require("target_link_libraries(${my_name} PRIVATE ${FRAMEWORK_DEPENDENCIES})" in macros, "framework link macro")
    require("MacMemory.cpp" in cc and "PARENT \"CoreServices\"" in cc, "CarbonCore source/parent")
    require("if (COMPONENT_cli OR COMPONENT_dev_gui_common)" in framework_root and
            "add_subdirectory(CoreServices)" in framework_root and
            "add_subdirectory(external/foundation)" in src_root, "CoreServices/Foundation selectors")
    print("PASS: 5/5 dependency/reexport invariants")

    with tempfile.TemporaryDirectory(prefix="d4rling-c4d-") as temp:
        tmp = Path(temp)
        for relative in SOURCES:
            target = tmp / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        require(run(["git", "apply", "--check", str(PATCH)], tmp).returncode == 0, "git apply --check")
        require(run(["git", "apply", str(PATCH)], tmp).returncode == 0, "scratch patch apply")
        print("PASS: git apply --check and scratch apply; no repository modifications")

        parser = tmp / "cmake/darling_parse_components.cmake"
        modified = parser.read_text()
        original = (ROOT / "cmake/darling_parse_components.cmake").read_text()
        fw = (tmp / "src/frameworks/CMakeLists.txt").read_text()
        qt = (tmp / "src/frameworks/QuickTime/CMakeLists.txt").read_text()
        positive = [
            'if (COMPONENT_gui_stubs OR COMPONENT_quicktime)' in fw,
            fw.count('add_subdirectory(QuickTime)') == 1,
            '        CoreServices\n        system' in qt,
            'set(COMPONENT_DEPS cli PARENT_SCOPE)' in modified,
            'gui_stubs quicktime jsc webkit' in modified,
        ]
        require(all(positive), "CMake proposal static invariants")
        print("PASS: 5/5 proposal static invariants")

        def contract(i: int, value: str) -> bool:
            if i == 0:
                return '        CoreServices\n        system' in value
            if i == 1:
                return 'if (COMPONENT_gui_stubs OR COMPONENT_quicktime)' in value
            return value.count('add_subdirectory(QuickTime)') == 1

        mutants = [
            qt.replace('        CoreServices\n', ''),
            fw.replace('if (COMPONENT_gui_stubs OR COMPONENT_quicktime)', 'if (COMPONENT_gui_stubs)'),
            fw.replace('    add_subdirectory(QuickTime)', '    add_subdirectory(QuickTime)\n    add_subdirectory(QuickTime)'),
        ]
        require(all(not contract(i, value) for i, value in enumerate(mutants)), "3 static mutants")
        print("PASS: 3/3 static mutants rejected")

        harness = tmp / 'harness.cmake'
        harness.write_text('''include("${SCRIPT}")
if(DEFINED SEED_QUICKTIME)
    set(COMPONENT_quicktime ON)
endif()
darling_parse_components("${PROFILE}")
if(PROFILE STREQUAL "quicktime")
    if(NOT COMPONENT_quicktime OR NOT COMPONENT_cli OR NOT COMPONENT_system OR NOT COMPONENT_core)
        message(FATAL_ERROR "missing dependency")
    endif()
    if(COMPONENT_gui OR COMPONENT_gui_stubs OR COMPONENT_dev_gui_common OR COMPONENT_iokitd)
        message(FATAL_ERROR "unwanted GUI components")
    endif()
elseif(PROFILE STREQUAL "gui_stubs")
    if(NOT COMPONENT_gui_stubs OR NOT COMPONENT_gui OR NOT COMPONENT_dev_gui_common OR NOT COMPONENT_system OR COMPONENT_quicktime)
        message(FATAL_ERROR "legacy gui_stubs regression")
    endif()
elseif(PROFILE STREQUAL "cli")
    if(NOT COMPONENT_cli OR NOT COMPONENT_system OR NOT COMPONENT_core OR COMPONENT_quicktime)
        message(FATAL_ERROR "legacy cli regression or flag leak")
    endif()
elseif(PROFILE STREQUAL "core")
    if(NOT COMPONENT_core OR COMPONENT_cli OR COMPONENT_quicktime OR COMPONENT_gui)
        message(FATAL_ERROR "core regression")
    endif()
else()
    message(FATAL_ERROR "invalid profile")
endif()
''')
        original_file = tmp / 'parser_original.cmake'
        original_file.write_text(original)
        gui_mutant = tmp / 'parser_gui_mutant.cmake'
        gui_mutant.write_text(modified.replace(
            'elseif ("${COMPONENT}" STREQUAL "quicktime")\n\t\tset(COMPONENT_DEPS cli PARENT_SCOPE)',
            'elseif ("${COMPONENT}" STREQUAL "quicktime")\n\t\tset(COMPONENT_DEPS gui_stubs PARENT_SCOPE)'))
        flag_mutant = tmp / 'parser_flag_mutant.cmake'
        flag_mutant.write_text(modified.replace('gui_stubs quicktime jsc webkit', 'gui_stubs jsc webkit'))
        cases = [
            (parser, 'quicktime', False, True),
            (parser, 'gui_stubs', False, True),
            (parser, 'cli', False, True),
            (parser, 'core', False, True),
            (parser, 'cli', True, True),
            (original_file, 'quicktime', False, False),
            (gui_mutant, 'quicktime', False, False),
            (flag_mutant, 'cli', True, False),
        ]
        detected = sum(cmake_check(p, harness, profile, seed) == expected for p, profile, seed, expected in cases)
        require(detected == len(cases), "CMake script cases")
        print(f"PASS: cmake -P {detected}/{len(cases)} cases (5 positive, 3 negative)")
    print("C4D_STATIC_PASS; I386_NOT_EXECUTED; PRODUCTION_NO_GO")


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
