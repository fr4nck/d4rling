#!/usr/bin/env bash
# B13-D: audio file -> AudioToolbox (ExtAudioFile + AudioConverter) -> CoreAudio -> PulseAudio
# (WSLg), with the private ELF32 ld.so.cache (LDCACHE, required) and optional LAYER.
# Usage: b13-play-run.sh LABEL i386|x86_64 play|stoprestart [CAPTURE_SECONDS] [FILE]
# Env: PULSE_SERVER (guest), LDCACHE (private cache), LAYER (optional overlay).
# Host observer (pa-tool) uses the host libpulse; it never plays audio.
set -Eeuo pipefail
B=${B12_STAGE:-$HOME/d4wrling-work/validation/quicktime-b12-20261114}
W=${B13_STAGE:-$HOME/d4wrling-work/validation/audiotoolbox-b13-20261115}
: "${LDCACHE:?LDCACHE is required}"
L=${1:?label}; A=${2:?arch}; M=${3:?mode}; CAP=${4:-8}; F=${5:-demo-s16.aiff}
O=$W/runs/play/$L; test ! -e "$O"; mkdir -p "$O"
PT="env PULSE_SERVER=unix:/mnt/wslg/PulseServer $B/build/pa-tool"
{ $PT info; $PT inputs; } > "$O/pa-before.txt" 2>&1 || true
$PT record "$CAP" "$O/monitor.raw" > "$O/pa-record.txt" 2>&1 &
rp=$!
( sleep 3.2; $PT inputs > "$O/pa-during.txt" 2>&1 ) &
ip=$!
sleep 0.3
bash "$W/tools/run-b13.sh" "$L" "$W/build/b13-atb-$A" normal 60 \
  play "/Volumes/SystemRoot$W/media" "/Volumes/SystemRoot$O" "$M" "$F" > "$O/run.log"
wait "$ip" || true
set +e; wait "$rp"; rrc=$?; set -e
sleep 0.5
$PT inputs > "$O/pa-after.txt" 2>&1 || true
G=$W/runs/guest/$L
cp "$G/stdout.log" "$O/guest.stdout.log"; cp "$G/stderr.log" "$O/guest.stderr.log"; cp "$G/meta.txt" "$O/guest.meta.txt"; cp "$G/rc" "$O/guest.rc"
sha256sum "$O/monitor.raw" "$O"/decoded.s16le 2>/dev/null > "$O/SHA256SUMS" || true
{
  echo "label=$L arch=$A mode=$M layer=${LAYER:-none} ldcache=$(sha256sum "$LDCACHE" | cut -d' ' -f1) pulse_server=${PULSE_SERVER:-unset}"
  echo "guest_rc=$(cat "$G/rc") $(grep -E '^B13_SUMMARY' "$G/stdout.log")"
  echo "record_rc=$rrc $(cat "$O/pa-record.txt")"
  echo "during: $(tr '\n' ' ' < "$O/pa-during.txt")"
  echo "after: $(tr '\n' ' ' < "$O/pa-after.txt")"
  grep -E 'mounts_after|residual|seconds' "$G/meta.txt" | tr '\n' ' '; echo
  echo "decoded_sha256=$(sha256sum "$O/decoded.s16le" 2>/dev/null | cut -d' ' -f1)"
  python3 -I "$B/probe/verify_audio.py" capture "$B/media/demo.json" "$O/monitor.raw" "$M"
  python3 -I "$B/probe/bitexact.py" "${REF:-$W/media/ref-s16be.raw}" "$O/monitor.raw"
} | tee "$O/summary.txt"
