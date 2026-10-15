#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT HUP INT TERM
cc=${CC:-clang}
cxx=${CXX:-clang++}

# Host ELF checks using real Darling headers, not a guest SDK or Mach-O build.
set -- -D__APPLE_CC__=1 -DDEPLOYMENT_RUNTIME_SWIFT=1 \
    -include "$repo/basic-headers/MacTypes.h" \
    -I"$repo/src/frameworks/Carbon/HIToolbox/include" \
    -I"$repo/src/frameworks/CoreServices/include" \
    -I"$repo/src/frameworks/ApplicationServices/QD/include" \
    -I"$repo/src/external/corefoundation/include" -I"$repo/basic-headers"
source="$repo/tests/regressions/carbon-contracts/contracts.c"
"$cxx" -std=c++17 "$@" -c \
    "$repo/src/frameworks/Carbon/HIToolbox/src/MacWindows.cpp" -o "$build/windows.o"
"$cc" -std=c11 "$@" -c \
    "$repo/src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c" -o "$build/events.o"

for language in c c++; do
    if [ "$language" = c ]; then compiler=$cc; standard=c11; else compiler=$cxx; standard=c++17; fi
    "$compiler" -x "$language" -std="$standard" \
        -Werror=incompatible-function-pointer-types "$@" -c "$source" -o "$build/contracts.o"
    "$cxx" "$build/contracts.o" "$build/windows.o" "$build/events.o" -o "$build/contracts"
    "$build/contracts"
    if "$compiler" -x "$language" -std="$standard" \
        -Werror=incompatible-function-pointer-types -DREJECT_BAD_HANDLER "$@" \
        -fsyntax-only "$source" > "$build/rejected.txt" 2>&1; then
        echo "FAIL: $language accepted an invalid callback" >&2
        exit 1
    fi
    if ! grep -q rejected_handler "$build/rejected.txt"; then
        cat "$build/rejected.txt" >&2
        echo "FAIL: negative compilation failed for an unexpected reason" >&2
        exit 1
    fi
    echo "PASS: $language signatures, direct callback invocation, null window target; invalid callback rejected"
done
