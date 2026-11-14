#!/usr/bin/env bash
# Isolated Darling guest run for the BSD i386 probe (rootless, delegated ids).
#
# Bench: unshare with delegated UID/GID mappings (uidmap: newuidmap/newgidmap and
# a range in /etc/subuid and /etc/subgid), setgroups allowed and checked by a real
# setgroups() call before Darling starts; private mount/pid/ipc/uts/net namespaces;
# the installation is bind-mounted read-only; one fresh prefix per run.
#
# The darling launcher and darlingserver use their compiled-in install prefix, so a
# copied installation still runs the original one. To substitute files (patched
# libsystem_kernel.dylib or dyld), LAYER names a directory laid out like
# INST/libexec/darling; it is mounted as a read-only OverlayFS lower layer over
# INST/libexec/darling inside the private mount namespace only. The SHA-256 seen
# inside the namespace is logged (PREFLIGHT ns_kernel / ns_dyld).
#
# Environment:
#   INST         Darling installation prefix (required)
#   LAYER        optional overlay layer directory
#   SGPROBE      setgroups-probe binary from build-probe.sh (required)
#   OUT_ROOT     directory for run records (required)
#   PREFIX_ROOT  directory for guest prefixes (required; keep it short: older
#                launchers fail with long prefix paths, see the report)
# Usage: run-guest.sh LABEL PROGRAM normal|bypass TIMEOUT_SECONDS [PROGRAM_ARGS...]
# The guest environment carries BM4_ENV_TOKEN=BM4_VALUE (B15 BM4 fixture contract).
set -Eeuo pipefail
test "$#" -ge 4 || { echo "usage: run-guest.sh LABEL PROGRAM normal|bypass TIMEOUT [ARGS...]" >&2; exit 2; }
: "${INST:?INST is required}" "${SGPROBE:?SGPROBE is required}" "${OUT_ROOT:?OUT_ROOT is required}" "${PREFIX_ROOT:?PREFIX_ROOT is required}"
LAYER="${LAYER:-}"
[ -z "$LAYER" ] || test -d "$LAYER"
PROBE="$(realpath "$SGPROBE")"; test -x "$PROBE"
which_inst="$INST"
subu=$(awk -F: -v u="$(id -un)" '$1==u{print $2":"$3}' /etc/subuid); subg=$(awk -F: -v u="$(id -un)" '$1==u{print $2":"$3}' /etc/subgid)
test -n "$subu" && test -n "$subg"
subu_start=${subu%%:*}; subg_start=${subg%%:*}
mkdir -p "$OUT_ROOT/home" "$OUT_ROOT/tmp"
R0="$(realpath "$OUT_ROOT")"
label="$1"; prog="$(realpath "$2")"; mode="$3"; secs="$4"; shift 4; pargs=("$@")
case "$label" in *[!A-Za-z0-9-]*|'') exit 2;; esac
case "$mode" in normal|bypass) ;; *) exit 2;; esac
case "$secs" in ''|*[!0-9]*) exit 2;; esac
test -x "$INST/bin/darling"; test -x "$prog"
out="$R0/$label"; prefix="$(realpath -m "$PREFIX_ROOT")/$label"
test ! -e "$out"; test ! -e "$prefix"
mkdir "$out"
{
  echo "label=$label mode=$mode timeout=$secs bench=delegated uidmap=0:$(id -u):1,1:$subu_start:65536 gidmap=0:$(id -g):1,1:$subg_start:65536 setgroups=allow supplementary_groups=0"
  echo "args=${pargs[*]:-}"
  echo "layer=${LAYER:-none}"
  [ -n "$LAYER" ] && (cd "$LAYER" && find . -type f -exec sha256sum {} \; | sed 's/^/layer_file=/')
  echo "program=$prog sha256=$(sha256sum "$prog" | cut -d' ' -f1)"
  for d in "$(dirname "$prog")"/*.dylib; do [ -e "$d" ] && echo "dylib=$d sha256=$(sha256sum "$d" | cut -d' ' -f1)"; done
  echo "installation=$INST kernel=$(sha256sum "$INST/libexec/darling/usr/lib/system/libsystem_kernel.dylib" | cut -d' ' -f1) darling=$(sha256sum "$INST/bin/darling" | cut -d' ' -f1) mldr32=$(sha256sum "$INST/libexec/darling/usr/libexec/darling/mldr32" | cut -d' ' -f1) dyld=$(sha256sum "$INST/libexec/darling/usr/lib/dyld" | cut -d' ' -f1)"
  echo "host_mounts_before=$(findmnt -rn | wc -l) darlingserver_before=$(pgrep -c -x darlingserver || true)"
  echo "start=$(date -Is)"
} > "$out/meta.txt"
t0=$(date +%s.%N)
set +e
env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME="$R0/home" TMPDIR="$R0/tmp" LANG=C.UTF-8 BM4_ENV_TOKEN=BM4_VALUE \
 timeout --signal=TERM --kill-after=3s "${secs}s" \
 unshare --user --map-users=0:$(id -u):1 --map-users=1:$subu_start:65536 --map-groups=0:$(id -g):1 --map-groups=1:$subg_start:65536 --setgroups=allow --mount --mount-proc --pid --fork --kill-child --ipc --uts --net \
 /bin/bash -c '
  set -Eeuo pipefail
  INSTX="$1"; PROGX="$3"
  echo "PREFLIGHT setgroups=$(cat /proc/self/setgroups)" >&2
  echo "PREFLIGHT uid_map=$(tr -s " " </proc/self/uid_map | tr "\n" ";")" >&2
  echo "PREFLIGHT gid_map=$(tr -s " " </proc/self/gid_map | tr "\n" ";")" >&2
  test "$(cat /proc/self/setgroups)" = allow
  "$5" >&2
  echo "PREFLIGHT probe=OK" >&2
  mount --make-rprivate /
  mount -t tmpfs -o size=64m,mode=1777 tmpfs /tmp
  mount --bind "$1" "$1"
  mount -o remount,bind,ro "$1"
  if test -n "$6"; then
    mount -t overlay overlay -o ro,lowerdir="$6":"$1/libexec/darling" "$1/libexec/darling"
  fi
  echo "PREFLIGHT ns_kernel=$(sha256sum "$1/libexec/darling/usr/lib/system/libsystem_kernel.dylib" | cut -d" " -f1)" >&2
  echo "PREFLIGHT ns_dyld=$(sha256sum "$1/libexec/darling/usr/lib/dyld" | cut -d" " -f1)" >&2
  export DPREFIX="$2"
  test ! -e "$DPREFIX"
  if test "$4" = bypass; then export DSERVER_INIT=/usr/libexec/shellspawn; else unset DSERVER_INIT; fi
  ulimit -c 0
  # Inherited host supplementary groups (adm, sudo, ...) cannot be delegated and show as 65534 here;
  # setgroups() would reorder them, so the bench starts from a fully mapped list {0} (= host primary gid).
  echo "PREFLIGHT groups_before=$(id -G)" >&2
  echo "PREFLIGHT groups_darling=$(setpriv --groups=0 -- id -G)" >&2
  shift 6
  exec setpriv --groups=0 -- "$INSTX/bin/darling" exec "$PROGX" "$@"
 ' r0b "$INST" "$prefix" "$prog" "$mode" "$PROBE" "$LAYER" "${pargs[@]}" </dev/null >"$out/stdout.log" 2>"$out/stderr.log"
rc=$?
set -e
t1=$(date +%s.%N)
sleep 1
{
  echo "rc=$rc"
  echo "seconds=$(echo "$t1 - $t0" | bc 2>/dev/null || echo NA)"
  echo "end=$(date -Is)"
  echo "host_mounts_after=$(findmnt -rn | wc -l) darlingserver_after=$(pgrep -c -x darlingserver || true)"
  echo "residual_prefix_processes=$(pgrep -f -- "$prefix" | wc -l)"
} >> "$out/meta.txt"
echo "$rc" > "$out/rc"
printf 'LABEL=%s RC=%s\n' "$label" "$rc"
exit 0
