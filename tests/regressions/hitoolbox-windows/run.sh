#!/bin/sh
set -eu
test_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(CDPATH= cd -- "$test_dir/../../.." && pwd)
mkdir -p "$test_dir/build"
"${CXX:-c++}" -std=c++17 -I "$test_dir/include" -Wall -Wextra -Wno-unused-parameter \
    "$repo_dir/src/frameworks/Carbon/HIToolbox/src/MacWindows.cpp" \
    "$test_dir/test_windows.cpp" -o "$test_dir/build/hitoolbox_contract_test"
"$test_dir/build/hitoolbox_contract_test"
