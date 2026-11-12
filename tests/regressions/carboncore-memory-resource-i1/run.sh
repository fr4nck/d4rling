#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# CarbonCore I1: true M2 + R2 production translation units, host-only shims.
set -Eeuo pipefail
umask 077
ulimit -c 0
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
SUITE="$ROOT/tests/regressions/carboncore-memory-resource-i1"
SRC="$ROOT/src/frameworks/CoreServices/src/CarbonCore"
HEAD="$ROOT/src/frameworks/CoreServices/include"
CXX="${1:-g++}"
OPT="${D4_I1_OPT_LEVEL:--O0}"
[[ "$OPT" == '-O0' || "$OPT" == '-O2' ]] || { echo "BLOCKED: only -O0 / -O2 permitted" >&2; exit 2; }
command -v "$CXX" >/dev/null || { echo "BLOCKED: compiler not found: $CXX" >&2; exit 2; }
command -v git >/dev/null || { echo 'BLOCKED: git hash-object required' >&2; exit 2; }
check_blob() {
    local file="$1" expected="$2"
    [[ -f "$file" ]] || { echo "BLOCKED: missing $file" >&2; exit 2; }
    local got
    got="$(git hash-object "$file")"
    [[ "$got" == "$expected" ]] || { echo "BLOCKED: blob mismatch $file: $got != $expected" >&2; exit 2; }
}
check_blob "$SRC/MacMemory.cpp" '26dfea4803ad1499a542f8843862f8998dc5f292'
check_blob "$HEAD/CarbonCore/MacMemory.h" '91be5171aee4910f7910f465a1da96519127a96e'
check_blob "$SRC/ResourcesImpl.cpp" '30714d701c18491c806f4a1c45d6c4cf902fd53d'
check_blob "$SRC/ResourcesImpl.h" '08eca11a823b4549dfc3f40229d9f729938ba385'
check_blob "$SUITE/test.cpp" '9b821cdfc9b88b35e7c9213766b47f1e9c03020b'
check_blob "$SUITE/shims/MacTypes.h" '55cbc3ed75e6f8b6b95b7c1a5a99a7cd9628f5b0'
check_blob "$SUITE/shims/CarbonCore/Resources.h" 'ba25052cbcb61d6660e0f18bb1d8c3237ce4f455'
check_blob "$SUITE/shims/CarbonCore/MacErrors.h" 'bc87e91bf19f156397af0aa3fdff5d80127e2c89'
check_blob "$SUITE/shims/malloc/malloc.h" 'c99523b1653e27526ba5d78851113e4d900741d8'
check_blob "$SUITE/shims/sys/xattr.h" '1d9820b07473c9ce78712c7d29922c2fa8fe9b42'
TMP="$(mktemp -d -t d4-carboncore-i1.XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
"$CXX" -std=c++17 "$OPT" -g0 -Wall -Wextra -Werror -Wno-unused-parameter -pthread \
  -fno-omit-frame-pointer -fsanitize=address,undefined \
  -I"$SUITE/shims" -I"$HEAD" -I"$SRC" \
  "$SRC/MacMemory.cpp" "$SRC/ResourcesImpl.cpp" "$SUITE/test.cpp" \
  -Wl,--wrap=malloc -o "$TMP/contracts"
set +e
OUT="$(TMPDIR="$TMP" ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 "$TMP/contracts" 2> "$TMP/stderr")"
RC=$?
set -e
if (( RC != 0 )); then cat "$TMP/stderr" >&2; printf '%s\n' "$OUT"; exit "$RC"; fi
[[ ! -s "$TMP/stderr" ]] || { cat "$TMP/stderr" >&2; exit 1; }
printf '%s\n' "$OUT"
[[ "$OUT" == 'CARBONCORE_I1_REAL_UNITS: 54 PASS, 0 FAIL' ]] || { echo 'FAIL: unexpected I1 contract count' >&2; exit 1; }
