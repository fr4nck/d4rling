#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -Eeuo pipefail
installation=$1
work=$2
label=$3
executable=$4
shift 4
ulimit -c 0
mount --make-rprivate /
mount --bind "$installation" /opt/d4rling-qt-i386
mount -o remount,bind,ro /opt/d4rling-qt-i386
printf 'RUN_LABEL=%s\nINSTALLATION_KERNEL_SHA256=' "$label"
sha256sum /opt/d4rling-qt-i386/libexec/darling/usr/lib/system/libsystem_kernel.dylib
export DPREFIX="$work/p-$label"
test "${#DPREFIX}" -le 75 || { echo 'Private prefix path too long for Unix sockets' >&2; exit 2; }
unset DSERVER_INIT
exec /opt/d4rling-qt-i386/bin/darling exec "$executable" "$@"
