#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Host-only fixture and symbol-inventory verification. No Darling runtime.
set -eu
umask 077

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python=${PYTHON:-python3}

"$python" -B "$root/test_generate.py"
"$python" -B "$root/test_symbol_providers.py"

work=$(mktemp -d "${TMPDIR:-/tmp}/d4rling-macho-i386.XXXXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM

"$python" -B "$root/generate.py" --output "$work/fixture" --base 0x100000
"$python" -B "$root/generate.py" --output "$work/fixture-alt" --base 0x10000

if command -v file >/dev/null 2>&1; then
    description=$(file -b "$work/fixture")
    case "$description" in
        *Mach-O*i386*) printf 'FILE_FORMAT=PASS (%s)\n' "$description" ;;
        *) printf 'FILE_FORMAT=FAIL (%s)\n' "$description" >&2; exit 1 ;;
    esac
else
    printf 'FILE_FORMAT=SKIP (file utility unavailable)\n'
fi

printf 'HOST_TESTS=PASS\n'
printf 'GUEST_EXECUTION=NOT_ATTEMPTED\n'
