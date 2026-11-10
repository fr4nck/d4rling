#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""C4-D-L1: exercise real add_framework() with a synthetic host-only linker.

This checks CMake target/link semantics, not Darling, Mach-O, CarbonCore's
actual binary, Memory Manager C4, or a QuickTime/Logic runtime.
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
PATCH = HERE / 'c4d-cmake-proposal.patch'
BASE = {
    'cmake/darling_parse_components.cmake': '7605a01569f6634d0cf4c0a948c3c4acd893dde9',
    'src/frameworks/CMakeLists.txt': 'ea2f9c07e83e2520de3fbce792ef7c429d11dc5a',
    'src/frameworks/QuickTime/CMakeLists.txt': '5c6d8ddd44341653be1e837133d5473c4d04ef6d',
}
FRAMEWORK_BLOB = 'f9a8ede1560936a3c5d1c140ade89b632135d4d9'
FRAMEWORK_PREFIX_SHA256 = '83def2451ccfb1c94eed9c3c0ad2a811759e2f137a3808275182941cb3f70439'
PATCH_SHA256 = '1f6caa834c45f43228602d4f76adaa177a92d6a5fa700aab4e15a3a149eed434'


def must(test: bool, message: str) -> None:
    if not test:
        raise RuntimeError(message)


def blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=35, check=False)


def replace_one(path: Path, old: str, new: str) -> None:
    source = path.read_text()
    must(source.count(old) == 1, f'mutant anchor absent/ambiguous: {path}: {old!r}')
    path.write_text(source.replace(old, new))


def framework_prefix(allow_fragment: bool) -> str:
    raw = (ROOT / 'cmake/darling_framework.cmake').read_bytes()
    if not allow_fragment:
        must(blob(raw) == FRAMEWORK_BLOB, 'full framework macro source changed')
    src = raw.decode('utf-8')
    stop = 'endfunction(add_framework)'
    must(src.count(stop) == 1, 'ambiguous add_framework definition')
    text = src[:src.index(stop) + len(stop)].rstrip('\n') + '\n'
    must(hashlib.sha256(text.encode()).hexdigest() == FRAMEWORK_PREFIX_SHA256,
         'add_framework macro source does not match GitHub-pinned excerpt')
    if allow_fragment:
        must(src.rstrip('\n') == text.rstrip('\n'),
             'fragment-fixture must contain only the pinned excerpt')
    return text


def prepare(dest: Path, macro: str, mutation: str | None = None) -> None:
    for rel, sha in BASE.items():
        raw = (ROOT / rel).read_bytes()
        must(blob(raw) == sha, 'base blob mismatch ' + rel)
        p = dest / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
    must(run(['git', 'apply', '--check', str(PATCH)], dest).returncode == 0,
         'patch cannot apply to pinned source')
    must(run(['git', 'apply', str(PATCH)], dest).returncode == 0,
         'patch apply failed in isolated fixture')

    qtcmake = dest / 'src/frameworks/QuickTime/CMakeLists.txt'
    if mutation == 'omit_core_dependency':
        replace_one(qtcmake, '        CoreServices\n        system', '        system')
    if mutation == 'wrong_version':
        replace_one(qtcmake, 'set(FRAMEWORK_VERSION "A")', 'set(FRAMEWORK_VERSION "B")')
    if mutation == 'macro_drops_dependencies':
        macro = macro.replace('target_link_libraries(${my_name} PRIVATE ${FRAMEWORK_DEPENDENCIES})',
                              'target_link_libraries(${my_name} PRIVATE system)')
    (dest / 'cmake/darling_framework.cmake').write_text(macro)
    (dest / 'cmake/darling_lib.cmake').write_text('''# Test-only stand-in; no Darling linker, no Mach-O, no real QuickTime source.
function(add_darling_library name)
  add_library(${name} SHARED "${CMAKE_SOURCE_DIR}/probe_quicktime.c")
endfunction()
function(make_fat name)
endfunction()
''')
    (dest / 'cmake/darling_open_source_sdk.cmake').write_text('''function(remove_sdk_framework name)
endfunction()
function(generate_sdk_framework name)
endfunction()
''')
    (dest / 'cmake/InstallSymlink.cmake').write_text('''function(InstallSymlink source dest)
endfunction()
''')
    (dest / 'probe_quicktime.c').write_text('''extern int d4rl_c4d_core(void);
int d4rl_c4d_quicktime(void) { return d4rl_c4d_core(); }
''')
    provider = 'int d4rl_c4d_core(void) { return 42; }\n'
    if mutation == 'provider_missing_symbol':
        provider = 'int d4rl_wrong_core(void) { return 42; }\n'
    (dest / 'probe_core.c').write_text(provider)
    (dest / 'probe_main.c').write_text('''extern int d4rl_c4d_quicktime(void);
int main(void) { return d4rl_c4d_quicktime() == 42 ? 0 : 7; }
''')
    top = '''cmake_minimum_required(VERSION 3.20)
project(C4DMacroLink LANGUAGES C)
set(CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")
add_library(system INTERFACE)
PROVIDER
include(darling_framework)
add_subdirectory(src/frameworks/QuickTime)
get_target_property(qt_libs QuickTime LINK_LIBRARIES)
if(NOT "${qt_libs}" STREQUAL "CoreServices;system")
  message(FATAL_ERROR "QT_LINK_INPUTS_WRONG:${qt_libs}")
endif()
if(NOT TARGET QuickTime_A)
  message(FATAL_ERROR "QuickTime_A_ALIAS_MISSING")
endif()
get_target_property(qt_id QuickTime DYLIB_INSTALL_NAME)
if(NOT "${qt_id}" STREQUAL "/System/Library/Frameworks/QuickTime.framework/Versions/A/QuickTime")
  message(FATAL_ERROR "QT_INSTALL_NAME_WRONG:${qt_id}")
endif()
target_link_options(QuickTime PRIVATE LINKER:--no-undefined)
add_executable(probe probe_main.c)
target_link_libraries(probe PRIVATE QuickTime)
'''
    definition = 'add_library(CoreServices SHARED probe_core.c)'
    if mutation == 'no_provider_target':
        definition = ''
    (dest / 'CMakeLists.txt').write_text(top.replace('PROVIDER', definition))


