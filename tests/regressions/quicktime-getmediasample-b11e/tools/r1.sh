#!/usr/bin/env bash
# QT-B11E-R1: build and run the native witness of the real extractor.
# Bash, Debian WSL2. Writes only $Q/runs/r1-<LABEL>-*. No network, no install.
# Usage: r1.sh LABEL
set -Eeuo pipefail
umask 077
export LC_ALL=C
Q=/home/Deniel/d4wrling-work/validation/quicktime-b11e-20261114
S=$Q/src
P=$Q/probe
QT=$S/src/frameworks/QuickTime/src
T=$S/tests/regressions/quicktime-mov-pcm
L=${1:?label}
case "$L" in *[!A-Za-z0-9_-]*) echo bad label; exit 2;; esac
SAN=(-O1 -g -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer)
W=(-std=c11 -Wall -Wextra -Werror)

run() { # name compiler-argv... -- pcm_source
  local name=$1; shift
  local d=$Q/runs/r1-$L-$name; test ! -e "$d"; mkdir -p "$d"
  local cc=() pcm
  while [ "$1" != "--" ]; do cc+=("$1"); shift; done; shift; pcm=$1
  "${cc[@]}" "${W[@]}" "${SAN[@]}" ${EXTRA:-} -I "$QT" -I "$T" "$pcm" "$QT/qt_mov_probe.c" "$P/b11e-r1-native.c" \
    -o "$d/b11e-r1-native" > "$d/compile.log" 2>&1 || { echo "COMPILE FAIL $name"; cat "$d/compile.log"; return 1; }
  sha256sum "$pcm" "$QT/qt_mov_probe.c" "$QT/qt_mov_pcm.h" "$QT/qt_mov_probe.h" "$T/test_mov_pcm.c" \
    "$P/b11e-r1-native.c" "$d/b11e-r1-native" > "$d/SHA256SUMS"
  local s=$(date +%s%N) rc
  set +e
  ASAN_OPTIONS=detect_leaks=${LEAKS:-1}:abort_on_error=0 UBSAN_OPTIONS=print_stacktrace=1 \
    timeout 600 "$d/b11e-r1-native" "$d" > "$d/stdout.log" 2> "$d/stderr.log"
  rc=$?
  set -e
  echo "$rc" > "$d/rc"
  echo "elapsed_ms=$(( ($(date +%s%N)-s)/1000000 ))" > "$d/meta.txt"
  local v; v=$(python3 -I "$P/verify_r1.py" "$d" | head -1)
  echo "$name rc=$rc $(grep -E '^R1_SUMMARY' "$d/stdout.log" | tail -1) $(grep -E '^checks=' "$d/stdout.log" | tail -1) sanitizer=$(grep -c -E 'ERROR: (Address|Leak)Sanitizer|runtime error' "$d/stderr.log") $v"
}

mkmut() { # name old new -> path of mutated qt_mov_pcm.c
  local out=$Q/runs/r1-$L-mutants; mkdir -p "$out"
  python3 -I - "$QT/qt_mov_pcm.c" "$out/$1.c" "$2" "$3" <<'PY'
import sys
src, dst, old, new = sys.argv[1:5]
t = open(src).read()
assert t.count(old) == 1, old
open(dst, "w").write(t.replace(old, new))
PY
  echo "$out/$1.c"
}

run clang-x64 clang-19 -- "$QT/qt_mov_pcm.c"
run clang-i686 clang-19 -m32 -- "$QT/qt_mov_pcm.c"
LEAKS=1 run gcc-x64 gcc -- "$QT/qt_mov_pcm.c"
# Negative controls: each mutant must be rejected (witness or oracle).
m1=$(mkmut no-mdat-bound "bytes <= body.n - (offset - start)" "(bytes | 1)")
m2=$(mkmut offset-plus-2 "    *where = (size_t)offset;" "    *where = (size_t)offset + 2;")
m3=$(mkmut no-self-flag "    if (version_flags != 0x000001)
        return D4RL_QT_PCM_UNSUPPORTED;
" "    (void)version_flags;
")
EXTRA=-Wno-error run mut-no-mdat-bound clang-19 -- "$m1" || true
run mut-offset-plus-2 clang-19 -- "$m2" || true
run mut-no-self-flag clang-19 -- "$m3" || true
