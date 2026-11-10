#!/usr/bin/env python3
"""Bounded cross-compile gate for XNU/Darling i386 variadic syscall() CF fix.

Reads pinned XNU Git blobs if --xnu is supplied. For --selftest, it only
exercises an exact short excerpt of the i386 body; never claims authentic
source qualification. All writes are within temporary directories.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import tempfile

REV = 'ba34c8ac576190d1bbacb6ee6b1903204a576114'
BLOBS = {
    'gen/bsdsyscalls/___syscall.S': '969b5847c4336fb16fa6a73fc06d9dc9ca38fe62',
    'libsyscall/custom/__syscall.S': '8d0c718312942ba3522c8ee9cdffb1c9dc472c4b',
    'gen/bsdsyscalls/SYS.h': '681a421262ccacce576ee6366a9b484ce73b3b3e',
    'libsyscall/custom/SYS.h': 'ba50e058a9c5dc621580c57522d1afb8bbd54c2a',
    'osfmk/mach/i386/syscall_sw.h': '175b89252a44670f017ac1542347cb4088832ae2',
}
TARGET = '\tUNIX_SYSCALL_TRAP\n\tmovl\t(%esp),%edx'
REPLACE = ('\tUNIX_SYSCALL_TRAP\n#ifdef DARLING\n'
           '\t// Darling dispatcher returns raw -errno, not a reliable CF.\n'
           '\tDARLING_SYSCALL_RESULT_TO_CF\n#endif\n\tmovl\t(%esp),%edx')

# Only the initial 32-bit body is replicated for the local, offline selftest.
# For the full genuine-source gate use --xnu and read the pinned Git objects.
EXCERPT = '''#if defined(__i386__)
LEAF(___syscall, 0)
\tpopl\t%ecx\t\t// ret addr
\tpopl\t%eax\t\t// syscall number
\tpushl\t%ecx
\tUNIX_SYSCALL_TRAP
\tmovl\t(%esp),%edx\t// add one element to stack so
#ifdef DARLING
\t// Pushing ecx will cause a i386 process
\t// that calls syscall(...) to crash.
\tpushl\t%edx
#else
\tpushl\t%ecx\t\t// caller "pop" will work
#endif
\tjnb\t2f
\tBRANCH_EXTERN(tramp_cerror)
2:
END(___syscall)
#elif defined(__x86_64__)
/* not built in the selftest */
'''

ABI_SHIM = '''#ifndef GUARD_NON_DARLING
#define DARLING 1
#endif
#define LEAF(name, n) .globl name ; name:
#define END(name) retl
#ifdef DARLING
#define UNIX_SYSCALL_TRAP calll __darling_bsd_syscall
#else
#define UNIX_SYSCALL_TRAP int $0x80
#endif
#define DARLING_SYSCALL_RESULT_TO_CF cmpl $-4095, %eax ; cmc ; jnc 9f ; negl %eax ; 9:
#define BRANCH_EXTERN(name) jmp name
'''


class GateError(Exception):
    pass


def load_pinned(repo: Path) -> dict[str, str]:
    def git(*args: str) -> str:
        return subprocess.check_output(['git', '-C', str(repo), *args],
                                       stderr=subprocess.PIPE).decode('utf-8')
    if git('rev-parse', f'{REV}^{{commit}}').strip() != REV:
        raise GateError('incorrect XNU commit')
    sources = {}
    for path, blob in BLOBS.items():
        actual = git('rev-parse', f'{REV}:{path}').strip()
        if actual != blob:
            raise GateError(f'XNU_BLOB_MISMATCH: {path}')
        sources[path] = git('cat-file', 'blob', blob)
    return sources


def i386_part(source: str) -> str:
    start = source.find('#if defined(__i386__)')
    end = source.find('#elif defined(__x86_64__)', start + 1)
    if start < 0 or end < 0:
        raise GateError('missing i386 section')
    return source[start:end] + '\n#endif\n'


def apply_candidate(source: str) -> str:
    i386 = i386_part(source)
    if i386.count(TARGET) != 1 or 'DARLING_SYSCALL_RESULT_TO_CF' in i386:
        raise GateError('expected unique unfixed i386 syscall() site')
    start = source.index('#if defined(__i386__)')
    end = source.index('#elif defined(__x86_64__)', start)
    result = source[:start] + source[start:end].replace(TARGET, REPLACE, 1) + source[end:]
    if result[end + len(REPLACE) - len(TARGET):] != source[end:]:
        raise GateError('non-i386 source changed')
    return result


def check_upstream_macros(source: dict[str, str]) -> None:
    gen = i386_part(source['gen/bsdsyscalls/SYS.h'])
    custom = i386_part(source['libsyscall/custom/SYS.h'])
    if gen != custom:
        raise GateError('SYS.h i386 divergence')
    for fragment in ('#define DARLING_SYSCALL_RESULT_TO_CF',
                     'cmpl\t$-4095, %eax', '\t\tcmc', '\t\tjnc\t9f', '\t\tnegl\t%eax',
                     'UNIX_SYSCALL_INT_TRAP', 'UNIX_SYSCALL_SYSENTER'):
        if fragment not in gen:
            raise GateError(f'upstream SYS.h conversion missing: {fragment}')
    if 'call __darling_bsd_syscall' not in source['osfmk/mach/i386/syscall_sw.h']:
        raise GateError('upstream trap route missing')


def compile_i386(body: str, temp: Path, name: str, extra: tuple[str, ...] = ()) -> tuple[bytes, str]:
    source = temp / f'{name}.S'
    target = temp / f'{name}.o'
    source.write_text(i386_part(body))
    subprocess.run(['clang', '-target', 'i386-apple-macosx10.9',
                    '-x', 'assembler-with-cpp', '-include', str(temp / 'abi-shim.h'),
                    *extra, '-c', str(source), '-o', str(target)],
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    data = target.read_bytes()
    if len(data) < 40 or data[:4] != b'\xce\xfa\xed\xfe' or data[4:8] != (7).to_bytes(4, 'little'):
        raise GateError('object is not Mach-O i386')
    asm = subprocess.check_output(['llvm-objdump', '--macho', '--disassemble', str(target)],
                                  text=True)
    return data, asm


def check_disassembly(original: str, candidate: str) -> None:
    def ops(asm: str) -> list[str]:
        return [x for x in re.findall(r'\t(calll|cmpl|cmc|jae|negl|movl|pushl|jmp|retl)\b', asm)]
    baseline = ops(original)
    modified = ops(candidate)
    expected = ['calll', 'cmpl', 'cmc', 'jae', 'negl', 'movl', 'pushl', 'jae']
    if 'calll' not in modified:
        raise GateError('missing BSD dispatcher call in candidate')
    begin = modified.index('calll')
    if modified[begin:begin+len(expected)] != expected:
        raise GateError(f'new i386 CF conversion opcode order incorrect: {modified!r}')
    if baseline.count('cmc') or baseline.count('negl'):
        raise GateError('baseline contains CF conversion unexpectedly')
    if candidate.count('tramp_cerror') != 1:
        raise GateError('missing/duplicate cerror trampoline branch')
    if not original.count('tramp_cerror'):
        raise GateError('baseline does not reach cerror branch')


def qualify(sources: dict[str, str], patch: Path | None = None) -> None:
    full = all(path in sources for path in BLOBS)
    if full:
        check_upstream_macros(sources)
    originals = {path: sources[path] for path in BLOBS if path.endswith('___syscall.S')}
    if len(originals) == 1 and 'gen/bsdsyscalls/___syscall.S' in originals:
        # Selftest: short excerpt, not an authentic XNU source tree.
        originals['libsyscall/custom/__syscall.S'] = sources['gen/bsdsyscalls/___syscall.S']
    if len(originals) != 2:
        raise GateError('expected two syscall() source copies')
    for name, src in originals.items():
        candidate = apply_candidate(src)
        if src[src.index('#elif defined(__x86_64__)'):] != candidate[candidate.index('#elif defined(__x86_64__)'):]:
            raise GateError(f'x86_64 changed in {name}')
    with tempfile.TemporaryDirectory(prefix='d4rling-syscall-cf-') as temporary:
        t = Path(temporary)
        (t / 'abi-shim.h').write_text(ABI_SHIM)
        original_source = originals['gen/bsdsyscalls/___syscall.S']
        new_source = apply_candidate(original_source)
        old_bin, old_asm = compile_i386(original_source, t, 'baseline')
        new_bin, new_asm = compile_i386(new_source, t, 'candidate')
        if old_bin == new_bin:
            raise GateError('candidate unchanged')
        check_disassembly(old_asm, new_asm)
        old_nd, _ = compile_i386(original_source, t, 'baseline-nondarling', ('-DGUARD_NON_DARLING',))
        new_nd, _ = compile_i386(new_source, t, 'candidate-nondarling', ('-DGUARD_NON_DARLING',))
        if old_nd != new_nd:
            raise GateError('non-DARLING i386 objects differ')
    print('SYSCALL_CF_MACHO_I386=PASS')
    print('SYSCALL_CF_ASM_DIFFERENTIAL=PASS')
    print('SYSCALL_CF_NON_DARLING_IDENTICAL=PASS')
    print('SYSCALL_CF_SOURCE=' + ('PINNED_UPSTREAM' if full else 'EXCERPT_ONLY'))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--xnu', type=Path)
    g.add_argument('--selftest', action='store_true')
    args = p.parse_args()
    try:
        source = load_pinned(args.xnu) if args.xnu else {'gen/bsdsyscalls/___syscall.S': EXCERPT}
        qualify(source)
    except (GateError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f'SYSCALL_CF_GATE=FAIL_OR_BLOCKED {exc}')
        return 10
    print('SYSCALL_CF_GATE=PASS_BOUNDED' if args.xnu else 'SYSCALL_CF_GATE=PASS_EXCERPT_ONLY')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
