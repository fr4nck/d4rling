#!/bin/sh
set -eu
test_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(CDPATH= cd -- "$test_dir/../../.." && pwd)
mkdir -p "$test_dir/build"
cc=${CC:-cc}
cxx=${CXX:-c++}
# Real Darling headers, host ELF build (as tests/regressions/carbon-contracts).
set -- -D_POSIX_C_SOURCE=200809L -D__APPLE_CC__=1 -DDEPLOYMENT_RUNTIME_SWIFT=1 -D__DARWIN_NULL=0 \
    -include "$repo_dir/basic-headers/MacTypes.h" \
    -I"$repo_dir/src/frameworks/Carbon/HIToolbox/include" \
    -I"$repo_dir/src/frameworks/CoreServices/include" \
    -I"$repo_dir/src/frameworks/ApplicationServices/QD/include" \
    -I"$repo_dir/src/external/corefoundation/include" -I"$repo_dir/basic-headers"
"$cxx" -std=c++17 "$@" -Wall -Wextra -Wno-unused-parameter -c \
    "$repo_dir/src/frameworks/Carbon/HIToolbox/src/MacWindows.cpp" -o "$test_dir/build/windows.o"
"$cxx" -std=c++17 "$@" -Wall -Wextra -Wno-unused-parameter -c \
    "$test_dir/test_windows.cpp" -o "$test_dir/build/test.o"
"$cc" -std=c11 "$@" -c "$repo_dir/tests/regressions/carbon-events/allocator-adapter.c" -o "$test_dir/build/allocator.o"
"$cc" -std=c11 "$@" -c "$repo_dir/tests/regressions/carbon-contracts/host-shims.c" -o "$test_dir/build/shims.o"
"$cxx" "$test_dir/build/test.o" "$test_dir/build/windows.o" "$test_dir/build/allocator.o" \
    "$test_dir/build/shims.o" -ldl -o "$test_dir/build/hitoolbox_contract_test"
"$test_dir/build/hitoolbox_contract_test"
