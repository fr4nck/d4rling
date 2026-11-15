#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Download the Debian trixie i386 metadata used by the AUDIO-I386 inventory into a NEW
# private directory (indexes only: InRelease, Packages.xz, Contents-i386.gz; no package).
# Usage: fetch_indexes.sh INDEX_DIR ; then verify_indexes.py INDEX_DIR
set -Eeuo pipefail
D=${1:?index dir}; test ! -e "$D"; mkdir -p "$D/raw"; cd "$D/raw"
get() { curl --fail --location --max-time 180 -sS -o "$2" "$1"; }
M=https://deb.debian.org/debian/dists; S=https://security.debian.org/debian-security/dists
get "$M/trixie/InRelease" trixie-InRelease
get "$M/trixie-updates/InRelease" trixie-updates-InRelease
get "$S/trixie-security/InRelease" trixie-security-InRelease
get "$M/trixie/main/binary-i386/Packages.xz" trixie-main-i386-Packages.xz
get "$M/trixie/main/Contents-i386.gz" trixie-main-Contents-i386.gz
get "$M/trixie-updates/main/binary-i386/Packages.xz" trixie-updates-main-i386-Packages.xz
get "$S/trixie-security/main/binary-i386/Packages.xz" trixie-security-main-i386-Packages.xz
ls -l
