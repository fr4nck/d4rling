#!/usr/bin/env bash
# Explicit runtime test in a fresh user/mount/PID/network namespace.
set -Eeuo pipefail
test "$#" = 4 || { echo "usage: bash run-guest.sh PRIVATE_INSTALL PROGRAM normal|bypass TIMEOUT_SECONDS" >&2; exit 2; }
installation="$(realpath "$1")"
program="$(realpath "$2")"
mode="$3"
seconds="$4"
test -x "$installation/bin/darling"
test -x "$program"
case "$installation" in /usr/*|/opt/*) echo "Use a separate private installation copy" >&2; exit 2;; esac
case "$mode" in normal|bypass) ;; *) exit 2;; esac
case "$seconds" in ''|*[!0-9]*) exit 2;; esac
test "$seconds" -ge 1
test "$seconds" -le 120
report="$(mktemp -d /tmp/d4rl-replay.XXXXXXXX)"
prefix="$report/prefix"
host_mnt="$(readlink /proc/self/ns/mnt)"
host_pid="$(readlink /proc/self/ns/pid)"
set +e
timeout --signal=TERM --kill-after=3s "${seconds}s" \
 unshare --user --map-root-user --mount --mount-proc --pid --fork --kill-child --ipc --uts --net \
 /bin/bash -c '
 set -Eeuo pipefail
 test "$(readlink /proc/self/ns/mnt)" != "$1"
 test "$(readlink /proc/self/ns/pid)" != "$2"
 mount --make-rprivate /
 export DPREFIX="$4"
 test ! -e "$DPREFIX"
 if test "$6" = bypass; then export DSERVER_INIT=/usr/libexec/shellspawn; else unset DSERVER_INIT; fi
 ulimit -c 0
 exec "$3/bin/darling" exec "$5"
 ' replay "$host_mnt" "$host_pid" "$installation" "$prefix" "$program" "$mode" \
 </dev/null >"$report/stdout.log" 2>"$report/stderr.log"
rc="$?"
set -e
printf '%s\n' "$rc" >"$report/exit-code.txt"
printf 'REPORT=%s\nEXIT_CODE=%s\n' "$report" "$rc"
exit "$rc"
