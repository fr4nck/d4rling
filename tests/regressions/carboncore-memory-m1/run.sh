#!/usr/bin/env bash
# CarbonCore Memory M1, host-only. Never touches an installed Darling prefix.
set -Eeuo pipefail
umask 077
ulimit -c 0
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SRC="$ROOT/src/frameworks/CoreServices/src/CarbonCore/MacMemory.cpp"
HEADER="$ROOT/src/frameworks/CoreServices/include/CarbonCore/MacMemory.h"
TEST="$(dirname "${BASH_SOURCE[0]}")/test.cpp"
CXX="${1:-g++}"
[[ -f "$SRC" && -f "$HEADER" && -f "$TEST" ]] || { echo 'BLOCKED: missing production source/header/test' >&2; exit 2; }
[[ "$(git hash-object "$SRC")" == "c862bb89b1e84ccd2a250f63c68c4a3d52e237e8" ]] || { echo 'BLOCKED: changed production source blob' >&2; exit 2; }
[[ "$(git hash-object "$HEADER")" == "91be5171aee4910f7910f465a1da96519127a96e" ]] || { echo 'BLOCKED: changed production header blob' >&2; exit 2; }
command -v "$CXX" >/dev/null || { echo "BLOCKED: no compiler $CXX" >&2; exit 2; }
TMP="$(mktemp -d -t d4-carboncore-m1.XXXXXXXX)"
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
constexpr OSErr paramErr = -50;
H
cat > "$TMP/include/malloc/malloc.h" <<'H'
#pragma once
#include <malloc.h>
static inline size_t malloc_size(void* ptr) { return malloc_usable_size(ptr); }
H
"$CXX" -std=c++17 -O0 -g -Wall -Wextra -Werror -Wno-unused-parameter -pthread \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  -I "$TMP/include" -I "$ROOT/src/frameworks/CoreServices/include" \
  "$SRC" "$TEST" -Wl,--wrap=malloc,--wrap=realloc -o "$TMP/contract"
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 "$TMP/contract"
