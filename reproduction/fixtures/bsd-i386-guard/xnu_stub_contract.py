#!/usr/bin/env python3
"""Read-only source contract for the genuine Darling XNU i386 BSD stubs.

The source is loaded from an existing local git object at a pinned revision.
No checkout, download, build, or guest execution is performed.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

XNU_REV = 'ba34c8ac576190d1bbacb6ee6b1903204a576114'
# Git blob IDs of genuine upstream sources at XNU_REV.
PINNED = {
    'gen/bsdsyscalls/SYS.h': '681a421262ccacce576ee6366a9b484ce73b3b3e',
    'libsyscall/custom/SYS.h': 'ba50e058a9c5dc621580c57522d1afb8bbd54c2a',
    'osfmk/mach/i386/syscall_sw.h': '175b89252a44670f017ac1542347cb4088832ae2',
    'gen/bsdsyscalls/___lseek.S': '0089abc6ad57d81593c99688b851056a2092b544',
    'libsyscall/custom/__lseek.S': '490418f7929be4f132fb6f46089c2dbd2e4df8',
    'gen/bsdsyscalls/___sigreturn.S': '62238b9eda4ffe5fb9d9e3aa4d85ed3b82dba779',
    'libsyscall/custom/__sigaltstack.S': '7c4fceaf571c99c6ffaf5a666d288ecd32eed694',
}


def section(source: str, start: str, end: str) -> str:
    left = source.find(start)
    right = source.find(end, left + len(start)) if left != -1 else -1
    if left == -1 or right == -1:
        return ''
    return source[left:right]


def ordered(source: str, needles: tuple[str, ...]) -> bool:
    offset = 0
    for needle in needles:
        index = source.find(needle, offset)
        if index < 0:
            return False
        offset = index + len(needle)
    return True


def macro_definition(source: str, name: str) -> str:
    """Return one C-preprocessor macro, respecting backslash continuations."""
    lines = source.splitlines()
    prefix = f'#define {name}('
    for index, line in enumerate(lines):
        if line.lstrip().startswith(prefix):
            found = [line]
            while found[-1].rstrip().endswith('\\') and index + len(found) < len(lines):
                found.append(lines[index + len(found)])
            return '\n'.join(found)
    return ''


def source_contract(sources: dict[str, str]) -> list[str]:
    """Return violations. Missing or drifted source cannot produce a PASS."""
    failures: list[str] = []
    for path in PINNED:
        if path not in sources:
            failures.append(f'missing source: {path}')
    if failures:
        return failures

    gen = section(sources['gen/bsdsyscalls/SYS.h'],
                  '#if defined(__i386__)', '#elif defined(__x86_64__)')
    custom = section(sources['libsyscall/custom/SYS.h'],
                     '#if defined(__i386__)', '#elif defined(__x86_64__)')
    if not gen or gen != custom:
        failures.append('i386 SYS.h branches missing or diverged')
    if not ordered(gen, ('#define DARLING_SYSCALL_RESULT_TO_CF',
                         'cmpl\t$-4095, %eax', 'cmc', 'jnc', 'negl')):
        failures.append('i386 raw -errno to CF/EAX conversion changed')
    if not re.search(r'#define UNIX_SYSCALL_SYSENTER\s+call __darling_bsd_syscall\s*;\s*DARLING_SYSCALL_RESULT_TO_CF', gen):
        failures.append('SYSENTER stub does not use Darling dispatcher and CF conversion')
    if not re.search(r'#define UNIX_SYSCALL_INT_TRAP\s+UNIX_SYSCALL_TRAP\s*;\s*DARLING_SYSCALL_RESULT_TO_CF', gen):
        failures.append('INT-style stub does not use trap macro and CF conversion')

    sw = sources['osfmk/mach/i386/syscall_sw.h']
    darling_sw = section(sw, '#else // DARLING', '#endif')
    if not re.search(r'#define UNIX_SYSCALL_TRAP\s*\\\s*call __darling_bsd_syscall', darling_sw):
        failures.append('Darling UNIX_SYSCALL_TRAP bypasses BSD dispatcher')
    if not re.search(r'#define MACHDEP_SYSCALL_TRAP\s*\\\s*call __darling_machdep_syscall', darling_sw):
        failures.append('Darling MACHDEP_SYSCALL_TRAP changed')
    if not re.search(r'#define UNIX_SYSCALL_TRAP\s*\\\s*int \$\(UNIX_INT\)',
                     section(sw, '#ifndef DARLING', '#else // DARLING')):
        failures.append('non-Darling trap baseline missing (conditional drift)')

    raw_ulock = macro_definition(gen, 'ULOCK_RAW_SYSCALL')
    if (not re.search(r'\bcall\s+__darling_bsd_syscall\b', raw_ulock)
        or re.search(r'\b(cmpl|cmc|negl|tramp_cerror)\b|DARLING_SYSCALL_RESULT_TO_CF',
                     raw_ulock)):
        failures.append('ULOCK raw -errno route missing or converted')
    noerror = macro_definition(gen, '__SYSCALL_NOERROR')
    if (not ordered(noerror, ('SYS_##name', 'call', '__darling_bsd_syscall', 'ret'))
        or re.search(r'\b(cmpl|cmc|negl|tramp_cerror)\b|DARLING_SYSCALL_RESULT_TO_CF',
                     noerror)):
        failures.append('NOERROR raw-return stub changed or converted')
    ulock = macro_definition(gen, 'ULOCK_SYSCALL')
    if not ordered(ulock, ('ULF_NO_ERRNO_BIT', 'ULOCK_RAW_SYSCALL(name)',
                            'UNIX_SYSCALL_NONAME(name, nargs, cerror)')):
        failures.append('ULOCK_NO_ERRNO branch changed')

    lseek_asm = []
    for path in ('gen/bsdsyscalls/___lseek.S', 'libsyscall/custom/__lseek.S'):
        body = section(sources[path], '#elif defined(__i386__)', '#elif defined(__arm__)')
        lseek_asm.append(body)
        if not ordered(body, ('#ifdef DARLING', 'LEAF(___lseek, 0)',
                              'call\t__darling_bsd_syscall', 'cmpl\t$-1, %edx',
                              'jne\t2f', 'cmpl\t$-4095, %eax',
                              'jb\t2f', 'negl\t%eax',
                              'BRANCH_EXTERN(tramp_cerror)',
                              '#else', '__SYSCALL_INT(___lseek, lseek, 3)')):
            failures.append(f'Darling lseek 64-bit return/error guard changed: {path}')
    if lseek_asm[0] != lseek_asm[1]:
        failures.append('lseek i386 generated/custom implementations diverged')

    for path, name in (('gen/bsdsyscalls/___sigreturn.S', 'sigreturn'),
                       ('libsyscall/custom/__sigaltstack.S', 'sigaltstack')):
        branch = section(sources[path], '#elif defined(__i386__)', '#elif defined(__arm__)')
        if f'__SYSCALL_INT(___{name}, {name}, 3)' not in branch:
            failures.append(f'{name} INT-style stub changed')
    return failures


def read_pinned(repo: Path) -> dict[str, str]:
    """Read exact content by Git object; never touch the index/worktree."""
    def git(*args: str) -> bytes:
        return subprocess.check_output(['git', '-C', str(repo), *args],
                                       stderr=subprocess.PIPE)
    head = git('rev-parse', f'{XNU_REV}^{{commit}}').decode().strip()
    if head != XNU_REV:
        raise ValueError(f'incorrect XNU commit: {head}')
    result: dict[str, str] = {}
    for path, blob in PINNED.items():
        actual = git('rev-parse', f'{XNU_REV}:{path}').decode().strip()
        if actual != blob:
            raise ValueError(f'XNU_BLOB_DRIFT {path}: expected {blob}, got {actual}')
        result[path] = git('cat-file', 'blob', actual).decode('utf-8')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xnu', type=Path, required=True,
                        help='an existing Git repository containing pinned upstream XNU objects')
    args = parser.parse_args()
    try:
        sources = read_pinned(args.xnu)
    except (OSError, ValueError, subprocess.CalledProcessError, UnicodeDecodeError) as err:
        print(f'XNU_STUB_CONTRACT=BLOCKED_SOURCE {err}')
        return 3
    problems = source_contract(sources)
    for problem in problems:
        print('XNU_STUB_CONTRACT_FAILURE=' + problem)
    print('XNU_STUB_CONTRACT=' + ('PASS_STATIC' if not problems else 'FAIL'))
    print(f'XNU_REV={XNU_REV}')
    print(f'XNU_SOURCE_FILES={len(PINNED)}')
    return 0 if not problems else 10


if __name__ == '__main__':
    raise SystemExit(main())
