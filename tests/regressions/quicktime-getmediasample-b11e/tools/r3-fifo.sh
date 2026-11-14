#!/usr/bin/env bash
# QT-B11E-R3: replay MOV -> GetMediaSample (production framework) -> HAL -> FIFO
# for the six B11E MOV files, without any PCM injection.
# Reused read-only: B11C-R2 hal.o, CoreAudio-B14.dylib, libpulse-B14.dylib (copied
# beside the program for @executable_path, SHA-256 recorded), the B0608-R5
# simulated host mock_host.py and the six B11C-R2 FIFO oracles oracle-N.json,
# computed in B11C for the same six PCM vectors injected after GetMediaSample.
# Usage: r3-fifo.sh LABEL [MOV_DIR]
set -Eeuo pipefail
umask 077
export LC_ALL=C
Q=/home/Deniel/d4wrling-work/validation/quicktime-b11e-20261114
G=/home/Deniel/d4wrling-work/validation/5700x-10400-convergence/quicktime-c3-m3/g2.0Tfg9onI
B11C=$G/qt-b11c-r2.takcqo1a
MOCK=$G/qt-batch-b0608-r5.pkA8UB1m/mock_host.py
L=${1:?label}; MOVS=$(realpath "${2:-$Q/runs/r1-r1-clang-x64}")
O=$Q/runs/r3f-$L; test ! -e "$O"; mkdir -p "$O/bin"
cp "$B11C/CoreAudio-B14.dylib" "$B11C/libpulse-B14.dylib" "$O/bin/"
SDK=/home/Deniel/d4rling-ui/d4rling-carbon-qualif/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
INST=$Q/build-gui/private-install/libexec/darling
LD=$Q/build-gui/src/external/cctools-port/cctools/ld64/src/x86_64-apple-darwin20-ld
S=$Q/src
clang-19 -target i386-apple-darwin -mmacosx-version-min=10.9 -std=gnu11 -O1 -g -fno-stack-protector -isysroot "$SDK" \
  -I "$S/src/frameworks/QuickTime/include" -I "$S/src/frameworks/CoreServices/include" -I "$S/basic-headers" \
  -Wall -Werror=implicit-function-declaration -c "$Q/probe/b11e-r3-fifo-chain.c" -o "$O/bin/chain.o" 2> "$O/compile.log"
"$LD" -arch i386 -macosx_version_min 10.9 -sdk_version 11.0 -syslibroot "$INST" -L "$INST/usr/lib" \
  -F "$INST/System/Library/Frameworks" -pie -e _main -o "$O/bin/b11e-r3-fifo-chain-i386" "$O/bin/chain.o" "$B11C/hal.o" \
  -framework QuickTime -framework CoreServices "$O/bin/CoreAudio-B14.dylib" "$O/bin/libpulse-B14.dylib" \
  "$INST/usr/lib/libSystem.B.dylib" 2> "$O/link.log"
sha256sum "$Q/probe/b11e-r3-fifo-chain.c" "$B11C/hal.o" "$B11C/hal.cpp" "$O/bin/"* "$MOCK" "$B11C"/oracle-*.json \
  "$INST/System/Library/Frameworks/QuickTime.framework/Versions/A/QuickTime" > "$O/SHA256SUMS"
for v in ${VECTORS:-0 1 2 3 4 5}; do
  d=$O/v$v; mkdir -p "$d"; mkfifo -m 600 "$d/audio.request" "$d/audio.reply"
  timeout 90 python3 -I "$MOCK" "$d/audio.request" "$d/audio.reply" "$B11C/oracle-$v.json" "$d/mock.result.json" \
    > "$d/mock.stdout.log" 2> "$d/mock.stderr.log" &
  mp=$!
  sleep 0.5
  bash "$Q/tools/run-guest.sh" "r3f-$L-v$v" "$O/bin/b11e-r3-fifo-chain-i386" normal 75 \
    "/Volumes/SystemRoot$MOVS" "$v" "/Volumes/SystemRoot$d/audio.request" "/Volumes/SystemRoot$d/audio.reply" > "$d/run.log"
  set +e; wait "$mp"; mrc=$?; set -e
  g=$Q/runs/guest/r3f-$L-v$v
  echo "v$v guest_rc=$(cat "$g/rc") mock_rc=$mrc mock=$(python3 -I -c 'import json,sys; r=json.load(open(sys.argv[1])); print(r.get("status"), r.get("sha256"), r.get("blocks"), r.get("bytes"))' "$d/mock.result.json" 2>/dev/null || echo none) oracle=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["sha256"])' "$B11C/oracle-$v.json") hal=$(grep -o 'R3_HAL_RC=[0-9]*' "$g/stdout.log" || true) selected=$(grep -o 'B11_VECTOR_SELECTED=[A-Z0-9]*' "$g/stdout.log" || true)"
done
