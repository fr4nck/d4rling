#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Linux host, real ResourcesImpl.cpp and ResourcesImpl.h; isolated API shims.
set -Eeuo pipefail
umask 077
ulimit -c 0
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SUITE="$ROOT/tests/regressions/carboncore-resource-r1"
SRC="${D4_R1_TEST_SOURCE:-$ROOT/src/frameworks/CoreServices/src/CarbonCore/ResourcesImpl.cpp}"
HDR="$ROOT/src/frameworks/CoreServices/src/CarbonCore/ResourcesImpl.h"
CXX="${1:-g++}"
OPT="${D4_R1_OPT_LEVEL:--O0}"
[[ -f "$SRC" && -f "$HDR" && -f "$SUITE/test.cpp" ]] || { echo 'BLOCKED: missing R1 files' >&2; exit 2; }
# Guard against running an old oracle on an unexpected production revision.
if [[ -z "${D4_R1_TEST_SOURCE:-}" ]]; then
  [[ "$(git hash-object "$SRC")" == "372496b37acaf4547ed05638cbc03fe0707cc90a" ]] || { echo 'BLOCKED: unexpected ResourcesImpl.cpp blob' >&2; exit 2; }
fi
[[ "$(git hash-object "$HDR")" == "12790458bb94d38f10ad3fd2d038667884acf7b2" ]] || { echo 'BLOCKED: unexpected ResourcesImpl.h blob' >&2; exit 2; }
command -v "$CXX" >/dev/null 2>&1 || { echo "BLOCKED: missing $CXX" >&2; exit 2; }
TMP="$(mktemp -d -t d4-resource-r1.XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
"$CXX" -std=c++17 "$OPT" -g -Wall -Wextra -Werror -Wno-unused-parameter \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  -I"$SUITE/shims" -I"$ROOT/src/frameworks/CoreServices/src/CarbonCore" \
  "$SRC" "$SUITE/test.cpp" -o "$TMP/resource-r1"
RESULT="$(TMPDIR="$TMP" ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 "$TMP/resource-r1")"
printf '%s\n' "$RESULT"
[[ "$RESULT" == 'CARBONCORE_RESOURCE_R1_HOST: 68 PASS, 0 FAIL' ]] || { echo 'FAIL: unexpected contract output' >&2; exit 1; }
