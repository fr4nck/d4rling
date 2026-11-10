#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Bounded Darwin i386 guest test for -errno -> carry conversion.
# No network, sudo, git mutation, or modifications to Darling installations.
set -Eeuo pipefail
umask 077
ulimit -c 0
export LC_ALL=C

HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
ROOT=/home/Deniel/d4wrling-work
B="$ROOT/L1-CANON-20261108T2019Z/build-core-i386"
L="$B/src/external/cctools-port/cctools/ld64/src/x86_64-apple-darwin20-ld"
P=/home/Deniel/d4rling-qt432-438-rRJ1fhT1/installation
B15="$ROOT/validation/bsd-i386/integration-b15-a7/d4/upper"
SLOT=/opt/d4rling-qt-i386
MLDR=libexec/darling/usr/libexec/darling/mldr32
DYLD=libexec/darling/usr/lib/dyld
KERNEL=libexec/darling/usr/lib/system/libsystem_kernel.dylib
blocked() { printf 'STUB_CF_GUEST_BLOCKED=%s\n' "$1" >&2; exit 3; }

[[ $(id -u) -ne 0 ]] || blocked ROOT_USER
for cmd in clang-19 sha256sum file unshare mount timeout mktemp cmp; do
    command -v "$cmd" >/dev/null || blocked "TOOL_$cmd"
done
[[ -x "$L" && -x "$P/bin/darling" && -d "$SLOT" ]] || blocked TOOLCHAIN
[[ -d "$ROOT" && $(stat -f -c %T "$ROOT") == ext4 ]] || blocked WORK_ROOT
for entry in \
    'c866e96ecede4bf84baf4aca4a98af8eb2668a9392391a32829c38562671550e:stub-cf-i386.S' \
    '4e452cbc4ecd55c0356fa93671324d9ad1de1dd9a8be22b63c73e1448d4fc3b1:stub-cf-capture-i386.S' \
    'c189cc6a5ebedaac70d93da56683d7370da00504737efdf222c98e21ab189f20:stub-cf-guest.c'
