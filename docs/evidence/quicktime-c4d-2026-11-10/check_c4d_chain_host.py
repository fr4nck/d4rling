#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""C4-D-E2: exercise the three-framework link chain on a synthetic ELF host.

Copies the exact published CMake inputs and evaluates the genuine CoreServices,
CarbonCore and QuickTime CMakeLists. Test-only add_framework and source objects
are substituted for actual Darwin framework construction. Mach-O-only linker
flags are checked and stripped *after* inspection, only for the ELF host.
No guest, SDK, private prefix, production source or installation is changed.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = {
    'src/frameworks/CoreServices/CMakeLists.txt': '3fac3be55879c09a21827c8335073ab36b4fd9b9',
    'src/frameworks/CoreServices/src/CarbonCore/CMakeLists.txt': '85f36aa6d5a4e976688dc4cafa70e42c34af02ff',
    'src/frameworks/QuickTime/CMakeLists.txt': '5c6d8ddd44341653be1e837133d5473c4d04ef6d',
}
LD = 'cmake/use_ld64.cmake'
LD_BLOB = '374f4352864aaef6157ca63cd0fac3cb9e653ab2'
START = 'function(reexport reexporter reexportee reexportee_output)'
STOP = 'endfunction(reexport)'
REEXPORT = '''function(reexport reexporter reexportee reexportee_output)
\tadd_dependencies(${reexporter} ${reexportee})
\tset_property(TARGET ${reexporter} APPEND_STRING PROPERTY LINK_FLAGS " -Wl,-reexport_library,${reexportee_output} ")
endfunction(reexport)
'''


def check(ok: bool, label: str) -> None:
    if not ok:
        raise RuntimeError(label)


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def cmd(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True,
                          timeout=45, check=False)


def change_one(path: Path, old: str, new: str) -> None:
    s = path.read_text()
    check(s.count(old) == 1, 'ambiguous mutation anchor: ' + str(path) + ' ' + repr(old))
    path.write_text(s.replace(old, new))


def provider_source(name: str, bad: str | None) -> str:
    if name == 'CarbonCore':
        if bad == 'broken_carbon_provider':
            return 'int d4rl_wrong_memory(void) { return 42; }\n'
        if bad == 'wrong_runtime_value':
            return 'int d4rl_c4d_memory(void) { return 41; }\n'
        return 'int d4rl_c4d_memory(void) { return 42; }\n'
    if name == 'CoreServices':
        if bad == 'broken_core_provider':
            return 'int d4rl_wrong_services(void) { return 42; }\n'
        return ('extern int d4rl_c4d_memory(void);\n'
                'int d4rl_c4d_services(void) { return d4rl_c4d_memory(); }\n')
    return ('extern int d4rl_c4d_services(void);\n'
            'int d4rl_c4d_quicktime(void) { return d4rl_c4d_services(); }\n')


def load_reexport(fragment: bool) -> str:
    raw = (ROOT / LD).read_bytes()
    if not fragment:
        check(git_blob(raw) == LD_BLOB, 'use_ld64 source blob differs')
    src = raw.decode('utf-8')
    check(src.count(START) == 1 and src.count(STOP) == 1,
          'ambiguous reexport macro')
    excerpt = src[src.index(START):src.index(STOP) + len(STOP)] + '\n'
    check(excerpt == REEXPORT, 'reexport macro differs from pinned source')
    if fragment:
        check(src.strip() == REEXPORT.strip(), 'fragment fixture contains extra code')
    return excerpt


