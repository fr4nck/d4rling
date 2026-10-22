#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Explicitly uses small dependency fixtures, NOT the Darling SDK/CF runtime.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT HUP INT TERM
cc=${CC:-gcc}
set -- -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror -pthread \
    -I"$repo/tests/regressions/carbon-events/isolated" \
    -I"$repo/src/frameworks/Carbon/HIToolbox/include"
case ${SANITIZE:-} in
    '') ;;
    address|undefined|address,undefined)
        set -- "$@" -fsanitize="$SANITIZE" -fno-omit-frame-pointer -fno-pie -no-pie ;;
    *) echo 'Unsupported SANITIZE' >&2; exit 2 ;;
esac
"$cc" "$@" -c "$repo/src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c" -o "$build/core.o"
"$cc" "$@" -c "$repo/tests/regressions/carbon-events/allocator-adapter.c" -o "$build/adapter.o"
for unit in events parameters queue-dispatch; do
    "$cc" "$@" "$repo/tests/regressions/carbon-events/$unit.c" \
        "$build/core.o" "$build/adapter.o" -o "$build/$unit"
    "$build/$unit"
done
