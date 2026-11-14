#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Verify a prebuilt REAL x86_64 Mach-O binary and run it through an explicit
# Darling wrapper. This script NEVER builds, installs, or downloads anything.
set -eu

blocked() { printf 'BLOCKED: %s\n' "$*" >&2; exit 2; }
failed() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

if [ "$#" -ne 4 ]; then
    blocked 'usage: sh run.sh corefoundation|carbon <Mach-O executable> <CoreFoundation Mach-O dylib> <Darling executable wrapper>'
fi
mode=$1
binary=$2
corefoundation=$3
runner=$4

case "$mode" in
    corefoundation)
        expected='CoreFoundation Mach-O runtime checks: 18 | Failures: 0'
        ;;
    carbon)
        expected='Carbon HIToolbox/CoreFoundation integration checks: 18 | Failures: 0'
        ;;
    *) blocked "unknown suite: $mode" ;;
esac

command -v file >/dev/null 2>&1 || blocked 'file utility unavailable'
command -v llvm-objdump >/dev/null 2>&1 || blocked 'llvm-objdump unavailable'

[ -f "$binary" ] && [ -r "$binary" ] || blocked 'Mach-O smoke executable unavailable'
kind=$(file -b -L "$binary") || blocked 'unable to inspect executable'
case "$kind" in *Mach-O*) ;; *) blocked "not a Mach-O executable: $kind" ;; esac
case "$kind" in *x86_64*) ;; *) blocked "not an x86_64 Mach-O binary: $kind" ;; esac
case "$kind" in *executable*) ;; *) blocked "input is not an executable Mach-O file: $kind" ;; esac

[ -f "$corefoundation" ] && [ -r "$corefoundation" ] || blocked 'real CoreFoundation dylib unavailable'
cf_kind=$(file -b -L "$corefoundation") || blocked 'unable to inspect CoreFoundation dylib'
case "$cf_kind" in *Mach-O*) ;; *) blocked "CoreFoundation is not Mach-O: $cf_kind" ;; esac
case "$cf_kind" in *x86_64*) ;; *) blocked "CoreFoundation is not x86_64 Mach-O: $cf_kind" ;; esac

libs=$(llvm-objdump --macho --dylibs-used "$binary" 2>&1) || blocked 'cannot inspect Mach-O linked libraries'
case "$libs" in *CoreFoundation*) ;; *) blocked 'executable has no direct CoreFoundation dylib dependency' ;; esac
if [ "$mode" = carbon ]; then
    case "$libs" in *HIToolbox*) ;; *) blocked 'Carbon smoke has no HIToolbox dylib dependency' ;; esac
fi

command -v "$runner" >/dev/null 2>&1 || blocked 'Darling runner wrapper unavailable'
[ -x "$runner" ] || blocked 'Darling runner wrapper is not executable'

log=$(mktemp) || blocked 'cannot create temporary log'
trap 'rm -f "$log"' EXIT HUP INT TERM

# The wrapper is expected to execute its one argument inside the installed
# Darling environment and expose stdout, stderr and exit status faithfully.
if "$runner" "$binary" >"$log" 2>&1; then
    cat "$log"
else
    status=$?
    cat "$log"
    failed "Darling wrapper exited $status"
fi

grep -Fx "$expected" "$log" >/dev/null 2>&1 || failed 'expected complete smoke-test summary is absent'
printf 'PASS: %s smoke executed through the supplied Darling wrapper.\n' "$mode"
printf 'LIMIT: independently verify which CoreFoundation image Darling actually loaded.\n'
