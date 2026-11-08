#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -Eeuo pipefail
# Run from tests/bsd-i386-return of the independent candidate tree.
testdir=$(cd -- "$(dirname -- "$0")" && pwd)
candidate=$(cd -- "$testdir/../.." && pwd)
work=$(cd -- "$candidate/.." && pwd)
original=$work/original
em=darling/src/libsystem_kernel/emulation
asm=$em/src/xnu_syscall/bsd/bsd_syscall.S
header=$em/include/xnu_syscall/bsd/bsd_syscall_table.h
sdk=${BSD_SDK:?Set BSD_SDK to an existing SDK}
linker=${BSD_LINKER:?Set BSD_LINKER to an existing Darling cctools linker}
installation=${BSD_INSTALLATION:?Set BSD_INSTALLATION to a coherent existing private installation}
results=$(mktemp -d "$work/results.XXXXXXXX")
printf '%s\n' "$results" > "$work/LAST_RESULTS.txt"
prefixroot=$(mktemp -d "$work/p.XXXX")
printf '%s\n' "$prefixroot" > "$results/PREFIX_ROOT.txt"
mkdir -p "$results/include/darling/emulation/xnu_syscall/bsd"
cp "$candidate/$header" "$results/include/darling/emulation/xnu_syscall/bsd/bsd_syscall_table.h"
flags=(-target i386-apple-macosx10.6 -isysroot "$sdk" -I "$results/include")
names=(-D__darling_bsd_syscall=__fixture_bsd_syscall -D___bsd_syscall_table=___fixture_bsd_table -D___unknown_syscall=___fixture_unknown_syscall -D__darling_bsd_syscall_entry=__fixture_bsd_syscall_entry -D__darling_bsd_syscall_exit=__fixture_bsd_syscall_exit)
clang-19 "${flags[@]}" -O2 -Wall -Wextra -Werror -c "$testdir/probe.c" -o "$results/probe.o"
clang-19 "${flags[@]}" -c "$testdir/fixture.S" -o "$results/fixture.o"
for variant in original candidate; do
    clang-19 "${flags[@]}" "${names[@]}" -c "$work/$variant/$asm" -o "$results/$variant.o"
    "$linker" -arch i386 -macosx_version_min 10.9 -syslibroot "$installation/libexec/darling" -e _main -no_pie -seg1addr 0x10000000 \
        -o "$results/probe-$variant" "$results/probe.o" "$results/fixture.o" "$results/$variant.o" -lSystem
    llvm-objdump-19 --macho --disassemble "$results/$variant.o" > "$results/$variant.disassembly.txt"
    clang-19 -target x86_64-apple-macosx10.6 -c "$work/$variant/$asm" -o "$results/$variant-x86_64.o"
done
cmp "$results/original-x86_64.o" "$results/candidate-x86_64.o"
printf 'X86_64_OBJECT_IDENTICAL=PASS\n'
# Countercheck: a deliberately broken variant classifies only EAX, like B7.
python3 - "$candidate/$asm" "$results/low-word-only.S" <<'PY'
import pathlib,sys
source=pathlib.Path(sys.argv[1]).read_text()
old='\tcmpl\t$-1, %edx\n\tjne\t\t.ret_success\n'
assert source.count(old)==1
pathlib.Path(sys.argv[2]).write_text(source.replace(old,''))
PY
clang-19 "${flags[@]}" "${names[@]}" -c "$results/low-word-only.S" -o "$results/low-word-only.o"
"$linker" -arch i386 -macosx_version_min 10.9 -syslibroot "$installation/libexec/darling" -e _main -no_pie -seg1addr 0x10000000 \
    -o "$results/probe-low-word-only" "$results/probe.o" "$results/fixture.o" "$results/low-word-only.o" -lSystem
file "$results"/probe-original "$results"/probe-candidate
for label in original candidate1 low-word-only candidate2; do
    executable=$results/probe-candidate
    extra=()
    case "$label" in
        original) executable=$results/probe-original; extra=(--baseline);;
        low-word-only) executable=$results/probe-low-word-only;;
    esac
    set +e
    timeout --kill-after=10s 75s unshare --user --map-root-user --mount --pid --fork --ipc --uts --net --mount-proc \
        bash "$testdir/run-private.sh" "$installation" "$prefixroot" "$label" "$executable" "${extra[@]}" \
        > "$results/$label.stdout.log" 2> "$results/$label.stderr.log"
    rc=$?
    set -e
    printf '%s\n' "$rc" > "$results/$label.exit-code.txt"
    printf '%s: rc=%s\n' "$label" "$rc"
    tail -4 "$results/$label.stdout.log"
done
python3 - "$results" <<'PY'
import json,pathlib,re,struct,sys
root=pathlib.Path(sys.argv[1]); runs=[]
for label in ['original','candidate1','low-word-only','candidate2']:
    output=(root/f'{label}.stdout.log').read_text()
    rc=int((root/f'{label}.exit-code.txt').read_text())
    matches=re.findall(r'FIXTURE_CHECKS=(\d+) FIXTURE_ERRORS=(\d+) THREAD_CALLS=(\d+)',output)
    assert len(matches)==1 and 'FIXTURE_FINISHED' in output, f'Fixture did not finish: {label}'
    checks,errors,thread_calls=map(int,matches[0])
    assert checks>82000 and thread_calls==8000
    expected_failure=label in ['original','low-word-only']
    assert (rc==10 and errors>0) if expected_failure else (rc==0 and errors==0), (label,rc,errors)
    runs.append(dict(label=label,exit_code=rc,checks=checks,errors=errors,thread_calls=thread_calls))
for variant in ['original','candidate','low-word-only']:
    magic,cpu=struct.unpack('<II',(root/f'probe-{variant}').read_bytes()[:8])
    assert magic==0xfeedface and cpu==7
result=dict(all_checks_passed=True,fixture='real source dispatcher compiled into private Mach-O i386 executable with synthetic handlers',
            x86_64_object_identical=True,runs=runs)
(root/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('SOURCE_RETURN_PROTOCOL=PASS')
PY