def trial(label: str, macro: str, scratch: Path, mutation: str | None = None) -> tuple[bool, str, str]:
    where = scratch / label
    where.mkdir()
    prepare(where, macro, mutation)
    configured = run(['cmake', '-S', str(where), '-B', str(where / 'build'), '-G', 'Ninja'], where)
    if configured.returncode != 0:
        return False, 'configure', configured.stderr + configured.stdout
    built = run(['cmake', '--build', str(where / 'build'), '--target', 'probe', '-v'], where)
    if built.returncode != 0:
        return False, 'link', built.stderr + built.stdout
    ran = run([str(where / 'build/probe')], where)
    if ran.returncode != 0:
        return False, 'runtime', ran.stderr + ran.stdout
    return True, 'runtime', configured.stdout + built.stdout + ran.stdout


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument('--fragment-fixture', action='store_true',
                      help='local test only: require exact 133-line archived macro excerpt')
    options = args.parse_args()
    for executable in ('cmake', 'git', 'ninja', 'cc'):
        must(shutil.which(executable) is not None, f'missing host test tool {executable}')
    must(hashlib.sha256(PATCH.read_bytes()).hexdigest() == PATCH_SHA256,
         'archived patch checksum mismatch')
    macro = framework_prefix(options.fragment_fixture)
    print('PASS: pinned macro, CMake inputs, and proposal checksum')
    with tempfile.TemporaryDirectory(prefix='d4rling-c4d-l1-') as tmp:
        scratch = Path(tmp)
        ok, stage, output = trial('positive', macro, scratch)
        must(ok, f'host ELF positive failed at {stage}: {output[-1200:]}')
        must('libCoreServices.so' in output, 'link line did not include CoreServices target')
        print('PASS: genuine add_framework() extracted from D4rling; host ELF build/link/run rc=0; dependency visible')
        mutants = [
            ('omit_core_dependency', 'configure', 'QT_LINK_INPUTS_WRONG'),
            ('no_provider_target', 'link', 'CoreServices'),
            ('provider_missing_symbol', 'link', 'undefined reference'),
            ('macro_drops_dependencies', 'configure', 'QT_LINK_INPUTS_WRONG'),
            ('wrong_version', 'configure', 'QuickTime_A_ALIAS_MISSING'),
        ]
        for i, (label, stage_expected, marker) in enumerate(mutants, 1):
            ok, stage, log = trial('negative_' + label, macro, scratch, label)
            must(not ok and stage == stage_expected and marker in log,
                 f'negative {label} did not fail as expected: stage={stage}, log={log[-800:]}')
            print(f'PASS NEGATIVE {i}/{len(mutants)}: {label} detected at {stage}')
    print('C4D_L1_HOST_ELF_PASS: 1 positive link/run; 5 negative witnesses; ' 
          'MACHO_I386_NOT_EXECUTED; PRODUCTION_NO_GO')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print('FAIL: ' + str(exc), file=sys.stderr)
        sys.exit(1)
