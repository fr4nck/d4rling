#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT HUP INT TERM
cc=${CC:-clang}
linker=${LINKER:-$cc}
set -- -std=c11 -D_POSIX_C_SOURCE=200809L -D__APPLE_CC__=1 \
    -DDEPLOYMENT_RUNTIME_SWIFT=1 -include "$repo/basic-headers/MacTypes.h" \
    -I"$repo/src/frameworks/Carbon/HIToolbox/include" \
    -I"$repo/src/frameworks/CoreServices/include" \
    -I"$repo/src/external/corefoundation/include" -I"$repo/basic-headers" \
    -pthread
# SANITIZE=address adds instrumentation; LINKER can select an installed runtime.
if [ "${SANITIZE:-}" = address ]; then
    set -- "$@" -fsanitize=address -fno-omit-frame-pointer
fi
for unit in events parameters allocator-adapter; do
    "$cc" "$@" -c "$repo/tests/regressions/carbon-events/$unit.c" -o "$build/$unit.o"
done
"$cc" "$@" -c "$repo/src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c" -o "$build/core.o"
if [ "${SANITIZE:-}" = address ]; then
    "$linker" -fsanitize=address -pthread "$build/events.o" "$build/allocator-adapter.o" "$build/core.o" -o "$build/events"
else
    "$linker" -pthread "$build/events.o" "$build/allocator-adapter.o" "$build/core.o" -o "$build/events"
fi
"$build/events"

# Second host executable exercises typed parameters and event-copy ownership.
if [ "${SANITIZE:-}" = address ]; then
    "$linker" -fsanitize=address -pthread "$build/parameters.o" "$build/allocator-adapter.o" "$build/core.o" -o "$build/parameters"
else
    "$linker" -pthread "$build/parameters.o" "$build/allocator-adapter.o" "$build/core.o" -o "$build/parameters"
fi
"$build/parameters"
