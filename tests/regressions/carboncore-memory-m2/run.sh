#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# CarbonCore Memory M2, host-only. Never touches an installed Darling prefix.
set -Eeuo pipefail
umask 077
ulimit -c 0
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SRC="${D4_M2_TEST_SOURCE:-$ROOT/src/frameworks/CoreServices/src/CarbonCore/MacMemory.cpp}"
HEADER="$ROOT/src/frameworks/CoreServices/include/CarbonCore/MacMemory.h"
TEST="$(dirname "${BASH_SOURCE[0]}")/test.cpp"
CXX="${1:-g++}"
OPT="${D4_M2_OPT_LEVEL:--O0}"
[[ -f "$SRC" && -f "$HEADER" && -f "$TEST" ]] || { echo 'BLOCKED: missing production source/header/test' >&2; exit 2; }
if [[ -z "${D4_M2_TEST_SOURCE:-}" ]]; then
  [[ "$(git hash-object "$SRC")" == "26dfea4803ad1499a542f8843862f8998dc5f292" ]] || { echo 'BLOCKED: changed production source blob' >&2; exit 2; }
fi
[[ "$(git hash-object "$HEADER")" == "91be5171aee4910f7910f465a1da96519127a96e" ]] || { echo 'BLOCKED: changed production header blob' >&2; exit 2; }
[[ "$(git hash-object "$TEST")" == "166aa6683e2c1891f16de39d5b9554256897c1ac" ]] || { echo 'BLOCKED: changed M2 test blob' >&2; exit 2; }
command -v "$CXX" >/dev/null || { echo "BLOCKED: no compiler $CXX" >&2; exit 2; }
TMP="$(mktemp -d -t d4-carboncore-m2.XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
mkdir -p "$TMP/include/CarbonCore" "$TMP/include/malloc"
cat > "$TMP/include/MacTypes.h" <<'H'
#pragma once
using Ptr = char*;
using Handle = Ptr*;
using Size = long;
using OSErr = short;
H
cat > "$TMP/include/CarbonCore/MacErrors.h" <<'H'
#pragma once
#include <MacTypes.h>
constexpr OSErr noErr = 0;
constexpr OSErr memFullErr = -108;
constexpr OSErr nilHandleErr = -109;
constexpr OSErr memAdrErr = -110;
constexpr OSErr memWZErr = -111;
constexpr OSErr memLockedErr = -117;
constexpr OSErr memPurErr = -112;
constexpr OSErr paramErr = -50;
H
cat > "$TMP/include/malloc/malloc.h" <<'H'
#pragma once
#include <malloc.h>
static inline size_t malloc_size(void* ptr) { return malloc_usable_size(ptr); }
H
"$CXX" -std=c++17 "$OPT" -g -Wall -Wextra -Werror -Wno-unused-parameter -pthread \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  -I "$TMP/include" -I "$ROOT/src/frameworks/CoreServices/include" \
  "$SRC" "$TEST" -Wl,--wrap=malloc,--wrap=realloc -o "$TMP/contract"
RESULT="$(ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 "$TMP/contract")"
printf '%s\n' "$RESULT"
[[ "$RESULT" == "CARBONCORE_MEMORY_M2_HOST: 113 PASS, 0 FAIL" ]] || { echo 'BLOCKED: unexpected host test count/result' >&2; exit 2; }
