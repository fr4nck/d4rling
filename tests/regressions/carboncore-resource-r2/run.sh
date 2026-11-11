#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# CarbonCore Resource Manager R2: host-only real ResourcesImpl.cpp.
set -Eeuo pipefail
umask 077
ulimit -c 0
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SUITE="$ROOT/tests/regressions/carboncore-resource-r2"
SRC="${D4_R2_TEST_SOURCE:-$ROOT/src/frameworks/CoreServices/src/CarbonCore/ResourcesImpl.cpp}"
HDR="$ROOT/src/frameworks/CoreServices/src/CarbonCore/ResourcesImpl.h"
OLD="$ROOT/tests/regressions/carboncore-resource-r1/test.cpp"
CXX="${1:-g++}"
OPT="${D4_R2_OPT_LEVEL:--O0}"
[[ -f "$SRC" && -f "$HDR" && -f "$OLD" && -f "$SUITE/test.cpp" ]] || { echo 'BLOCKED: missing Resource Manager production/contract files' >&2; exit 2; }
if [[ -z "${D4_R2_TEST_SOURCE:-}" ]]; then
  [[ "$(git hash-object "$SRC")" == '033d5cc3720b45925249113eab9dea94772e3de1' ]] || { echo 'BLOCKED: production source changed' >&2; exit 2; }
fi
[[ "$(git hash-object "$HDR")" == '1eb79e93c2ad5d91b1b205fe6824b776332a65da' ]] || { echo 'BLOCKED: production header changed' >&2; exit 2; }
[[ "$(git hash-object "$OLD")" == 'c5764b57982efada42104e4e7e7a9ec72d3674af' ]] || { echo 'BLOCKED: R1 test dependency changed' >&2; exit 2; }
[[ "$(git hash-object "$SUITE/test.cpp")" == 'cb75c91b38f7f55d28a68d5a7f4c842c073c1e4f' ]] || { echo 'BLOCKED: R2 test changed' >&2; exit 2; }
command -v "$CXX" >/dev/null || { echo "BLOCKED: missing C++ compiler $CXX" >&2; exit 2; }
[[ "$OPT" == '-O0' || "$OPT" == '-O2' ]] || { echo 'BLOCKED: only -O0 and -O2 supported' >&2; exit 2; }
TMP="$(mktemp -d -t d4-carbon-r2.XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
"$CXX" -std=c++17 "$OPT" -g -Wall -Wextra -Werror -Wno-unused-parameter \
 -fsanitize=address,undefined -fno-omit-frame-pointer \
 -I"$SUITE/shims" -I"$ROOT/src/frameworks/CoreServices/src/CarbonCore" \
 "$SRC" "$SUITE/test.cpp" \
 -Wl,--wrap=write,--wrap=rename,--wrap=fsync -o "$TMP/contract"
set +e
OUTPUT="$(TMPDIR="$TMP" ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 "$TMP/contract" 2> "$TMP/stderr")"
STATUS=$?
set -e
if (( STATUS != 0 )); then
  cat "$TMP/stderr" >&2
  printf '%s\n' "$OUTPUT"
  exit "$STATUS"
fi
[[ ! -s "$TMP/stderr" ]] || { cat "$TMP/stderr" >&2; exit 1; }
printf '%s\n' "$OUTPUT"
[[ "$OUTPUT" == *'CARBONCORE_RESOURCE_R1_HOST: 68 PASS, 0 FAIL'* ]] || { echo 'FAIL: missing R1 baseline' >&2; exit 1; }
[[ "$OUTPUT" == *'CARBONCORE_RESOURCE_R2_HOST: 153 PASS, 0 FAIL (69 R1 retained)'* ]] || { echo 'FAIL: unexpected R2 count' >&2; exit 1; }
