#!/usr/bin/env bash
# QT-B11E-R2 native stage: real QuickTime.c (worktree), qt_mov_*.c and the real
# CarbonCore MacMemory.cpp, compiled for Linux x64 and i686 with ASan/UBSan
# (LSan on x64), driven by b11e-r2-getmediasample.c on the R1 MOV files.
# Compat headers only replace Darwin platform macros/malloc_size (probe/compat-native).
# Writes only $Q/runs/r2n-<LABEL>-*. Usage: r2-native.sh LABEL R1_RUN_DIR
set -Eeuo pipefail
umask 077
export LC_ALL=C
Q=/home/Deniel/d4wrling-work/validation/quicktime-b11e-20261114
S=$Q/src
QT=$S/src/frameworks/QuickTime
CS=$S/src/frameworks/CoreServices
L=${1:?label}; MOVS=${2:?r1 run dir}
SAN=(-O1 -g -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer)
INC=(-I "$Q/probe/compat-native" -I "$QT/include" -I "$QT/src" -I "$CS/include" -I "$S/basic-headers")

run() { # name arch-flags quicktime_c
  local name=$1 arch=$2 qtc=$3 d=$Q/runs/r2n-$L-$1
  test ! -e "$d"; mkdir -p "$d/out"
  {
    clang-19 $arch -std=gnu11 "${SAN[@]}" -w "${INC[@]}" -c "$qtc" -o "$d/QuickTime.o"
    clang-19 $arch -std=gnu11 "${SAN[@]}" -Wall -Wextra -Werror "${INC[@]}" -c "$QT/src/qt_mov_probe.c" -o "$d/probe.o"
    clang-19 $arch -std=gnu11 "${SAN[@]}" -Wall -Wextra -Werror "${INC[@]}" -c "$QT/src/qt_mov_pcm.c" -o "$d/pcm.o"
    clang++-19 $arch -std=gnu++17 "${SAN[@]}" -Wall -Wextra "${INC[@]}" -c "$CS/src/CarbonCore/MacMemory.cpp" -o "$d/MacMemory.o"
    clang-19 $arch -std=gnu11 "${SAN[@]}" -Wall -Wextra -Werror "${INC[@]}" -c "$Q/probe/b11e-r2-getmediasample.c" -o "$d/witness.o"
    clang++-19 $arch "${SAN[@]}" "$d"/*.o -o "$d/witness"
  } > "$d/compile.log" 2>&1 || { echo "$name COMPILE_FAIL"; tail -5 "$d/compile.log"; return 0; }
  sha256sum "$qtc" "$QT/include/QuickTime/QuickTime.h" "$QT/src/qt_mov_probe.c" "$QT/src/qt_mov_pcm.c" \
    "$CS/src/CarbonCore/MacMemory.cpp" "$Q/probe/b11e-r2-getmediasample.c" "$MOVS"/mov-*.mov "$d/witness" > "$d/SHA256SUMS"
  local rc
  set +e
  ASAN_OPTIONS=detect_leaks=${LEAKS:-1} UBSAN_OPTIONS=print_stacktrace=1 timeout 600 "$d/witness" "$MOVS" "$d/out" "${CYCLES:-100}" \
    > "$d/stdout.log" 2> "$d/stderr.log"
  rc=$?
  set -e
  echo "$rc" > "$d/rc"
  echo "$name rc=$rc $(grep -E '^R2_SUMMARY' "$d/stdout.log") fails=$(grep -c ' FAIL ' "$d/stdout.log") sanitizer=$(grep -c -E 'ERROR: (Address|Leak)Sanitizer|runtime error' "$d/stderr.log")"
}

mkmut() { # name old new
  local out=$Q/runs/r2n-$L-mutants; mkdir -p "$out"
  python3 -I - "$QT/src/QuickTime.c" "$out/$1.c" "$2" "$3" <<'PY'
import sys
src, dst, old, new = sys.argv[1:5]
t = open(src).read()
assert t.count(old) == 1, old
open(dst, "w").write(t.replace(old, new))
PY
  echo "$out/$1.c"
}

run x64 "" "$QT/src/QuickTime.c"
LEAKS=0 run i686 "-m32" "$QT/src/QuickTime.c"
# Negative controls on GetMediaSample itself.
run mut-no-copy "" "$(mkmut no-copy '    memcpy(*dataOut, (const unsigned char *)movie->pcm + start, bytes);
' '' )" || true
run mut-offset-ignored "" "$(mkmut offset-ignored '(const unsigned char *)movie->pcm + start, bytes);' '(const unsigned char *)movie->pcm, bytes);')" || true
run mut-no-end-check "" "$(mkmut no-end-check '    if (time < 0 || (uint32_t)time >= info->frame_count)
        return movie_fail(d4rlTimeNotInMedia);
' '    if (time < 0)
        return movie_fail(d4rlTimeNotInMedia);
')" || true
run mut-empty-as-error "" "$(mkmut empty-as-error '    empty = error == d4rlNilHandleErr; /* registered handle without a block */' '    empty = 0;')" || true
