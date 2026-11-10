#!/usr/bin/env bash
# BSD i386 guard: reproduce a bounded, synthetic Mach-O fixture in private mounts.
# Never mutates the checkout, historical installations, or B15 evidence.
set -Eeuo pipefail
umask 077
ulimit -c 0
export LC_ALL=C
export GIT_OPTIONAL_LOCKS=0 GIT_NO_LAZY_FETCH=1 GIT_TERMINAL_PROMPT=0
export PYTHONDONTWRITEBYTECODE=1
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR

HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
REPO=$(cd -- "$HERE/../../.." && pwd -P)
PATCH="$REPO/reproduction/patches/bsd-i386-dispatch-guard-nosys-ba34c8ac.patch"
FIXTURE="$REPO/reproduction/fixtures/bsd-i386-return/fixture.S"
REV=fa29287aa2f0115271e091f1031f53c9e024005d
A=darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/bsd_syscall.S
H=darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/bsd_syscall_table.h
C=darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/bsd_syscall_table.c
MLDR=libexec/darling/usr/libexec/darling/mldr32
DYLD=libexec/darling/usr/lib/dyld
KERNEL=libexec/darling/usr/lib/system/libsystem_kernel.dylib
MLDR_SHA=599bb14c0e264c972631f689de15bed64183460f36583aaa431c97e44d441bb7
DYLD_SHA=81c1c0a85b362e970130fb6181d88fc8a75e3a05e105f7e2b05f35ab18e0572d
KERNEL_SHA=33a47b0e56d4e44e9b5aa6778f009b00d6eb51aae7a790e5ba864aafb7bd1b1d
SLOT=/opt/d4rling-qt-i386

