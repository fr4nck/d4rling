#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
cc=${CC:-clang}
linker=${LINKER:-$cc}
case ${SANITIZE:-} in
    '') sanitizer= ;;
    address|undefined|address,undefined) sanitizer="-fsanitize=$SANITIZE" ;;
    *) printf 'ERROR: unsupported SANITIZE=%s (use address, undefined or address,undefined)\n' "$SANITIZE" >&2; exit 2 ;;
esac
sh "$repo/tests/regressions/carbon-events/check-real-deps.sh"
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT HUP INT TERM
set -- -std=c11 -D_POSIX_C_SOURCE=200809L -D__APPLE_CC__=1 \
    -DDEPLOYMENT_RUNTIME_SWIFT=1 -include "$repo/basic-headers/MacTypes.h" \
    -I"$repo/src/frameworks/Carbon/HIToolbox/include" \
    -I"$repo/src/frameworks/CoreServices/include" \
    -I"$repo/src/external/corefoundation/include" -I"$repo/basic-headers" \
    -pthread
if [ -n "$sanitizer" ]; then
    set -- "$@" "$sanitizer" -fno-omit-frame-pointer
fi
for unit in events parameters queue-dispatch allocator-adapter; do
    "$cc" "$@" -c "$repo/tests/regressions/carbon-events/$unit.c" -o "$build/$unit.o"
done
"$cc" "$@" -c "$repo/src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c" -o "$build/core.o"
link_executable() {
    if [ -n "$sanitizer" ]; then
        "$linker" "$sanitizer" -pthread "$@"
    else
        "$linker" -pthread "$@"
    fi
}
for unit in events parameters queue-dispatch; do
    link_executable "$build/$unit.o" "$build/allocator-adapter.o" "$build/core.o" -o "$build/$unit"
    "$build/$unit"
done
