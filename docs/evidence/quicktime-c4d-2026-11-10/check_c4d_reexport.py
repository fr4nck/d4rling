#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Qualify CoreServices -> CarbonCore CMake reexport without a Darling build.

Authentic CMake inputs; framework creation and children are test-only stubs.
No Mach-O link, i386 execution, Apple SDK, installation, or production writes.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CORE = 'src/frameworks/CoreServices/CMakeLists.txt'
CARBON = 'src/frameworks/CoreServices/src/CarbonCore/CMakeLists.txt'
QUICK = 'src/frameworks/QuickTime/CMakeLists.txt'
LD = 'cmake/use_ld64.cmake'
BLOBS = {
    CORE: '3fac3be55879c09a21827c8335073ab36b4fd9b9',
    CARBON: '85f36aa6d5a4e976688dc4cafa70e42c34af02ff',
    QUICK: '5c6d8ddd44341653be1e837133d5473c4d04ef6d',
}
LD_BLOB = '374f4352864aaef6157ca63cd0fac3cb9e653ab2'
START = 'function(reexport reexporter reexportee reexportee_output)'
STOP = 'endfunction(reexport)'


def require(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError(why)


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True,
                          check=False, timeout=30)


def once(raw: str, old: str, new: str) -> str:
    require(raw.count(old) == 1, 'non-unique mutation anchor ' + repr(old[:70]))
    return raw.replace(old, new)


def read_ld(fragment: bool) -> str:
    raw = (ROOT / LD).read_bytes()
    if not fragment:
        require(git_blob(raw) == LD_BLOB, 'use_ld64.cmake blob differs')
    source = raw.decode('utf-8')
    require(source.count(START) == 1 and source.count(STOP) == 1,
            'cannot extract authentic reexport()')
    first = source.index(START)
    last = source.index(STOP, first) + len(STOP)
    body = source[first:last] + '\n'
    expected = (START + '\n'
                '\tadd_dependencies(${reexporter} ${reexportee})\n'
                '\tset_property(TARGET ${reexporter} APPEND_STRING PROPERTY LINK_FLAGS '
                '" -Wl,-reexport_library,${reexportee_output} ")\n'
                + STOP + '\n')
    require(body == expected, 'reexport() function changed')
    if fragment:
        require(source.strip() == body.strip(), 'fragment fixture must contain only reexport()')
    return body


