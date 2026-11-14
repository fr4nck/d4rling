#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Host qualification ONLY: actual 3-unit CarbonCore API, original public header.
set -Eeuo pipefail
umask 077
ulimit -c 0
ROOT="$(cd -- "$(dirname -- "$0")/../../.." && pwd)"
SUITE="$ROOT/tests/regressions/carboncore-resource-i2c"
I1="$ROOT/tests/regressions/carboncore-memory-resource-i1"
SRC="$ROOT/src/frameworks/CoreServices/src/CarbonCore"
HEAD="$ROOT/src/frameworks/CoreServices/include"
CXX="$1"
OPT="$2"
[[ "$OPT" == '-O0' || "$OPT" == '-O2' ]] || { echo 'BLOCKED: unexpected optimization mode' >&2; exit 2; }
command -v "$CXX" >/dev/null || { echo 'BLOCKED: no C++ compiler' >&2; exit 2; }
while IFS=':' read -r f blob; do
  [[ "$(git hash-object "$SRC/$f")" == "$blob" ]] || { echo "BLOCKED: source changed: $f" >&2; exit 2; }
done <<'PINS'
MacMemory.cpp:26dfea4803ad1499a542f8843862f8998dc5f292
ResourcesImpl.cpp:30714d701c18491c806f4a1c45d6c4cf902fd53d
Resources.cpp:2b005a49a29d72e136a63c978eee3bc30d4df7af
PINS
TMP="$(mktemp -d -t d4-i2c-public.XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
"$CXX" -std=c++17 "$OPT" -g0 -Wall -Wextra -Werror -Wno-unused-parameter -Wno-error=sign-compare -include cstring -pthread \
 -fno-omit-frame-pointer -fsanitize=address,undefined \
 -I"$SUITE/shims" -I"$HEAD" -I"$I1/shims" -I"$SRC" \
 "$SRC/MacMemory.cpp" "$SRC/ResourcesImpl.cpp" "$SRC/Resources.cpp" "$SUITE/test.cpp" \
 -o "$TMP/i2c-public"
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 TMPDIR="$TMP" "$TMP/i2c-public"
