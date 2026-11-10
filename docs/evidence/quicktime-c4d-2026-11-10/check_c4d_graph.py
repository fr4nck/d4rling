#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""C4-D: isolated, real-CMake configuration checks of the proposed graph.

Only the three SHA-pinned CMake files are read from the checkout. The archive
patch is applied to copies inside a temporary directory. Other framework
subdirectories and framework creation are intercepted by test-only stubs;
this is NOT a Darling build, Mach-O link, or i386 runtime qualification.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PATCH = HERE / 'c4d-cmake-proposal.patch'
FILES = {
    'cmake/darling_parse_components.cmake': '7605a01569f6634d0cf4c0a948c3c4acd893dde9',
    'src/frameworks/CMakeLists.txt': 'ea2f9c07e83e2520de3fbce792ef7c429d11dc5a',
    'src/frameworks/QuickTime/CMakeLists.txt': '5c6d8ddd44341653be1e837133d5473c4d04ef6d',
}
PATCH_SHA256 = '1f6caa834c45f43228602d4f76adaa177a92d6a5fa700aab4e15a3a149eed434'


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True,
                          timeout=30, check=False)


def git_sha(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def mutate(file: Path, old: str, new: str) -> None:
    raw = file.read_text()
    require(raw.count(old) == 1, f'mutation anchor absent/ambiguous: {file.name}: {old[:42]!r}')
    file.write_text(raw.replace(old, new))


def make_fixture(where: Path, apply: bool, change: str | None = None) -> None:
    for name in FILES:
        dest = where / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    if apply:
        check = run(['git', 'apply', '--check', str(PATCH)], where)
        require(check.returncode == 0, 'git apply --check: ' + check.stderr)
        action = run(['git', 'apply', str(PATCH)], where)
        require(action.returncode == 0, 'git apply: ' + action.stderr)

    parser = where / 'cmake/darling_parse_components.cmake'
    frameworks = where / 'src/frameworks/CMakeLists.txt'
    quicktime = where / 'src/frameworks/QuickTime/CMakeLists.txt'
    if change == 'no_core_link':
        mutate(quicktime, '        CoreServices\n        system', '        system')
    elif change == 'no_quicktime_gate':
        mutate(frameworks, 'if (COMPONENT_gui_stubs OR COMPONENT_quicktime)', 'if (COMPONENT_gui_stubs)')
    elif change == 'gui_dependency':
        mutate(parser, 'set(COMPONENT_DEPS cli PARENT_SCOPE)\n\telseif ("${COMPONENT}" STREQUAL "dev_gui_common")',
               'set(COMPONENT_DEPS gui_stubs PARENT_SCOPE)\n\telseif ("${COMPONENT}" STREQUAL "dev_gui_common")')
    elif change == 'duplicate_quicktime':
        mutate(frameworks, '    add_subdirectory(QuickTime)', '    add_subdirectory(QuickTime)\n    add_subdirectory(QuickTime)')
    elif change == 'wrong_install_component':
        mutate(frameworks, 'set(CMAKE_INSTALL_DEFAULT_COMPONENT_NAME "quicktime")',
               'set(CMAKE_INSTALL_DEFAULT_COMPONENT_NAME "gui_stubs")')
    elif change == 'drop_legacy_gate':
        mutate(frameworks, 'if (COMPONENT_gui_stubs OR COMPONENT_quicktime)', 'if (COMPONENT_quicktime)')
    elif change is not None:
        raise RuntimeError('unrecognized mutation ' + change)

    # The actual frameworks/CMakeLists.txt is evaluated by CMake's native
    # add_subdirectory command; only its recursive child projects are mocked.
    subdirs = re.findall(r'^\s*add_subdirectory\(([^)]+)\)', frameworks.read_text(), re.M)
    require(len(subdirs) > 50 and 'QuickTime' in subdirs, 'unexpected framework graph')
    for rel in set(subdirs):
        if rel == 'QuickTime':
            continue
        path = where / 'src/frameworks' / rel
        path.mkdir(parents=True, exist_ok=True)
        (path / 'CMakeLists.txt').write_text(
            f'file(APPEND "${{CMAKE_BINARY_DIR}}/trace.tsv" "dir|{rel}|${{CMAKE_INSTALL_DEFAULT_COMPONENT_NAME}}\\n")\n')

    (where / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.20)
project(C4DGraph LANGUAGES NONE)
include("${CMAKE_SOURCE_DIR}/cmake/darling_parse_components.cmake")
darling_parse_components("${COMPONENTS}")
function(remove_sdk_framework name)
endfunction()
function(generate_sdk_framework name)
endfunction()
function(add_framework name)
    cmake_parse_arguments(F "FAT;CURRENT_VERSION" "VERSION" "SOURCES;DEPENDENCIES" ${ARGN})
    file(APPEND "${CMAKE_BINARY_DIR}/trace.tsv" "framework|${name}|${CMAKE_INSTALL_DEFAULT_COMPONENT_NAME}|${F_DEPENDENCIES}\\n")
endfunction()
add_subdirectory(src/frameworks)
''')


def check_graph(lines: list[str], profile: str) -> None:
    items = [line.split('|') for line in lines]
    qt = [x for x in items if x[0] == 'framework' and x[1] == 'QuickTime']
    core = [x for x in items if x[0] == 'dir' and x[1] == 'CoreServices']
    gui = [x for x in items if x[0] == 'dir' and x[1] in {'OpenGL', 'ImageIO', 'QTKit'}]

    # A minimal profile should enable QuickTime and CoreServices without the
    # Cocotron/GUI stubs. The historical profile must remain available.
    expected = {
        'quicktime': (1, 'quicktime', 1, 0),
        ' QuickTime ': (1, 'quicktime', 1, 0),
        'quicktime,cli': (1, 'quicktime', 1, 0),
        'gui_stubs': (1, 'gui_stubs', 1, 3),
        'quicktime,gui_stubs': (1, 'gui_stubs', 1, 3),
        'cli': (0, '', 1, 0),
        'core': (0, '', 0, 0),
        'stock': (1, 'gui_stubs', 1, 3),
    }
    count, component, cs_count, gui_count = expected[profile]
    require(len(qt) == count, f'{profile}: QuickTime count {len(qt)} != {count}')
    require(len(core) == cs_count, f'{profile}: CoreServices count {len(core)} != {cs_count}')
    require(len(gui) == gui_count, f'{profile}: GUI dependencies {len(gui)} != {gui_count}')
    if qt:
        require(qt[0][2] == component, f'{profile}: incorrect install component {qt[0][2]}')
        require(qt[0][3].split(';') == ['CoreServices', 'system'],
                f'{profile}: QuickTime linker inputs {qt[0][3]}')
        require(lines.index('|'.join(core[0])) < lines.index('|'.join(qt[0])),
                f'{profile}: CoreServices not configured before QuickTime')


def configure(where: Path, profile: str) -> tuple[bool, str]:
    build = where / '_build'
    cmd = ['cmake', '-S', str(where), '-B', str(build), f'-DCOMPONENTS={profile}']
    result = run(cmd, where)
    if result.returncode != 0:
        return False, 'CMake configure failed: ' + (result.stderr + result.stdout)[-900:]
    trace = build / 'trace.tsv'
    # In the `core` profile, no framework child is enabled: an empty trace
    # is a legitimate positive outcome rather than a missing artifact.
    lines = trace.read_text().splitlines() if trace.is_file() else []
    try:
        check_graph(lines, profile)
    except RuntimeError as exc:
        return False, str(exc)
    return True, ''


def main() -> None:
    require(shutil.which('cmake') is not None, 'cmake not installed')
    require(shutil.which('git') is not None, 'git not installed')
    require(hashlib.sha256(PATCH.read_bytes()).hexdigest() == PATCH_SHA256, 'patch checksum')
    for name, expected in FILES.items():
        require(git_sha((ROOT / name).read_bytes()) == expected, 'wrong source blob: ' + name)
    print('PASS: pinned inputs 3/3 and patch SHA-256')

    positives = ['quicktime', ' QuickTime ', 'quicktime,cli', 'gui_stubs',
                 'quicktime,gui_stubs', 'cli', 'core', 'stock']
    negatives = [
        ('prepatch', 'quicktime', False, None),
        ('no_core_link', 'quicktime', True, 'no_core_link'),
        ('no_quicktime_gate', 'quicktime', True, 'no_quicktime_gate'),
        ('gui_dependency', 'quicktime', True, 'gui_dependency'),
        ('duplicate_quicktime', 'quicktime', True, 'duplicate_quicktime'),
        ('wrong_install_component', 'quicktime', True, 'wrong_install_component'),
        ('drop_legacy_gate', 'gui_stubs', True, 'drop_legacy_gate'),
    ]
    with tempfile.TemporaryDirectory(prefix='d4rling-c4d-graph-') as t:
        temp = Path(t)
        for i, profile in enumerate(positives):
            where = temp / f'pos{i:02d}'
            where.mkdir()
            make_fixture(where, True)
            passed, reason = configure(where, profile)
            require(passed, f'positive {i}: {profile!r}: {reason}')
            print(f'PASS POSITIVE {i+1}/{len(positives)}: {profile!r}')
        for i, (label, profile, apply, change) in enumerate(negatives):
            where = temp / f'neg{i:02d}'
            where.mkdir()
            make_fixture(where, apply, change)
            passed, reason = configure(where, profile)
            require(not passed, f'negative {i}: {label}: mutant survived')
            print(f'PASS NEGATIVE {i+1}/{len(negatives)}: {label} ({reason[:90]})')
    print(f'C4D_GRAPH_PASS: {len(positives)}/{len(positives)} positives; '
          f'{len(negatives)}/{len(negatives)} negatives detected; '
          'DARLING_FULL_CONFIG_NOT_EXECUTED; MACHO_I386_NOT_EXECUTED; PRODUCTION_NO_GO')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print('FAIL: ' + str(exc), file=sys.stderr)
        sys.exit(1)
