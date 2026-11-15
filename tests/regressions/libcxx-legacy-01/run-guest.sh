#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Adapted from the qualified upstream-sync delegated-mapping runner.
set -Eeuo pipefail
test "$#" = 4 || { echo 'variant label program mode'; exit 2; }
H="${LIBCXX_LEGACY_STAGE:?}"
LIBROOT="${LIBCXX_LEGACY_LIBROOT:?}"
BIN="${LIBCXX_LEGACY_BIN:?}"
TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec 9>"$H/run.lock"
flock -n 9 || { echo 'BLOCKED: another qualification is active'; exit 2; }
Q="$(dirname "$H")/upstream-sync-20261114"
INST="$Q/build-core-i386/private-install"
variant="$1"; label="$2"; program="$3"; mode="$4"
case "$variant" in candidate|baseline) ;; *) exit 2;; esac
case "$label" in *[!A-Za-z0-9-]*|'') exit 2;; esac
case "$program" in
 valarray-size-i386|valarray-size-x86_64|legacy-i386|legacy-x86_64|bindings-i386|bindings-x86_64|shared-reset-i386|shared-reset-x86_64|weak-lock-i386|weak-lock-x86_64|weak-expired-i386|weak-expired-x86_64|bad-weak-ptr-i386|bad-weak-ptr-x86_64|function-copy-move-i386|function-copy-move-x86_64|generic-category-i386|generic-category-x86_64) executable="$BIN/$program";;
 *) exit 2;;
esac
case "$mode" in normal|bypass) ;; *) exit 2;; esac
test ! -e "$H/runs/$label"; test ! -e "$H/prefixes/$label"
mkdir "$H/runs/$label"
out="$H/runs/$label"
runtime="$H/runtime"
lib="$LIBROOT/$variant/libc++.1.dylib"
dest=libexec/darling/usr/lib/libc++.1.dylib
test -f "$runtime/$dest"; test -f "$lib"; test -x "$executable"
# The prefix overlay's lower directory must contain the actual selected file.
# A nested file bind over that lower directory is not visible through overlayfs.
cp -- "$lib" "$runtime/$dest"
subu=$(awk -F: -v u="$(id -un)" '$1==u{print $2":"$3}' /etc/subuid)
subg=$(awk -F: -v u="$(id -un)" '$1==u{print $2":"$3}' /etc/subgid)
test -n "$subu" && test -n "$subg"
subu_start=${subu%%:*}; subg_start=${subg%%:*}
sha=$(sha256sum "$lib" | cut -d' ' -f1)
{
  echo "variant=$variant label=$label mode=$mode"
  echo "library_sha256=$sha"
  echo "program_sha256=$(sha256sum "$executable" | cut -d' ' -f1)"
  echo "host_mounts_before=$(findmnt -rn | wc -l)"
  echo "darlingserver_before=$(pgrep -c -x darlingserver || true)"
  echo "start=$(date -Is)"
} > "$out/meta.txt"
set +e
env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME="$H/home" TMPDIR="$H/tmp" LANG=C.UTF-8 DYLD_PRINT_LIBRARIES=1 \
 timeout --signal=TERM --kill-after=3s 45s \
 unshare --user --map-users=0:$(id -u):1 --map-users=1:$subu_start:65536 \
 --map-groups=0:$(id -g):1 --map-groups=1:$subg_start:65536 --setgroups=allow \
 --mount --mount-proc --pid --fork --kill-child --ipc --uts --net \
 /bin/bash -c '
  set -Eeuo pipefail
  h="$1"; inst="$2"; lib="$3"; dest="$4"; sha="$5"; label="$6"; program="$7"; mode="$8"; probe="$9"; runtime="${10}"
  readlink /proc/self/ns/pid > "$h/runs/$label/pid-namespace"
  test "$(cat /proc/self/setgroups)" = allow
  echo "PREFLIGHT setgroups=$(cat /proc/self/setgroups)" >&2
  cat /proc/self/uid_map /proc/self/gid_map >&2
  "$probe" >&2
  mount --make-rprivate /
  mount -t tmpfs -o size=64m,mode=1777 tmpfs /tmp
  mkdir /tmp/p
  mount --bind "$h/prefixes" /tmp/p
  mount --bind "$runtime" "$inst"
  mount -o remount,bind,ro "$inst"
  got=$(sha256sum "$inst/$dest" | cut -d" " -f1)
  test "$got" = "$sha"
  echo "PREFLIGHT mounted_library_sha256=$got" >&2
  export DPREFIX="/tmp/p/$label"
  test ! -e "$DPREFIX"
  if test "$mode" = bypass; then export DSERVER_INIT=/usr/libexec/shellspawn; else unset DSERVER_INIT; fi
  ulimit -c 0
  echo "PREFLIGHT groups_darling=$(setpriv --groups=0 -- id -G)" >&2
  exec setpriv --groups=0 -- "$inst/bin/darling" exec "$program"
 ' home-res "$H" "$INST" "$lib" "$dest" "$sha" "$label" "$executable" "$mode" "$Q/g/tools/sgprobe" "$runtime" \
 </dev/null > "$out/stdout.log" 2> "$out/stderr.log"
rc=$?
set -e
python3 "$TOOLS/check-teardown.py" "$out"
{
  echo "rc=$rc"
  echo "end=$(date -Is)"
  echo "host_mounts_after=$(findmnt -rn | wc -l)"
  echo "darlingserver_after=$(pgrep -c -x darlingserver || true)"
} >> "$out/meta.txt"
echo "$rc" > "$out/rc"
printf 'LABEL=%s RC=%s\n' "$label" "$rc"
cat "$out/stdout.log"
exit 0
