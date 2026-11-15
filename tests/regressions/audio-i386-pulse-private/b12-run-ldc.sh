#!/usr/bin/env bash
# AUDIO-I386 replay of QT-B12: MOV -> QuickTime -> CoreAudio -> PulseAudio (WSLg),
# with a private ELF32 ld.so.cache (LDCACHE, required) and optional LAYER (TLV libdyld).
# Usage: b12-run.sh LABEL i386|x86_64 play|stoprestart [CAPTURE_SECONDS]
# Env: PULSE_SERVER (guest), LDCACHE (private cache), LAYER (optional overlay).
# Host observer (pa-tool) uses the host libpulse; it never plays audio.
set -Eeuo pipefail
B=${B12_STAGE:-$HOME/d4wrling-work/validation/quicktime-b12-20261114}
W=${AUDIO_STAGE:-$HOME/d4wrling-work/validation/audio-i386-deps-20261114}
: "${LDCACHE:?LDCACHE is required}"
L=${1:?label}; A=${2:?arch}; M=${3:?mode}; CAP=${4:-8}
O=$W/runs/b12/$L; test ! -e "$O"; mkdir -p "$O"
PT="env PULSE_SERVER=unix:/mnt/wslg/PulseServer $B/build/pa-tool"
{ $PT info; $PT inputs; } > "$O/pa-before.txt" 2>&1 || true
$PT record "$CAP" "$O/monitor.raw" > "$O/pa-record.txt" 2>&1 &
rp=$!
( sleep 3.2; $PT inputs > "$O/pa-during.txt" 2>&1 ) &
ip=$!
sleep 0.3
bash "$W/tools/run-ldc.sh" "$L" "$B/build/b12-play-$A" normal 60 \
  "/Volumes/SystemRoot$B/media/demo.mov" "/Volumes/SystemRoot$O" "$M" > "$O/run.log"
wait "$ip" || true
set +e; wait "$rp"; rrc=$?; set -e
sleep 0.5
$PT inputs > "$O/pa-after.txt" 2>&1 || true
G=$W/runs/guest/$L
cp "$G/stdout.log" "$O/guest.stdout.log"; cp "$G/stderr.log" "$O/guest.stderr.log"; cp "$G/meta.txt" "$O/guest.meta.txt"; cp "$G/rc" "$O/guest.rc"
sha256sum "$O/monitor.raw" "$O"/gms.pcm 2>/dev/null > "$O/SHA256SUMS" || true
{
  echo "label=$L arch=$A mode=$M layer=${LAYER:-none} ldcache=$(sha256sum "$LDCACHE" | cut -d' ' -f1) pulse_server=${PULSE_SERVER:-unset}"
  echo "guest_rc=$(cat "$G/rc") $(grep -E '^B12_SUMMARY' "$G/stdout.log")"
  echo "record_rc=$rrc $(cat "$O/pa-record.txt")"
  echo "during: $(tr '\n' ' ' < "$O/pa-during.txt")"
  echo "after: $(tr '\n' ' ' < "$O/pa-after.txt")"
  grep -E 'mounts_after|residual|seconds' "$G/meta.txt" | tr '\n' ' '; echo
  test -f "$O/gms.pcm" && python3 -I "$B/probe/verify_audio.py" pcm "$B/media/demo.json" "$O/gms.pcm" | head -1
  python3 -I "$B/probe/verify_audio.py" capture "$B/media/demo.json" "$O/monitor.raw" "$M"
} | tee "$O/summary.txt"