def prepare(where: Path, reexport: str, mutation: str | None) -> None:
    for rel, sha in BASE.items():
        raw = (ROOT / rel).read_bytes()
        check(git_blob(raw) == sha, 'source blob mismatch: ' + rel)
        dest = where / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
    cs = where / 'src/frameworks/CoreServices/CMakeLists.txt'
    qt = where / 'src/frameworks/QuickTime/CMakeLists.txt'
    # Only the separately archived C4-D dependency is modeled: the production
    # QuickTime CMakeLists and C4 source candidate are not changed.
    change_one(qt, '    DEPENDENCIES\n        system',
               '    DEPENDENCIES\n        CoreServices\n        system')
    if mutation == 'missing_quicktime_dependency':
        change_one(qt, '        CoreServices\n', '')
    elif mutation == 'missing_carbon_dependency':
        change_one(cs, '\t\tCarbonCore\n', '')
    elif mutation == 'missing_carbon_reexport':
        change_one(cs, 'reexport(CoreServices CarbonCore ${CarbonCore_BUILD})',
                   '# deliberately removed for negative test')
    elif mutation == 'wrong_carbon_reexport_path':
        change_one(cs, 'reexport(CoreServices CarbonCore ${CarbonCore_BUILD})',
                   'reexport(CoreServices CarbonCore ${AE_BUILD})')
    elif mutation not in {None, 'broken_carbon_provider', 'broken_core_provider',
                          'wrong_runtime_value'}:
        raise RuntimeError('unknown mutation: ' + str(mutation))

    ld = where / 'cmake/reexport_only.cmake'
    ld.parent.mkdir(parents=True, exist_ok=True)
    ld.write_text(reexport)
    for name in ('CarbonCore', 'CoreServices', 'QuickTime'):
        (where / (name + '.c')).write_text(provider_source(name, mutation))
    (where / 'witness.c').write_text('''extern int d4rl_c4d_quicktime(void);
int main(void) { return d4rl_c4d_quicktime() == 42 ? 0 : 7; }
''')
    rootcs = where / 'src/frameworks/CoreServices/src'
    for n in ('AE', 'DictionaryServices', 'FSEvents', 'LaunchServices',
              'Metadata', 'OSServices', 'SearchKit', 'SharedFileList'):
        (rootcs / n).mkdir(parents=True, exist_ok=True)
        (rootcs / n / 'CMakeLists.txt').write_text('# synthetic framework neighbor\n')
    (where / 'CMakeLists.txt').write_text(r'''cmake_minimum_required(VERSION 3.20)
project(C4DChainHost LANGUAGES C)
include("${CMAKE_SOURCE_DIR}/cmake/reexport_only.cmake")
function(remove_sdk_framework name)
endfunction()
function(generate_sdk_framework name)
endfunction()
function(generate_sdk_subframework name)
endfunction()
function(get_path_preframework out)
  set(${out} "${CMAKE_BINARY_DIR}/sdk" PARENT_SCOPE)
endfunction()
function(append_path_sdk_subframework base out child)
  set(${out} "${base}/${child}" PARENT_SCOPE)
endfunction()
# Framework creation is synthetic for the ELF host, NOT Darling add_framework().
function(add_framework name)
  cmake_parse_arguments(F "FAT;CURRENT_VERSION" "VERSION;PARENT" "SOURCES;DEPENDENCIES;RESOURCES" ${ARGN})
  add_library(${name} SHARED "${CMAKE_SOURCE_DIR}/${name}.c")
  set_target_properties(${name} PROPERTIES PREFIX "" SUFFIX "" OUTPUT_NAME "${name}")
  target_link_libraries(${name} PRIVATE ${F_DEPENDENCIES})
  target_link_options(${name} PRIVATE LINKER:--no-undefined)
  set_property(TARGET ${name} PROPERTY C4D_PARENT "${F_PARENT}")
  set_property(TARGET ${name} PROPERTY C4D_SOURCES "${F_SOURCES}")
endfunction()
foreach(name IN ITEMS system CoreFoundation Foundation cxx icucore iconv
 AE CFNetwork DictionaryServices FSEvents LaunchServices Metadata
 OSServices SearchKit SharedFileList)
  add_library(${name} INTERFACE)
endforeach()
add_subdirectory(src/frameworks/CoreServices)
add_subdirectory(src/frameworks/QuickTime)
get_target_property(qt_links QuickTime LINK_LIBRARIES)
if(NOT "${qt_links}" STREQUAL "CoreServices;system")
  message(FATAL_ERROR "C4D_QUICKTIME_LINK_WRONG:${qt_links}")
endif()
get_target_property(cs_links CoreServices LINK_LIBRARIES)
list(FIND cs_links CarbonCore ci)
if(ci EQUAL -1)
  message(FATAL_ERROR "C4D_CARBON_LINK_MISSING")
endif()
get_target_property(flags CoreServices LINK_FLAGS)
set(expected "${CMAKE_BINARY_DIR}/src/frameworks/CoreServices/src/CarbonCore/CarbonCore")
string(FIND "${flags}" "-Wl,-reexport_library,${expected} " rp)
if(rp EQUAL -1)
  message(FATAL_ERROR "C4D_CARBON_REEXPORT_PATH_WRONG")
endif()
string(REGEX MATCHALL "-Wl,-reexport_library," entries "${flags}")
list(LENGTH entries count)
if(NOT count EQUAL 11)
  message(FATAL_ERROR "C4D_REEXPORT_COUNT_WRONG:${count}")
endif()
get_target_property(manual CoreServices MANUALLY_ADDED_DEPENDENCIES)
list(FIND manual CarbonCore dep)
if(dep EQUAL -1)
  message(FATAL_ERROR "C4D_REEXPORT_ORDER_MISSING")
endif()
get_target_property(cc_parent CarbonCore C4D_PARENT)
if(NOT "${cc_parent}" STREQUAL "CoreServices")
  message(FATAL_ERROR "C4D_CARBON_PARENT_WRONG")
endif()
get_target_property(cc_sources CarbonCore C4D_SOURCES)
list(FIND cc_sources "MacMemory.cpp" src_index)
if(src_index EQUAL -1)
  message(FATAL_ERROR "C4D_MACMEMORY_NOT_DECLARED")
endif()
# The linker flags above are Mach-O-only. Remove only in this test-only ELF
# project, after verifying their provenance and the reexport CMake contract.
set_property(TARGET CoreServices PROPERTY LINK_FLAGS "")
add_executable(witness witness.c)
target_link_libraries(witness PRIVATE QuickTime)
message(STATUS "C4D_HOST_CHAIN_CONFIGURED")
''')