do
    hash=${entry%%:*}
    name=${entry#*:}
    [[ -f "$HERE/$name" ]] || blocked "SOURCE_$name"
    printf '%s  %s\n' "$hash" "$HERE/$name" | sha256sum -c --status - || blocked "SOURCE_HASH_$name"
done
for entry in \
    "599bb14c0e264c972631f689de15bed64183460f36583aaa431c97e44d441bb7:$MLDR" \
    "81c1c0a85b362e970130fb6181d88fc8a75e3a05e105f7e2b05f35ab18e0572d:$DYLD" \
    "33a47b0e56d4e44e9b5aa677f009b00d6eb51aae7a790e5ba864aafb7bd1b1d:$KERNEL"
do
    hash=${entry%%:*}
    name=${entry#*:}
    printf '%s  %s\n' "$hash" "$B15/$name" | sha256sum -c --status - || blocked "B15_HASH_$name"
done
printf 'STUB_CF_GUEST_PREFLIGHT=PASS\n'
R=$(mktemp -d "$ROOT/bsd-cf-guest.XXXXXXXX")
printf 'RESULT_DIR=%s\n' "$R"
[[ ${#R} -le 63 ]] || blocked RESULT_DIR_TOO_LONG
flags=(-target i386-apple-macosx10.9)
clang-19 "${flags[@]}" -c "$HERE/stub-cf-i386.S" -o "$R/convert.o"
clang-19 "${flags[@]}" -c "$HERE/stub-cf-capture-i386.S" -o "$R/capture.o"
clang-19 "${flags[@]}" -nostdinc -fno-builtin -fno-stack-protector \
    -O1 -Wall -Wextra -Werror -c "$HERE/stub-cf-guest.c" -o "$R/guest.o"
"$L" -arch i386 -macosx_version_min 10.9 \
    -syslibroot "$P/libexec/darling" \
    -L "$P/libexec/darling/usr/lib" -e _main -no_pie -seg1addr 0x10000000 \
    -o "$R/stub-cf-guest" "$R/convert.o" "$R/capture.o" "$R/guest.o" \
    -lSystem > "$R/link.log" 2>&1 || {
        tail -n 30 "$R/link.log" >&2
        blocked MACHO_LINK
    }
file "$R/stub-cf-guest"
file -b "$R/stub-cf-guest" | grep -qi 'Mach-O.*i386' || blocked MACHO_FORMAT
printf 'STUB_CF_GUEST_LINK=PASS\n'
mkdir -m 700 "$R/lower" "$R/upper" "$R/work"
for name in "$MLDR" "$DYLD" "$KERNEL"; do
    mkdir -p "$R/upper/$(dirname "$name")"
    cp --preserve=mode -- "$B15/$name" "$R/upper/$name"
    cmp -- "$B15/$name" "$R/upper/$name"
done
printf 'STUB_CF_GUEST_PRIVATE_COPIES=PASS\n'
set +e
timeout --signal=TERM --kill-after=10s 75s \
    unshare --user --map-root-user --mount --mount-proc \
        --pid --fork --kill-child --ipc --uts --net \
    /bin/bash -s -- "$R" "$P" "$SLOT" \
    > "$R/guest.stdout.log" 2> "$R/guest.stderr.log" <<'WORKER'
set -Eeuo pipefail
umask 077
ulimit -c 0
R=$1
P=$2
SLOT=$3
mount --make-rprivate /
mount --bind "$P" "$R/lower"
mount -o remount,bind,ro "$R/lower"
mount -t overlay overlay \
    -o "lowerdir=$R/lower,upperdir=$R/upper,workdir=$R/work" \
    "$SLOT"
[[ $(stat -f -c %T "$SLOT") == overlayfs ]]
for entry in \
    '599bb14c0e264c972631f689de15bed64183460f36583aaa431c97e44d441bb7:libexec/darling/usr/libexec/darling/mldr32' \
    '81c1c0a85b362e970130fb6181d88fc8a75e3a05e105f7e2b05f35ab18e0572d:libexec/darling/usr/lib/dyld' \
    '33a47b0e56d4e44e9b5aa677f009b00d6eb51aae7a790e5ba864aafb7bd1b1d:libexec/darling/usr/lib/system/libsystem_kernel.dylib'
do
    hash=${entry%%:*}
    name=${entry#*:}
    printf '%s  %s\n' "$hash" "$SLOT/$name" | sha256sum -c --status -
done
printf 'B15_ACTIVE_HASHES=PASS\n'
export DPREFIX="$R/p-cf"
[[ ${#DPREFIX} -le 75 ]]
unset DSERVER_INIT
set +e
"$SLOT/bin/darling" exec "$R/stub-cf-guest"
RC=$?
set -e
printf 'STUB_CF_GUEST_EXIT=%d\n' "$RC"
exit "$RC"
WORKER
RC=$?
set -e
printf 'GUEST_RC=%d\n' "$RC"
printf '%s\n' '=== GUEST STDOUT ==='
tail -n 25 "$R/guest.stdout.log"
printf '%s\n' '=== GUEST STDERR ==='
tail -n 15 "$R/guest.stderr.log"
sha256sum "$R/stub-cf-guest" "$R/guest.stdout.log" "$R/guest.stderr.log" > "$R/SHA256SUMS"
if [[ "$RC" -eq 0 ]] && \
   grep -Fxq 'B15_ACTIVE_HASHES=PASS' "$R/guest.stdout.log" && \
   grep -Fxq 'STUB_CF_GUEST_CHECKS=12 FAILURES=0' "$R/guest.stdout.log" && \
   grep -Fxq 'STUB_CF_GUEST_FINISHED' "$R/guest.stdout.log" && \
   grep -Fxq 'STUB_CF_GUEST_EXIT=0' "$R/guest.stdout.log"; then
    printf 'STUB_CF_GUEST_RUNTIME=PASS_BOUNDED\n'
else
    printf 'STUB_CF_GUEST_RUNTIME=NOT_QUALIFIED\n'
fi
printf 'RESULT_DIR=%s\n' "$R"