def setup(where: Path, ld_function: str, mutation: str | None) -> None:
    for rel, expected in BLOBS.items():
        raw = (ROOT / rel).read_bytes()
        require(git_blob(raw) == expected, 'changed input blob: ' + rel)
        target = where / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    cs = where / CORE
    cc = where / CARBON
    qt = where / QUICK
    cm = cs.read_text()
    carbon = cc.read_text()
    quick = qt.read_text()
    quick = once(quick, '    DEPENDENCIES\n        system',
                 '    DEPENDENCIES\n        CoreServices\n        system')

    if mutation == 'missing_reexport':
        cm = once(cm, 'reexport(CoreServices CarbonCore ${CarbonCore_BUILD})',
                  '# removed by negative test')
    elif mutation == 'wrong_reexport_path':
        cm = once(cm, 'reexport(CoreServices CarbonCore ${CarbonCore_BUILD})',
                  'reexport(CoreServices CarbonCore ${FSEvents_BUILD})')
    elif mutation == 'wrong_reexport_flag':
        ld_function = once(ld_function, '-Wl,-reexport_library,', '-Wl,-weak_library,')
    elif mutation == 'missing_order_dependency':
        ld_function = once(ld_function, 'add_dependencies(${reexporter} ${reexportee})',
                           '# removed by negative test')
    elif mutation == 'missing_core_link':
        quick = once(quick, '        CoreServices\n', '')
    elif mutation == 'missing_carbon_provider':
        cm = once(cm, '\t\tCarbonCore\n', '')
    elif mutation == 'bad_carbon_parent':
        carbon = once(carbon, '\tPARENT "CoreServices"', '\tPARENT "OtherFramework"')
    elif mutation == 'missing_macmemory':
        carbon = once(carbon, '\tMacMemory.cpp\n', '')
    elif mutation is not None:
        raise RuntimeError('unknown mutation: ' + mutation)

    cs.write_text(cm)
    cc.write_text(carbon)
    qt.write_text(quick)
    (where / LD).parent.mkdir(parents=True, exist_ok=True)
    (where / LD).write_text(ld_function)

    # Every other CoreServices child has its actual name, but contains only a
    # target declaration. The real CarbonCore CMakeLists is evaluated intact.
    children = re.findall(r'^add_subdirectory\(src/([^)]+)\)', cm, re.MULTILINE)
    require(len(children) == 9 and 'CarbonCore' in children,
            'CoreServices children unexpectedly changed')
    for name in children:
        if name == 'CarbonCore':
            continue
        path = where / 'src/frameworks/CoreServices/src' / name / 'CMakeLists.txt'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'add_custom_target({name})\n')

    (where / 'CMakeLists.txt').write_text(r'''cmake_minimum_required(VERSION 3.20)
project(C4DReexport LANGUAGES NONE)
function(remove_sdk_framework name)
endfunction()
function(generate_sdk_framework name)
endfunction()
function(generate_sdk_subframework name)
endfunction()
function(get_path_preframework output)
  set(${output} "${CMAKE_SOURCE_DIR}/sdk" PARENT_SCOPE)
endfunction()
function(append_path_sdk_subframework in_path output child)
  set(${output} "${in_path}/${child}" PARENT_SCOPE)
endfunction()
function(add_framework name)
  cmake_parse_arguments(F "FAT;CURRENT_VERSION" "VERSION;PARENT" "SOURCES;DEPENDENCIES;RESOURCES" ${ARGN})
  add_custom_target(${name})
  set_property(TARGET ${name} PROPERTY C4D_DEPENDENCIES "${F_DEPENDENCIES}")
  set_property(TARGET ${name} PROPERTY C4D_SOURCES "${F_SOURCES}")
  set_property(TARGET ${name} PROPERTY C4D_PARENT "${F_PARENT}")
endfunction()
add_custom_target(CFNetwork)
add_custom_target(CoreFoundation)
include("${CMAKE_SOURCE_DIR}/cmake/use_ld64.cmake")
add_subdirectory(src/frameworks/CoreServices)
add_subdirectory(src/frameworks/QuickTime)
get_target_property(deps CoreServices MANUALLY_ADDED_DEPENDENCIES)
list(FIND deps "CarbonCore" dep_index)
if(dep_index EQUAL -1)
  message(FATAL_ERROR "C4D_NO_CARBON_BUILD_ORDER")
endif()
get_target_property(flags CoreServices LINK_FLAGS)
set(expected "${CMAKE_CURRENT_BINARY_DIR}/src/frameworks/CoreServices/src/CarbonCore/CarbonCore")
string(FIND "${flags}" "-Wl,-reexport_library,${expected} " flag_index)
if(flag_index EQUAL -1)
  message(FATAL_ERROR "C4D_CARBON_REEXPORT_PATH_OR_FLAG_WRONG")
endif()
string(REGEX MATCHALL "-Wl,-reexport_library," reexports "${flags}")
list(LENGTH reexports how_many)
if(NOT how_many EQUAL 11)
  message(FATAL_ERROR "C4D_REEXPORT_COUNT_WRONG:${how_many}")
endif()
get_target_property(cs_links CoreServices C4D_DEPENDENCIES)
list(FIND cs_links "CarbonCore" c_idx)
if(c_idx EQUAL -1)
  message(FATAL_ERROR "C4D_CARBON_NOT_LINKED_BY_CORESERVICES")
endif()
get_target_property(qt_links QuickTime C4D_DEPENDENCIES)
if(NOT "${qt_links}" STREQUAL "CoreServices;system")
  message(FATAL_ERROR "C4D_QUICKTIME_LINKS_WRONG:${qt_links}")
endif()
get_target_property(cc_parent CarbonCore C4D_PARENT)
if(NOT "${cc_parent}" STREQUAL "CoreServices")
  message(FATAL_ERROR "C4D_CARBON_PARENT_WRONG:${cc_parent}")
endif()
get_target_property(cc_src CarbonCore C4D_SOURCES)
list(FIND cc_src "MacMemory.cpp" mem_index)
if(mem_index EQUAL -1)
  message(FATAL_ERROR "C4D_MACMEMORY_NOT_BUILT")
endif()
message(STATUS "C4D_REEXPORT_GRAPH_PASS")
''')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fragment-fixture', action='store_true',
                    help='test-only: use an exact reexport function fragment, not full use_ld64.cmake')
    options = ap.parse_args()
    require(shutil.which('cmake') is not None, 'cmake unavailable')
    source = read_ld(options.fragment_fixture)
    with tempfile.TemporaryDirectory(prefix='d4rling-c4d-reexport-') as temp:
        root = Path(temp)
        names = [None, 'missing_reexport', 'wrong_reexport_path',
                 'wrong_reexport_flag', 'missing_order_dependency',
                 'missing_core_link', 'missing_carbon_provider',
                 'bad_carbon_parent', 'missing_macmemory']
        for index, mutation in enumerate(names):
            fixture = root / f'case{index:02d}'
            fixture.mkdir()
            setup(fixture, source, mutation)
            result = run(['cmake', '-S', str(fixture), '-B', str(fixture / 'build')], fixture)
            if mutation is None:
                require(result.returncode == 0 and 'C4D_REEXPORT_GRAPH_PASS' in result.stdout,
                        'positive failed: ' + result.stdout[-1000:] + result.stderr[-1000:])
                print('PASS POSITIVE: CoreServices -> CarbonCore reexport and QuickTime graph')
            else:
                require(result.returncode != 0 and 'C4D_' in result.stderr + result.stdout,
                        'mutant survived or failed for wrong reason: ' + mutation + ' ' +
                        result.stdout[-700:] + result.stderr[-700:])
                print(f'PASS NEGATIVE {index}/8: {mutation}')
    print('C4D_REEXPORT_PASS: 1 positive; 8 negative mutations detected; '
          'FULL_DARLING_NOT_BUILT; MACHO_I386_NOT_EXECUTED; PRODUCTION_NO_GO')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print('FAIL: ' + str(exc), file=sys.stderr)
        sys.exit(1)
