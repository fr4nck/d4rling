#!/usr/bin/env python3
"""Fail-closed source gate for the D4rling Machdep i386 research patch.

Reads pinned XNU objects only; any patch application happens in a temp dir.
No downloads, branch changes, or installation changes.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import tempfile

REV = 'ba34c8ac576190d1bbacb6ee6b1903204a576114'
MACH = 'darling/src/libsystem_kernel/emulation/src/xnu_syscall/machdep/machdep_syscall.S'
GEN = 'gen/bsdsyscalls/custom.S'
CUSTOM = 'libsyscall/custom/custom.S'
HEADER = 'darling/src/libsystem_kernel/emulation/include/xnu_syscall/machdep/machdep_syscall_table.h'
TABLE = 'darling/src/libsystem_kernel/emulation/src/xnu_syscall/machdep/machdep_syscall_table.c'
BLOBS = {
    MACH: '6cf2c60ee6f90c483d57201aa3d2e2ca823c5c19',
    GEN: '3f72013314c58f729ed7ee2efb8506597afae471',
    CUSTOM: '3f72013314c58f729ed7ee2efb8506597afae471',
    HEADER: 'ad3c3dfcb1c3b9d78a89104b3f74340c075c8b59',
    TABLE: 'fc5b04f0d193838606339b465757a1340674921a',
}
PATCH = Path(__file__).resolve().parents[2] / 'patches/bsd-i386-machdep-guard-cf-ba34c8ac.patch'


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE).decode()


def contract(source: dict[str, str]) -> list[str]:
    errors = []
    for path in BLOBS:
        if path not in source:
            return ['missing ' + path]
    if source[GEN] != source[CUSTOM]:
        errors.append('custom copies differ')
    if '__machdep_syscall_table[10]' not in source[HEADER] or '__machdep_syscall_table[10]' not in source[TABLE]:
        errors.append('table size is not 10')
    if '[3] = sys_thread_set_tsd_base' not in source[TABLE]:
        errors.append('Machdep table slot 3 changed')
    mach = source[MACH].split('#elif defined(__i386__)')[-1].split('#elif defined(__aarch64__)')[0]
    if not re.search(r'andl\s+\$0xffff, %eax.*?movl\s+\(%ecx,%eax,4\), %eax', mach, re.S):
        errors.append('original dispatcher lookup changed')
    if '.no_sys:\n\tpushl\t%ecx' not in mach:
        errors.append('original unknown handler call changed')
    custom = source[GEN].split('#if defined(__i386__)')[-1].split('#elif defined(__x86_64__)')[0]
    for name, nr in (('_i386_get_ldt:', '6'), ('_i386_set_ldt:', '5')):
        if not re.search(re.escape(name) + r'.*?movl\s+\$' + nr +
                         r'\s*,\s*%eax\s+MACHDEP_SYSCALL_TRAP\s+jnb', custom, re.S):
            errors.append('original LDT stub changed: ' + name)
    return errors


def load(repo: Path) -> dict[str, str]:
    if git(repo, 'rev-parse', REV + '^{commit}').strip() != REV:
        raise ValueError('wrong XNU revision')
    contents = {}
    for path, expected in BLOBS.items():
        actual = git(repo, 'rev-parse', REV + ':' + path).strip()
        if actual != expected:
            raise ValueError('XNU blob mismatch: ' + path)
        contents[path] = git(repo, 'cat-file', 'blob', actual)
    return contents


def verify_patch(src: dict[str, str]) -> list[str]:
    if not PATCH.is_file():
        return ['patch missing']
    with tempfile.TemporaryDirectory(prefix='d4rling-machdep-') as folder:
        root = Path(folder)
        for path, data in src.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(data)
        result = subprocess.run(['git', 'apply', '--check', str(PATCH)], cwd=root,
                                capture_output=True, text=True)
        if result.returncode:
            return ['patch does not apply to pinned originals: ' + result.stderr.strip()]
        subprocess.run(['git', 'apply', str(PATCH)], cwd=root, check=True,
                       capture_output=True)
        changed = {path: (root / path).read_text() for path in src}
        mach = changed[MACH].split('#elif defined(__i386__)')[-1].split('#elif defined(__aarch64__)')[0]
        order = ('andl', 'movl\t%eax, %edx', 'cmpl\t$10, %eax',
                 'jae\t\t.no_sys', 'movl\t(%ecx,%eax,4), %eax')
        positions = [mach.find(item) for item in order]
        errors = []
        if any(pos < 0 for pos in positions) or positions != sorted(positions):
            errors.append('guard is not before table lookup')
        if '.no_sys:\n\tpushl\t%edx' not in mach:
            errors.append('wrong unknown Machdep number')
        if changed[GEN] != changed[CUSTOM]:
            errors.append('custom copies diverged after patch')
        for path in (GEN, CUSTOM):
            i386 = changed[path].split('#if defined(__i386__)')[-1].split('#elif defined(__x86_64__)')[0]
            if i386.count('DARLING_SYSCALL_RESULT_TO_CF') != 2:
                errors.append('missing i386 LDT conversion: ' + path)
            if changed[path].split('#elif defined(__x86_64__)')[-1] != src[path].split('#elif defined(__x86_64__)')[-1]:
                errors.append('non-i386 source modified: ' + path)
        for path in (HEADER, TABLE):
            if changed[path] != src[path]:
                errors.append('table source unexpectedly changed: ' + path)
        return errors


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--xnu', type=Path, required=True)
    args = p.parse_args()
    try:
        sources = load(args.xnu)
        errors = contract(sources)
        if not errors:
            errors = verify_patch(sources)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print('MACHDEP_PINNED=BLOCKED_SOURCE', exc)
        return 3
    for error in errors:
        print('MACHDEP_PINNED_FAIL=' + error)
    print('MACHDEP_PINNED=' + ('PASS_STATIC' if not errors else 'FAIL'))
    return 0 if not errors else 10


if __name__ == '__main__':
    raise SystemExit(main())