fail() { printf 'GUARD_BLOCKED=%s\n' "$1" >&2; exit 3; }
mode=${1:-}
[[ $# -eq 1 && ( "$mode" == '--check' || "$mode" == '--run' ) ]] || fail USAGE_CHECK_OR_RUN

# All paths are supplied by the operator; there are no downloads, sudo, git
# updates, or writes outside a newly allocated qualification directory.
XNU=${BSD_GUARD_XNU:?Set BSD_GUARD_XNU to the pinned local XNU checkout}
LINKER=${BSD_GUARD_LINKER:?Set BSD_GUARD_LINKER to the existing cctools linker}
INSTALLATION=${BSD_GUARD_INSTALLATION:?Set BSD_GUARD_INSTALLATION to a private FAT installation}
B15=${BSD_GUARD_B15_UPPER:?Set BSD_GUARD_B15_UPPER to a qualified B15 d4/upper directory}
WORK_ROOT=${BSD_GUARD_WORK_ROOT:?Set BSD_GUARD_WORK_ROOT to an existing short WSL ext4 directory}
CLANG=${BSD_GUARD_CLANG:-clang-19}

for tool in git python3 file sha256sum cmp timeout unshare mount stat mktemp; do
    command -v "$tool" >/dev/null || fail "TOOL_$tool"
done
command -v "$CLANG" >/dev/null || fail CLANG_MISSING
[[ $(id -u) -ne 0 ]] || fail ROOT_USER_NOT_ALLOWED
[[ -d "$XNU" && -d "$WORK_ROOT" && -d "$SLOT" ]] || fail DIRECTORY_MISSING
[[ -x "$LINKER" && -x "$INSTALLATION/bin/darling" ]] || fail TOOLCHAIN_MISSING
[[ -s "$PATCH" && -s "$FIXTURE" && -s "$HERE/probe.c" ]] || fail SOURCES_MISSING
[[ -f "$INSTALLATION/libexec/darling/usr/lib/libSystem.B.dylib" ]] || fail LIBSYSTEM_MISSING
file -L "$INSTALLATION/libexec/darling/usr/lib/libSystem.B.dylib" | grep -q i386 || fail LIBSYSTEM_NOT_I386
[[ "$(git hash-object "$PATCH")" == 15fe7c455313a2160120f8193d69892824e1e4d9 ]] || fail PATCH_BLOB
[[ "$(git hash-object "$FIXTURE")" == 620a192308c58a39bdbb0e26edbe69ba836c08c5 ]] || fail FIXTURE_BLOB
[[ "$(git -C "$XNU" rev-parse "$REV^{commit}")" == "$REV" ]] || fail XNU_REVISION

for ENTRY in \
    "a26ae39ccc83de68afede4143861d7c63612b210:$A" \
    "a52497e33703b8cecfd41796bb498f1f5bbdc78c:$H" \
    "7d5ef80e0a488d2564079260d2d6624a9fb359ed:$C"
do
    SHA=${ENTRY%%:*}
    REL=${ENTRY#*:}
    [[ "$(git -C "$XNU" rev-parse "$REV:$REL")" == "$SHA" ]] || fail XNU_BLOB
 done
for ENTRY in \
    "$MLDR_SHA:$MLDR" \
    "$DYLD_SHA:$DYLD" \
    "$KERNEL_SHA:$KERNEL"
do
    SHA=${ENTRY%%:*}
    REL=${ENTRY#*:}
    printf '%s  %s\n' "$SHA" "$B15/$REL" | sha256sum -c --status - || fail B15_HASH
 done
case "$(stat -f -c %T "$WORK_ROOT")" in ext4|ext2/ext3) ;; *) fail WORK_ROOT_NOT_EXT4 ;; esac
[[ ${#WORK_ROOT} -le 40 ]] || fail WORK_ROOT_PATH_TOO_LONG
printf 'GUARD_PREFLIGHT=PASS\n'
[[ "$mode" == '--run' ]] || exit 0

R=$(mktemp -d "$WORK_ROOT/guard-r.XXXXXXXX")
printf 'RESULT_DIR=%s\n' "$R"
[[ ${#R} -le 57 ]] || fail RESULT_PATH_TOO_LONG
mkdir -p "$R/source/original" "$R/source/candidate" \
    "$R/include/darling/emulation/xnu_syscall/bsd"
for REL in "$A" "$H" "$C"; do
    mkdir -p "$R/source/original/$(dirname "$REL")" \
             "$R/source/candidate/$(dirname "$REL")"
    git -C "$XNU" show "$REV:$REL" > "$R/source/original/$REL"
    cp -- "$R/source/original/$REL" "$R/source/candidate/$REL"
 done
(
    cd "$R/source/candidate"
    git apply --check -- "$PATCH"
    git apply -- "$PATCH"
)
cp -- "$R/source/candidate/$H" \
      "$R/include/darling/emulation/xnu_syscall/bsd/bsd_syscall_table.h"
[[ $(grep -c 'BSD_SYSCALL_TABLE_SIZE 600' "$R/source/candidate/$H") -eq 1 ]] || fail TABLE_CONSTANT
printf 'GUARD_PATCH_PRIVATE=PASS\n'

FLAGS=(-target i386-apple-macosx10.6 -I "$R/include")
NAMES=(-D__darling_bsd_syscall=__fixture_bsd_syscall
       -D___bsd_syscall_table=___fixture_bsd_table
       -D___unknown_syscall=___fixture_unknown_syscall
       -D__darling_bsd_syscall_entry=__fixture_bsd_syscall_entry
       -D__darling_bsd_syscall_exit=__fixture_bsd_syscall_exit)
"$CLANG" "${FLAGS[@]}" -nostdinc -fno-builtin -fno-stack-protector \
    -O1 -Wall -Wextra -Werror -c "$HERE/probe.c" -o "$R/probe.o"
"$CLANG" "${FLAGS[@]}" -c "$FIXTURE" -o "$R/fixture.o"
for VAR in original candidate; do
    "$CLANG" "${FLAGS[@]}" "${NAMES[@]}" \
        -c "$R/source/$VAR/$A" -o "$R/$VAR.o"
    "$LINKER" -arch i386 -macosx_version_min 10.9 \
        -syslibroot "$INSTALLATION/libexec/darling" \
        -L "$INSTALLATION/libexec/darling/usr/lib" \
        -e _main -no_pie -seg1addr 0x10000000 \
        -o "$R/probe-$VAR" "$R/probe.o" "$R/fixture.o" "$R/$VAR.o" \
        -lSystem > "$R/$VAR.link.log" 2>&1 || {
            tail -n 25 "$R/$VAR.link.log" >&2
            fail "LINK_$VAR"
        }
    file -b "$R/probe-$VAR" | grep -qi 'Mach-O.*i386' || fail "MACHO_$VAR"
 done
printf 'GUARD_FIXTURE_BUILD=PASS\n'

for VAR in original candidate; do
    mkdir -m 700 "$R/$VAR" "$R/$VAR/lower" "$R/$VAR/upper" "$R/$VAR/work"
    for REL in "$MLDR" "$DYLD" "$KERNEL"; do
        mkdir -p "$R/$VAR/upper/$(dirname "$REL")"
        cp --preserve=mode -- "$B15/$REL" "$R/$VAR/upper/$REL"
        cmp -- "$B15/$REL" "$R/$VAR/upper/$REL"
    done
 done
printf 'GUARD_PRIVATE_OVERLAYS=PASS\n'

for VAR in original candidate; do
    set +e
    timeout --signal=TERM --kill-after=10s 75s \
        unshare --user --map-root-user --mount --mount-proc \
          --pid --fork --kill-child --ipc --uts --net \
        /bin/bash -s -- "$R" "$VAR" "$INSTALLATION" "$SLOT" \
        > "$R/$VAR.stdout.log" 2> "$R/$VAR.stderr.log" <<'WORKER'
set -Eeuo pipefail
umask 077
ulimit -c 0
R=$1
VAR=$2
P=$3
SLOT=$4
mount --make-rprivate /
mount --bind "$P" "$R/$VAR/lower"
mount -o remount,bind,ro "$R/$VAR/lower"
mount -t overlay overlay \
    -o "lowerdir=$R/$VAR/lower,upperdir=$R/$VAR/upper,workdir=$R/$VAR/work" \
    "$SLOT"
[[ $(stat -f -c %T "$SLOT") == overlayfs ]]
for ENTRY in \
    "599bb14c0e264c972631f689de15bed64183460f36583aaa431c97e44d441bb7:libexec/darling/usr/libexec/darling/mldr32" \
    "81c1c0a85b362e970130fb6181d88fc8a75e3a05e105f7e2b05f35ab18e0572d:libexec/darling/usr/lib/dyld" \
    "33a47b0e56d4e44e9b5aa6778f009b00d6eb51aae7a790e5ba864aafb7bd1b1d:libexec/darling/usr/lib/system/libsystem_kernel.dylib"
do
    SHA=${ENTRY%%:*}
    REL=${ENTRY#*:}
    printf '%s  %s\n' "$SHA" "$SLOT/$REL" | sha256sum -c --status -
 done
printf 'B15_ACTIVE_HASHES=PASS\n'
export DPREFIX="$R/p-$VAR"
[[ ${#DPREFIX} -le 75 ]]
unset DSERVER_INIT
set +e
if [[ "$VAR" == original ]]; then
    "$SLOT/bin/darling" exec "$R/probe-$VAR" --baseline
else
    "$SLOT/bin/darling" exec "$R/probe-$VAR"
fi
RC=$?
set -e
printf 'FIXTURE_EXIT=%d\n' "$RC"
exit "$RC"
WORKER
    RC=$?
    set -e
    printf '%s\n' "$RC" > "$R/$VAR.exit-code.txt"
    printf 'RUNTIME_CASE=%s RC=%d\n' "$VAR" "$RC"
    tail -n 5 "$R/$VAR.stdout.log"
    tail -n 3 "$R/$VAR.stderr.log" >&2
 done
sha256sum "$R/probe-original" "$R/probe-candidate" \
    "$R/original.stdout.log" "$R/candidate.stdout.log" \
    "$R/original.stderr.log" "$R/candidate.stderr.log" \
    > "$R/SHA256SUMS"
sha256sum -c --status "$R/SHA256SUMS"
printf 'GUARD_MANIFEST=PASS\n'
python3 "$HERE/verify_guard.py" "$R"