def trial(where: Path, reexport: str, mutation: str | None) -> tuple[bool, str, str]:
    prepare(where, reexport, mutation)
    config = cmd(['cmake', '-S', str(where), '-B', str(where / 'build'), '-G', 'Ninja'], where)
    if config.returncode:
        return False, 'configure', config.stderr + config.stdout
    build = cmd(['cmake', '--build', str(where / 'build'), '--target', 'witness'], where)
    if build.returncode:
        return False, 'link', build.stderr + build.stdout
    elf = where / 'build'
    for library, provider in (('CoreServices', 'CarbonCore'), ('QuickTime', 'CoreServices')):
        path = (elf / f'src/frameworks/CoreServices/{library}' if library == 'CoreServices'
                else elf / f'src/frameworks/QuickTime/{library}')
        dynamic = cmd(['readelf', '-d', str(path)], where)
        if dynamic.returncode or f'[{provider}]' not in dynamic.stdout:
            return False, 'elf-needed', 'Missing DT_NEEDED ' + provider + ' in ' + str(path) + '\n' + dynamic.stdout + dynamic.stderr
    execution = cmd([str(elf / 'witness')], where)
    if execution.returncode:
        return False, 'runtime', f'exit={execution.returncode} ' + execution.stderr + execution.stdout
    return True, 'runtime', 'C4D_HOST_CHAIN_PASS'


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fragment-fixture', action='store_true',
                    help='local mirror: only the exact reexport() excerpt is available')
    args = ap.parse_args()
    for tool in ('cmake', 'ninja', 'cc', 'readelf', 'git'):
        check(shutil.which(tool) is not None, 'missing host tool: ' + tool)
    reexport = load_reexport(args.fragment_fixture)
    with tempfile.TemporaryDirectory(prefix='d4rling-c4d-chain-') as tmp:
        temp = Path(tmp)
        positive = temp / 'positive'
        positive.mkdir()
        ok, stage, log = trial(positive, reexport, None)
        check(ok, 'positive failed at ' + stage + ': ' + log[-1800:])
        print('PASS POSITIVE: synthetic ELF CarbonCore -> CoreServices -> QuickTime -> witness')
        negatives = [
            ('missing_quicktime_dependency', 'configure', 'C4D_QUICKTIME_LINK_WRONG'),
            ('missing_carbon_dependency', 'configure', 'C4D_CARBON_LINK_MISSING'),
            ('missing_carbon_reexport', 'configure', 'C4D_CARBON_REEXPORT_PATH_WRONG'),
            ('wrong_carbon_reexport_path', 'configure', 'C4D_CARBON_REEXPORT_PATH_WRONG'),
            ('broken_carbon_provider', 'link', 'undefined reference'),
            ('broken_core_provider', 'link', 'undefined reference'),
            ('wrong_runtime_value', 'runtime', 'exit=7'),
        ]
        for i, (mutation, expected_stage, marker) in enumerate(negatives, 1):
            where = temp / ('negative_' + mutation)
            where.mkdir()
            ok, stage, log = trial(where, reexport, mutation)
            check(not ok and stage == expected_stage and marker in log,
                  f'mutant {mutation} survived/unexpected stage={stage}: {log[-1500:]}')
            print(f'PASS NEGATIVE {i}/{len(negatives)}: {mutation} ({stage})')
    print('C4D_HOST_CHAIN_PASS: 1 ELF build/link/runtime positive; 7 negatives detected; '
          'MACHO_I386_NOT_EXECUTED; PRODUCTION_NO_GO')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print('FAIL:', str(exc), file=sys.stderr)
        sys.exit(1)
