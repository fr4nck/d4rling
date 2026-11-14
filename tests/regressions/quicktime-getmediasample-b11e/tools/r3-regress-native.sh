#!/usr/bin/env bash
# QT-B11E-R3 native non-regression of the existing QuickTime witnesses against a
# given QuickTime.c (default: B11E worktree). Linux x64, ASan/UBSan/LSan.
# Usage: r3-regress-native.sh LABEL [QUICKTIME_C]
set -Eeuo pipefail
umask 077
export LC_ALL=C
Q=/home/Deniel/d4wrling-work/validation/quicktime-b11e-20261114
S=$Q/src; QT=$S/src/frameworks/QuickTime; CS=$S/src/frameworks/CoreServices; T=$S/tests/regressions
L=${1:?label}; QTC=${2:-$QT/src/QuickTime.c}
O=$Q/runs/r3n-$L; test ! -e "$O"; mkdir -p "$O"
SAN=(-O1 -g -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer)
INC=(-I "$Q/probe/compat-native" -I "${QTINC:-$QT/include}" -I "$QT/src" -I "$CS/include" -I "$S/basic-headers")
clang-19 -std=gnu11 "${SAN[@]}" -w "${INC[@]}" -include "$Q/probe/compat-hooks/alloc-adapter.h" -c "$QTC" -o "$O/QuickTime.o"
clang-19 -std=gnu11 "${SAN[@]}" -Wall -Wextra -Werror "${INC[@]}" -c "$QT/src/qt_mov_probe.c" -o "$O/probe.o"
clang-19 -std=gnu11 "${SAN[@]}" -Wall -Wextra -Werror "${INC[@]}" -c "$QT/src/qt_mov_pcm.c" -o "$O/pcm.o"
clang++-19 -std=gnu++17 "${SAN[@]}" "${INC[@]}" -c "$CS/src/CarbonCore/MacMemory.cpp" -o "$O/MacMemory.o"
sha256sum "$QTC" "$QT/src/qt_mov_probe.c" "$QT/src/qt_mov_pcm.c" "$CS/src/CarbonCore/MacMemory.cpp" > "$O/SHA256SUMS"
for w in quicktime-mov-pcm quicktime-tracks quicktime-mov-dataref; do
  d=$O/$w; mkdir -p "$d"
  hooks=(); grep -q D4RL_NATIVE_HOOKS "$T/$w/witness.c" && hooks=(-DD4RL_NATIVE_HOOKS)
  if ! clang-19 -std=gnu11 "${SAN[@]}" -w "${hooks[@]}" "${INC[@]}" -c "$T/$w/witness.c" -o "$d/witness.o" > "$d/compile.log" 2>&1 ||
     ! clang++-19 "${SAN[@]}" "$d/witness.o" "$O/QuickTime.o" "$O/probe.o" "$O/pcm.o" "$O/MacMemory.o" -o "$d/witness" >> "$d/compile.log" 2>&1; then
    echo "$w COMPILE_FAIL"; tail -3 "$d/compile.log"; continue; fi
  sha256sum "$T/$w/witness.c" >> "$O/SHA256SUMS"
  set +e; ASAN_OPTIONS=detect_leaks=1 timeout 300 "$d/witness" > "$d/stdout.log" 2> "$d/stderr.log"; rc=$?; set -e
  echo "$w rc=$rc $(grep -E 'checks=|CHECKS=' "$d/stdout.log" | tail -1) FAIL=$(grep -c '^FAIL' "$d/stdout.log") sanitizer=$(grep -c -E 'ERROR: (Address|Leak)Sanitizer|runtime error' "$d/stderr.log") marker=$(grep -E -o 'D4RLING[-A-Z0-9_]*OK' "$d/stdout.log" | tail -1)"
done
python3 -I "$T/quicktime-mov-metadata/run.py" --out "$O/mov-metadata" --cc clang-19 > "$O/mov-metadata.log" 2>&1; echo "quicktime-mov-metadata rc=$? $(tail -2 "$O/mov-metadata.log" | tr '\n' ' ')"
