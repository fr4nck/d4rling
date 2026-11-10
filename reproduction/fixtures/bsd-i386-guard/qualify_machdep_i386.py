#!/usr/bin/env python3
"""Bounded, read-only XNU Machdep i386 qualification.

--selftest: compile/test an isolated i386 excerpt with a minimal macro shim.
--xnu: read pinned genuine XNU Git blobs, patch only private temp copies,
       compile real Machdep.S and extracted genuine LDT routines.
Never modifies XNU, a Darling installation, or the working checkout.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

REV = 'ba34c8ac576190d1bbacb6ee6b1903204a576114'
MACH = 'darling/src/libsystem_kernel/emulation/src/xnu_syscall/machdep/machdep_syscall.S'
GEN = 'gen/bsdsyscalls/custom.S'
CUSTOM = 'libsyscall/custom/custom.S'
HEADER = 'darling/src/libsystem_kernel/emulation/include/xnu_syscall/machdep/machdep_syscall_table.h'
TABLE = 'darling/src/libsystem_kernel/emulation/src/xnu_syscall/machdep/machdep_syscall_table.c'
PINNED = {
    MACH: '6cf2c60ee6f90c483d57201aa3d2e2ca823c5c19',
    GEN: '3f72013314c58f729ed7ee2efb8506597afae471',
    CUSTOM: '3f72013314c58f729ed7ee2efb8506597afae471',
    HEADER: 'ad3c3dfcb1c3b9d78a89104b3f74340c075c8b59',
    TABLE: 'fc5b04f0d193838606339b465757a1340674921a',
}
PATCH = Path(__file__).resolve().parent.parent.parent / 'patches' / 'bsd-i386-machdep-guard-cf-ba34c8ac.patch'
# Minimal stand-ins with the exact source anchors: used only for --selftest.
MACH_FIXTURE = '''.text
.globl __darling_machdep_syscall
.private_extern __darling_machdep_syscall

#if defined(__x86_64__)

__darling_machdep_syscall:
	movq    ___machdep_syscall_table@GOTPCREL(%rip), %r10
	andq	$0xff, %rax
	movq	(%r10,%rax,8), %r10
	test	%r10, %r10
	jz		.no_sys
	# Re-push possible 7th and 8th arg
	movq	24(%rsp), %r11
	pushq	%r11
	movq	24(%rsp), %r11
	pushq	%r11
	call	*%r10
	addq	$16, %rsp
	ret
.no_sys:
	movq	%rax, %rdi
	call	___unknown_syscall_machdep
	ret

#elif defined(__i386__)

#define copy_arg(off) \
	movl	8+off(%esp), %ecx ;\
	movl	%ecx, -24+off(%esp)

__darling_machdep_syscall:
	calll	1f
1:
	popl	%ecx
2:
	movl	L___machdep_syscall_table$non_lazy_ptr-1b(%ecx), %ecx
	andl	$0xffff, %eax // Because there is some extra stuff in upper bytes we don't need
	movl	(%ecx,%eax,4), %eax
	test	%eax, %eax
	jz		.no_sys
	// Copy arguments
	copy_arg(0)
	copy_arg(4)
	copy_arg(8)
	copy_arg(12)
	copy_arg(16)
	copy_arg(20)
	subl	$24, %esp
	call	*%eax
	addl	$24, %esp
	ret
.no_sys:
	pushl	%ecx
	call	___unknown_syscall_machdep
	addl	$4, %esp
	ret

	.section        __IMPORT,__pointers,non_lazy_symbol_pointers
L___machdep_syscall_table$non_lazy_ptr:
	.indirect_symbol        ___machdep_syscall_table
	.long   0

.subsections_via_symbols

#elif defined(__aarch64__)

__darling_machdep_syscall:
	// Save fp/lr -- we make a function call (blr x9) and RET back to caller.
	stp  x29, x30, [sp, #-16]!
	mov  x29, sp
Lentry_hook:
	// NOP sled for xtrace hook (ARM64 NOP = 0xd503201f)
	nop
	nop
	nop
	nop
	adrp x9, ___machdep_syscall_table@GOTPAGE
	ldr  x9, [x9, x16, lsl #3]
	cbz  x9, .no_sys
	blr x9
	ret
.no_sys:
	mov x0, x16
	bl ___unknown_syscall_machdep
	ret

#else
#	error Missing assembly
#endif
'''
LDT_FIXTURE = '''.text
#if defined(__i386__)
	.globl _i386_get_ldt
	ALIGN
_i386_get_ldt:
	movl    $6,%eax
	MACHDEP_SYSCALL_TRAP
	jnb		2f
	jmp		tramp_cerror
2:	ret


	.globl _i386_set_ldt
	ALIGN
_i386_set_ldt:
	movl    $5,%eax
	MACHDEP_SYSCALL_TRAP
	jnb		2f
	jmp		tramp_cerror
2:	ret
#elif defined(__x86_64__)
 ret
#endif
'''
# The upstream excerpts are assembled with the same macro semantics; no Apple
# headers or actual cerror/TLS symbol definition is claimed in this mini-shim.
ABI = '''#define ALIGN .p2align 4
#ifdef DARLING
#define MACHDEP_SYSCALL_TRAP calll __darling_machdep_syscall
#else
#define MACHDEP_SYSCALL_TRAP int $0x81
#endif
#define DARLING_SYSCALL_RESULT_TO_CF cmpl $-4095, %eax ; cmc ; jnc 9f ; negl %eax ; 9:
'''

class GateError(Exception):
    pass


def run(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def read_pinned(root: Path) -> dict[str, str]:
    rev = run(['git', '-C', str(root), 'rev-parse', f'{REV}^{{commit}}']).stdout.strip()
    if rev != REV:
        raise GateError(f'wrong revision: {rev}')
    sources = {}
    for path, expected in PINNED.items():
        actual = run(['git', '-C', str(root), 'rev-parse', f'{REV}:{path}']).stdout.strip()
        if actual != expected:
            raise GateError(f'Git blob mismatch: {path} ({actual})')
        sources[path] = run(['git', '-C', str(root), 'cat-file', 'blob', actual]).stdout
    return sources


def validate_source(sources: dict[str, str], *, full: bool) -> None:
    mach = sources[MACH]
    old = 'andl\t$0xffff, %eax // Because there is some extra stuff in upper bytes we don\'t need'
    if old not in mach or mach.count('movl\t(%ecx,%eax,4), %eax') != 1:
        # In selftest, indentation may be spaces, but the intrinsic operands
        # and relative instruction order must remain the original bug.
        if full:
            raise GateError('original Machdep i386 dispatch site changed')
    idx = mach.find('movl (%ecx,%eax,4), %eax')
    if idx < 0:
        idx = mach.find('movl\t(%ecx,%eax,4), %eax')
    if idx < 0 or not ('andl' in mach[max(0, idx-240):idx]):
        raise GateError('original Machdep table access not located')
    if full:
        if sources[GEN] != sources[CUSTOM]:
            raise GateError('generated and custom LDT stubs diverged')
        if not re.search(r'__machdep_syscall_table\[10\]', sources[HEADER]):
            raise GateError('Machdep table declaration is no longer 10')
        if not re.search(r'__machdep_syscall_table\[10\]', sources[TABLE]):
            raise GateError('Machdep table definition is no longer 10')
        if '[3] = sys_thread_set_tsd_base' not in sources[TABLE]:
            raise GateError('Machdep slot 3 definition changed')
    for path in (GEN, CUSTOM):
        src = sources[path]
        for sym, number in (('_i386_get_ldt:', '6'), ('_i386_set_ldt:', '5')):
            if not re.search(re.escape(sym) + r'\s+movl\s+\$' + number +
                             r'\s*,\s*%eax\s+MACHDEP_SYSCALL_TRAP\s+jnb', src):
                raise GateError(f'uncorrected Machdep wrapper missing: {path} {sym}')


def extract_ldt(source: str) -> str:
    start = source.find('\t.globl _i386_get_ldt')
    if start < 0: start = source.find('.globl _i386_get_ldt')
    end = source.find('\t.globl __thread_set_tsd_base', start)
    if end < 0: end = source.find('.globl __thread_set_tsd_base', start)
    if start < 0 or end < 0 or end <= start:
        raise GateError('missing LDT source section')
    return '.text\n' + source[start:end]


def qualify(sources: dict[str,str], *, full: bool) -> dict[str,str]:
    validate_source(sources, full=full)
    if not PATCH.is_file():
        raise GateError(f'patch unavailable: {PATCH}')
    with tempfile.TemporaryDirectory(prefix='d4rling-machdep-i386-') as d:
        root=Path(d)
        for path, data in sources.items():
            dest=root/path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(data)
        run(['git', 'apply', '--check', str(PATCH)], cwd=root)
        run(['git', 'apply', str(PATCH)], cwd=root)
        patched={path:(root/path).read_text() for path in sources}
        for path in sources:
            if patched[path] == sources[path] and path in (MACH,GEN,CUSTOM):
                raise GateError(f'no change: {path}')
            if path in (HEADER,TABLE) and patched[path] != sources[path]:
                raise GateError(f'table source unexpectedly modified: {path}')
        if full:
            if patched[GEN] != patched[CUSTOM]:
                raise GateError('LDT copies diverged after patch')
        body=patched[MACH]
        code=body[body.index('#elif defined(__i386__)'):body.index('#elif defined(__aarch64__)')]
        cmp_at=code.index('cmpl\t$10, %eax')
        if not (code.index('andl') < code.index('movl\t%eax, %edx') < cmp_at
                < code.index('jae\t\t.no_sys') < code.index('movl\t(%ecx,%eax,4), %eax')):
            raise GateError('Machdep table guard not before table dereference')
        if '.no_sys:\n\tpushl\t%edx' not in code:
            raise GateError('incorrect unknown syscall argument')
        for path in (GEN,CUSTOM):
            if patched[path].count('DARLING_SYSCALL_RESULT_TO_CF') != sources[path].count('DARLING_SYSCALL_RESULT_TO_CF')+2:
                raise GateError('wrong number of LDT conversions')
            for name in ('_i386_get_ldt:', '_i386_set_ldt:'):
                section=patched[path].split(name,1)[1].split('2:',1)[0]
                if not re.search(r'MACHDEP_SYSCALL_TRAP\s+#ifdef DARLING\s+DARLING_SYSCALL_RESULT_TO_CF\s+#endif\s+jnb',section):
                    raise GateError('missing conversion before CF branch')
        artifacts={}
        for arch in ('i386','x86_64'):
            for kind in ('original','candidate'):
                src=root/f'{kind}-{arch}.S'
                src.write_text(sources[MACH] if kind=='original' else patched[MACH])
                out=root/f'{kind}-{arch}.o'
                run(['clang','-target',f'{arch}-apple-macosx10.9','-c',str(src),'-o',str(out)])
                artifacts[f'{kind}-{arch}']=out.read_bytes()
        if artifacts['original-i386']==artifacts['candidate-i386']:
            raise GateError('i386 Machdep dispatcher unchanged')
        if artifacts['original-x86_64']!=artifacts['candidate-x86_64']:
            raise GateError('x86_64 Machdep dispatcher changed')
        for kind in ('original','candidate'):
            data=artifacts[f'{kind}-i386']
            if data[:4] != b'\xce\xfa\xed\xfe' or data[4:8] != (7).to_bytes(4,'little'):
                raise GateError('not a Mach-O i386 object')
        for kind in ('original','candidate'):
            src=root/f'{kind}-ldts.S'
            # Source selftest has no enclosing __thread_set_tsd_base, so use
            # isolated LDT text for both cases; genuine sources are extracted.
            original=extract_ldt(sources[GEN]) if full else sources[GEN]
            candidate=extract_ldt(patched[GEN]) if full else patched[GEN]
            src.write_text('#include "shim.h"\n'+(original if kind=='original' else candidate))
            (root/'shim.h').write_text(ABI)
            for macro in ('DARLING','NON_DARLING'):
                target=root/f'{kind}-{macro}.o'
                args=['clang','-target','i386-apple-macosx10.9','-x','assembler-with-cpp','-I',str(root)]
                if macro=='DARLING': args+=['-DDARLING=1']
                run(args+['-c',str(src),'-o',str(target)])
                artifacts[f'ldt-{kind}-{macro}']=target.read_bytes()
        if artifacts['ldt-original-DARLING']==artifacts['ldt-candidate-DARLING']:
            raise GateError('Darling LDT wrappers unchanged')
        if artifacts['ldt-original-NON_DARLING']!=artifacts['ldt-candidate-NON_DARLING']:
            raise GateError('non-Darling LDT wrappers changed')
        ldt_disasm=run(['llvm-objdump','--macho','--disassemble',
                        str(root/'candidate-DARLING.o')]).stdout
        if (ldt_disasm.count('calll\t__darling_machdep_syscall') != 2
            or len(re.findall(r'\tcmpl\s+\$0xfffff001, %eax', ldt_disasm)) != 2
            or len(re.findall(r'\tcmc\b', ldt_disasm)) != 2
            or len(re.findall(r'\tnegl\s+%eax', ldt_disasm)) != 2
            or len(re.findall(r'\tjmp\s+tramp_cerror', ldt_disasm)) != 2):
            raise GateError('Machdep LDT wrappers do not convert -errno to CF')
        disasm=run(['llvm-objdump','--macho','--disassemble',str(root/'candidate-i386.o')]).stdout
        if not re.search(r'andl\s+\$0xffff, %eax.*?movl\s+%eax, %edx.*?cmpl\s+\$0xa, %eax.*?jae\s+\.no_sys.*?movl',disasm,re.S):
            raise GateError('i386 Machdep disassembly lacks bounds guard')
        if not re.search(r'\.no_sys:.*?pushl\s+%edx',disasm,re.S):
            raise GateError('unknown Machdep call not receiving masked number')
        return {'patch':'PASS', 'macho_i386':'PASS','machdep_guard':'PASS','x86_64_unchanged':'PASS',
                'ldt_darling_changed':'PASS','ldt_nondarling_unchanged':'PASS',
                'source':'PINNED_FULL_XNU' if full else 'SELFTEST_FRAGMENTS'}


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--selftest',action='store_true')
    group.add_argument('--xnu',type=Path)
    args=p.parse_args()
    if shutil.which('clang') is None or shutil.which('llvm-objdump') is None:
        print('MACHDEP_GATE=BLOCKED_TOOLS')
        return 3
    try:
        sources=read_pinned(args.xnu) if args.xnu else {MACH:MACH_FIXTURE,GEN:LDT_FIXTURE,CUSTOM:LDT_FIXTURE}
        result=qualify(sources,full=bool(args.xnu))
    except (GateError, OSError, ValueError, subprocess.CalledProcessError) as e:
        print(f'MACHDEP_GATE=FAIL_OR_BLOCKED {e}')
        return 10
    for key,value in result.items():
        print(f'MACHDEP_{key.upper()}={value}')
    print('MACHDEP_GATE=PASS_FULL_PINNED' if args.xnu else 'MACHDEP_GATE=PASS_SELFTEST_ONLY')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
