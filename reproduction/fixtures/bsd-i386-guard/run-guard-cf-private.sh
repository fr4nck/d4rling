#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# BSD guard + CF mirror: candidate-only Mach-O i386 positive/mutant replay.
# No sudo, downloads, global mount changes, installation, or Git mutations.
set -Eeuo pipefail
umask 077
ulimit -c 0
export LC_ALL=C GIT_OPTIONAL_LOCKS=0 GIT_NO_LAZY_FETCH=1
export GIT_TERMINAL_PROMPT=0 PYTHONDONTWRITEBYTECODE=1
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR

HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
REPO=$(cd -- "$HERE/../../.." && pwd -P)
PATCH="$REPO/reproduction/patches/bsd-i386-dispatch-guard-nosys-ba34c8ac.patch"
HANDLERS="$REPO/reproduction/fixtures/bsd-i386-return/fixture.S"
REV=fa29287aa2f0115271e091f1031f53c9e024005d
A=darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/bsd_syscall.S
H=darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/bsd_syscall_table.h
C=darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/bsd_syscall_table.c
MLDR=libexec/darling/usr/libexec/darling/mldr32
DYLD=libexec/darling/usr/lib/dyld
KERNEL=libexec/darling/usr/lib/system/libsystem_kernel.dylib
SLOT=/opt/d4rling-qt-i386
blocked() { printf 'GUARD_CF_BLOCKED=%s\n' "$1" >&2; exit 3; }
MODE=${1:-}
[[ $# -eq 1 && ( "$MODE" == --check || "$MODE" == --run ) ]] || blocked USAGE
XNU=${BSD_GUARD_XNU:?Set BSD_GUARD_XNU to the pinned local XNU checkout}
LINKER=${BSD_GUARD_LINKER:?Set BSD_GUARD_LINKER to the existing cctools linker}
INSTALLATION=${BSD_GUARD_INSTALLATION:?Set BSD_GUARD_INSTALLATION to the FAT private installation}
B15=${BSD_GUARD_B15_UPPER:?Set BSD_GUARD_B15_UPPER to the qualified B15 d4/upper}
WORK_ROOT=${BSD_GUARD_WORK_ROOT:?Set BSD_GUARD_WORK_ROOT to a short existing ext4 directory}
CLANG=${BSD_GUARD_CLANG:-clang-19}

for cmd in git python3 file sha256sum cmp timeout unshare mount mktemp stat; do
    command -v "$cmd" >/dev/null || blocked "TOOL_$cmd"
done
command -v "$CLANG" >/dev/null || blocked CLANG
[[ $(id -u) -ne 0 ]] || blocked ROOT_USER
[[ -d "$XNU" && -d "$WORK_ROOT" && -d "$SLOT" ]] || blocked DIRECTORY
[[ -x "$LINKER" && -x "$INSTALLATION/bin/darling" ]] || blocked TOOLCHAIN
[[ -f "$INSTALLATION/libexec/darling/usr/lib/libSystem.B.dylib" ]] || blocked LIBSYSTEM
file -L "$INSTALLATION/libexec/darling/usr/lib/libSystem.B.dylib" | grep -qi i386 || blocked LIBSYSTEM_NO_I386
[[ ${#WORK_ROOT} -le 40 ]] || blocked WORK_ROOT_LONG
case "$(stat -f -c %T "$WORK_ROOT")" in ext4|ext2/ext3) ;; *) blocked WORK_ROOT_FS ;; esac
[[ "$(git hash-object "$PATCH")" == 15fe7c455313a2160120f8193d69892824e1e4d9 ]] || blocked PATCH_BLOB
[[ "$(git hash-object "$HANDLERS")" == 620a192308c58a39bdbb0e26edbe69ba836c08c5 ]] || blocked HANDLERS_BLOB
for entry in \
    'a26ae39ccc83de68afede4143861d7c63612b210:darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/bsd_syscall.S' \
    'a52497e33703b8cecfd41796bb498f1f5bbdc78c:darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/bsd_syscall_table.h' \
    '7d5ef80e0a488d2564079260d2d6624a9fb359ed:darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/bsd_syscall_table.c'
do
    expected=${entry%%:*}
    rel=${entry#*:}
    [[ $(git -C "$XNU" rev-parse "$REV:$rel") == "$expected" ]] || blocked XNU_BLOB
 done
for entry in \
    '599bb14c0e264c972631f689de15bed64183460f36583aaa431c97e44d441bb7:libexec/darling/usr/libexec/darling/mldr32' \
    '81c1c0a85b362e970130fb6181d88fc8a75e3a05e105f7e2b05f35ab18e0572d:libexec/darling/usr/lib/dyld' \
    '33a47b0e56d4e44e9b5aa6778f009b00d6eb51aae7a790e5ba864aafb7bd1b1d:libexec/darling/usr/lib/system/libsystem_kernel.dylib'
do
    expected=${entry%%:*}
    rel=${entry#*:}
    printf '%s  %s\n' "$expected" "$B15/$rel" | sha256sum -c --status - || blocked B15_HASH
 done
for entry in \
    'c9eb682cd66af5505827108645c6d692d2f27b0759de9a5cc702f70619bf45f1:fixture-cf-i386.S' \
    '76ce8178ac2e3d7ea0d8e7afad94fde324ef6bdfeae10d9fb29fa9a03b4c5b1d:probe-cf.c' \
    'a6b7c760ded2de4d012207088225585310f23e26466e266ce3fecb7e7c9248e9:verify_guard_cf.py'
do
    expected=${entry%%:*}
    rel=${entry#*:}
    printf '%s  %s\n' "$expected" "$HERE/$rel" | sha256sum -c --status - || blocked "WITNESS_HASH_$rel"
 done
printf 'GUARD_CF_PREFLIGHT=PASS\n'
[[ "$MODE" == --run ]] || exit 0

R=$(mktemp -d "$WORK_ROOT/gcf-i1.XXXXXXXX")
printf 'RESULT_DIR=%s\n' "$R"
[[ ${#R} -le 57 ]] || blocked RESULT_PATH
mkdir -p "$R/source" "$R/include/darling/emulation/xnu_syscall/bsd"
for rel in "$A" "$H" "$C"; do
    mkdir -p "$R/source/$(dirname "$rel")"
    git -C "$XNU" show "$REV:$rel" > "$R/source/$rel"
 done
(cd "$R/source" && git apply --check -- "$PATCH" && git apply -- "$PATCH")
cp -- "$R/source/$H" "$R/include/darling/emulation/xnu_syscall/bsd/bsd_syscall_table.h"
printf 'GUARD_CF_PRIVATE_PATCH=PASS\n'
FLAGS=(-target i386-apple-macosx10.6 -I "$R/include")
NAMES=(-D__darling_bsd_syscall=__fixture_bsd_syscall
       -D___bsd_syscall_table=___fixture_bsd_table
       -D___unknown_syscall=___fixture_unknown_syscall
       -D__darling_bsd_syscall_entry=__fixture_bsd_syscall_entry
       -D__darling_bsd_syscall_exit=__fixture_bsd_syscall_exit)
"$CLANG" "${FLAGS[@]}" -nostdinc -fno-builtin -fno-stack-protector \
    -O1 -Wall -Wextra -Werror -c "$HERE/probe-cf.c" -o "$R/probe.o"
"$CLANG" "${FLAGS[@]}" -c "$HANDLERS" -o "$R/handlers.o"
"$CLANG" "${FLAGS[@]}" "${NAMES[@]}" -c "$R/source/$A" -o "$R/dispatch.o"
for case in positive mutant; do
    extra=()
    [[ "$case" == positive ]] || extra=(-DGUARD_CF_MUTANT_NO_CMC=1)
    "$CLANG" "${FLAGS[@]}" "${extra[@]}" -c "$HERE/fixture-cf-i386.S" -o "$R/fixture-$case.o"
    "$LINKER" -arch i386 -macosx_version_min 10.9 \
        -syslibroot "$INSTALLATION/libexec/darling" \
        -L "$INSTALLATION/libexec/darling/usr/lib" \
        -e _main -no_pie -seg1addr 0x10000000 \
        -o "$R/probe-$case" "$R/probe.o" "$R/handlers.o" \
        "$R/dispatch.o" "$R/fixture-$case.o" -lSystem \
        > "$R/$case.link.log" 2>&1 || {
            tail -n 30 "$R/$case.link.log" >&2
            blocked "LINK_$case"
        }
    file -b "$R/probe-$case" | grep -qi 'Mach-O.*i386' || blocked MACHO_FORMAT
 done
printf 'GUARD_CF_MACHO_BUILD=PASS\n'
for case in positive mutant; do
    mkdir -m 700 "$R/$case" "$R/$case/lower" "$R/$case/upper" "$R/$case/work"
    for rel in "$MLDR" "$DYLD" "$KERNEL"; do
        mkdir -p "$R/$case/upper/$(dirname "$rel")"
        cp --preserve=mode -- "$B15/$rel" "$R/$case/upper/$rel"
        cmp -- "$B15/$rel" "$R/$case/upper/$rel"
    done
 done
printf 'GUARD_CF_PRIVATE_OVERLAYS=PASS\n'

for case in positive mutant; do
    set +e
    timeout --signal=TERM --kill-after=10s 75s \
      unshare --user --map-root-user --mount --mount-proc \
        --pid --fork --kill-child --ipc --uts --net \
      /bin/bash -s -- "$R" "$case" "$INSTALLATION" "$SLOT" \
      > "$R/$case.stdout.log" 2> "$R/$case.stderr.log" <<'WORKER'
set -Eeuo pipefail
umask 077
ulimit -c 0
R=$1
CASE=$2
P=$3
SLOT=$4
mount --make-rprivate /
mount --bind "$P" "$R/$CASE/lower"
mount -o remount,bind,ro "$R/$CASE/lower"
mount -t overlay overlay \
  -o "lowerdir=$R/$CASE/lower,upperdir=$R/$CASE/upper,workdir=$R/$CASE/work" \
  "$SLOT"
[[ $(stat -f -c %T "$SLOT") == overlayfs ]]
for entry in \
    '599bb14c0e264c972631f689de15bed64183460f36583aaa431c97e44d441bb7:libexec/darling/usr/libexec/darling/mldr32' \
    '81c1c0a85b362e970130fb6181d88fc8a75e3a05e105f7e2b05f35ab18e0572d:libexec/darling/usr/lib/dyld' \
    '33a47b0e56d4e44e9b5aa6778f009b00d6eb51aae7a790e5ba864aafb7bd1b1d:libexec/darling/usr/lib/system/libsystem_kernel.dylib'
do
    expected=${entry%%:*}
    rel=${entry#*:}
    printf '%s  %s\n' "$expected" "$SLOT/$rel" | sha256sum -c --status -
 done
printf 'B15_ACTIVE_HASHES=PASS\n'
export DPREFIX="$R/p-$CASE"
[[ ${#DPREFIX} -le 75 ]]
unset DSERVER_INIT
set +e
"$SLOT/bin/darling" exec "$R/probe-$CASE"
RC=$?
set -e
printf 'GUARD_CF_EXIT=%d\n' "$RC"
exit "$RC"
WORKER
    rc=$?
    set -e
    printf '%s\n' "$rc" > "$R/$case.exit-code.txt"
    printf 'GUARD_CF_CASE=%s RC=%s\n' "$case" "$rc"
    tail -n 3 "$R/$case.stdout.log"
 done
(cd "$R" && sha256sum positive.stdout.log positive.stderr.log \
    mutant.stdout.log mutant.stderr.log probe-positive probe-mutant > SHA256SUMS)
(cd "$R" && sha256sum -c --status SHA256SUMS) || blocked MANIFEST
python3 "$HERE/verify_guard_cf.py" "$R"
