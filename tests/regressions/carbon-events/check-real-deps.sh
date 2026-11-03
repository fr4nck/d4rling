#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Preflight only. This does not build Darling or validate its CF runtime.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
cc=${CC:-clang}
linker=${LINKER:-$cc}
status=0
for tool in "$cc" "$linker"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'BLOCKED: tool unavailable: %s\n' "$tool" >&2
        status=2
    fi
done
for rel in \
    basic-headers/MacTypes.h \
    src/frameworks/CoreServices/include/CoreServices/MacTypes.h \
    src/frameworks/CoreServices/include/CarbonCore/MacErrors.h \
    src/frameworks/Carbon/HIToolbox/include/HIToolbox/CarbonEventsCore.h \
    src/frameworks/Carbon/HIToolbox/include/HIToolbox/Menus.h \
    src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c \
    tests/regressions/carbon-events/allocator-adapter.c \
    tests/regressions/carbon-events/events.c \
    tests/regressions/carbon-events/parameters.c \
    tests/regressions/carbon-events/queue-dispatch.c
do
    if [ ! -f "$repo/$rel" ]; then
        printf 'BLOCKED: required source/header missing: %s\n' "$rel" >&2
        status=2
    fi
done
cf='src/external/corefoundation/include/CoreFoundation/CFBase.h'
if [ ! -f "$repo/$cf" ]; then
    printf 'BLOCKED: required real CoreFoundation header missing: %s\n' "$cf" >&2
    if [ -L "$repo/$cf" ]; then
        printf '  CFBase.h is a broken symlink: check the nested swift-corelibs-foundation submodule.\n' >&2
    else
        printf '  Check that the pinned CoreFoundation submodule is initialized.\n' >&2
    fi
    status=2
fi
if [ "$status" -ne 0 ]; then
    printf 'NOT RUN: real-header Carbon regression suite (no dependencies installed by this script).\n' >&2
    exit "$status"
fi
printf 'PASS: declared toolchain and primary header/source paths present (compilation not yet proven).\n'
