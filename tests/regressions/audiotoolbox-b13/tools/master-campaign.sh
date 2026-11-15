#!/usr/bin/env bash
# B13-INT: requalification on the private master build (397e94d4, libc++ 061279eb).
# Every guest run uses the master installation ($T/mbuild/private-install), the official libdyld,
# the private FFmpeg+PulseAudio ld.so.cache and, for candidates, the AudioToolbox overlay layer.
# Usage: master-campaign.sh witnesses | candidates | matrix | afm   (one phase per call)
set -Eeuo pipefail
T=$HOME/d4wrling-work/validation/audiotoolbox-b13-20261115
export INST=$T/mbuild/private-install
export LDCACHE=$T/private-ffmpeg-20261115/ld.so.cache
W=$T/mwit; F=$T/mfix; M=/Volumes/SystemRoot$T/media
run() { # LABEL CAND ARCH PROGRAM SECONDS ARGS...
  local l=$1 c=$2 a=$3 p=$4 s=$5; shift 5
  local lay=""; [ "$c" = ref ] || lay=$F/cand-$c/layer
  mkdir -p "$T/runs/out/$l"
  set +e
  local o=("/Volumes/SystemRoot$T/runs/out/$l"); [ "${NOOUT:-0}" = 1 ] && o=()   # b13-afm takes no output dir
  LAYER=$lay bash "$T/tools/run-b13.sh" "$l" "$W/$p-$a" normal "$s" "$@" "${o[@]}" > /dev/null 2>&1
  set -e
  echo "RUN $l cand=$c arch=$a prog=$p rc=$(cat "$T/runs/guest/$l/rc" 2>/dev/null) $(grep -h -E '^(B13_SUMMARY|B13FIX_SUMMARY|B13AFM_ABI)' "$T/runs/guest/$l/stdout.log" | tr '\n' ' ') ns_atb=$(grep -o 'ns_audiotoolbox=[0-9a-f]\{12\}' "$T/runs/guest/$l/stderr.log" | head -1) ns_cxx=$(grep -o 'ns_libcxx=[0-9a-f]\{12\}' "$T/runs/guest/$l/stderr.log" | head -1)"
}
case "$1" in
witnesses)
  SDK=${MACOSX_SDK:?MACOSX_SDK must name a private MacOSX.sdk}
  mkdir -p "$W"
  for a in i386 x86_64; do
    for s in b13-atb.c b13-fix.c b13-fix-v1.c b13-afm.c; do
      (cd "$T/probe" && B13_BUILD=$T/mbuild B13_SRC=$T/src CXX=1 MACOSX_SDK=$SDK bash "$T/tools/build.sh" $a "$W" $s AudioToolbox CoreAudio CoreFoundation)
    done
  done ;;
candidates)
  G=$T/mbuild; S0=$T/src/src/CoreAudio/AudioToolbox
  mkdir -p "$F"
  (cd "$G" && ninja -t compdb > "$F/compdb-all.json" && ninja -t commands -s src/CoreAudio/AudioToolbox/AudioToolbox > "$F/link-command.txt")
  B="python3 -I $T/fix/build_candidate.py $G $F/compdb-all.json $F/link-command.txt"
  $B "$F/cand-ref0"
  $B "$F/cand-fix1" "$S0/AudioConverterImpl.cpp=$T/fix/fix1/AudioToolbox/AudioConverterImpl.cpp"
  $B "$F/cand-fix2" "$S0/AudioConverter.cpp=$T/fix/fix2/AudioToolbox/AudioConverter.cpp"
  $B "$F/cand-fix2r" "$S0/AudioConverter.cpp=$T/fix/fix2r/AudioToolbox/AudioConverter.cpp"
  $B "$F/cand-fix12" "$S0/AudioConverterImpl.cpp=$T/fix/fix12/AudioToolbox/AudioConverterImpl.cpp" "$S0/AudioConverter.cpp=$T/fix/fix12/AudioToolbox/AudioConverter.cpp"
  $B "$F/cand-fix12r" "$S0/AudioConverterImpl.cpp=$T/fix/fix12r/AudioToolbox/AudioConverterImpl.cpp" "$S0/AudioConverter.cpp=$T/fix/fix12r/AudioToolbox/AudioConverter.cpp"
  ;;
matrix)
  for c in ${CANDS:-ref fix1 fix2 fix2r fix12 fix12r}; do
    k=${c/fix/}; k=${k/ref/0}
    for a in i386 x86_64; do
      x=${a:0:1}
      run "m${k}p$x" "$c" $a b13-atb 120 probe "$M"
      run "m${k}c$x" "$c" $a b13-atb 60 convertbuffer "$M"
      run "m${k}a$x" "$c" $a b13-fix 120 fix1 "$M"
      run "m${k}v$x" "$c" $a b13-fix-v1 120 fix2 "$M"
      run "m${k}b$x" "$c" $a b13-fix 120 fix2 "$M"
    done
  done ;;
afm)
  export NOOUT=1   # first afm series (mdci..mdox, 14:xx) failed with rc=2 usage: recipe error, kept as invalid attempts
  for a in i386 x86_64; do
    x=${a:0:1}${AFMSFX:-}
    run "mdc$x" ${CAND:-ref} $a b13-afm 60 component
    run "mdt$x" ${CAND:-ref} $a b13-afm 60 tables
    run "mdw$x" ${CAND:-ref} $a b13-afm 60 ext wav
    run "mdz$x" ${CAND:-ref} $a b13-afm 60 ext zzzq
    run "mdo$x" ${CAND:-ref} $a b13-afm 60 open "$M"
  done ;;
*) exit 2 ;;
esac
