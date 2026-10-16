#!/bin/sh
# Isolated native ALSA test; does not build Darling or access a physical device.
set -eu
cd "$(dirname "$0")/../../.."
ROOT=$(pwd)
if ! command -v pkg-config >/dev/null 2>&1 || ! pkg-config --exists alsa; then
    echo "ALSA_COMPILE_SKIP: pkg-config ALSA development files not found"
    exit 77
fi
CC=${CC:-cc}
OUT=$(mktemp "${TMPDIR:-/tmp}/d4rling-midi-alsa-XXXXXX")
PREFLIGHT=$(mktemp "${TMPDIR:-/tmp}/d4rling-midi-preflight-XXXXXX")
TRANSLATE=$(mktemp "${TMPDIR:-/tmp}/d4rling-midi-translation-XXXXXX")
trap 'rm -f "$OUT" "$PREFLIGHT" "$TRANSLATE"' EXIT HUP INT TERM
"$CC" -std=c11 -DDARLING_COREMIDI_WITH_ALSA=1 \
    -Wall -Wextra -Werror -pthread \
    -I"$ROOT/tests/regressions/coremidi-virtual/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/src" \
    $(pkg-config --cflags alsa) \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIVirtual.c" \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIAlsaBridge.c" \
    "$ROOT/tests/regressions/coremidi-alsa/host_loopback.c" \
    -o "$OUT" $(pkg-config --libs alsa)
echo "ALSA_COMPILE_PASS: compiled against system ALSA development files"
# Exercise MIDI -> ALSA conversion on the production bridge without /dev/snd/seq.
"$CC" -std=c11 -DDARLING_COREMIDI_WITH_ALSA=1 \
    -Wall -Wextra -Werror -pthread \
    -I"$ROOT/tests/regressions/coremidi-virtual/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/src" \
    $(pkg-config --cflags alsa) \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIVirtual.c" \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIAlsaBridge.c" \
    "$ROOT/tests/regressions/coremidi-alsa/host_translation.c" \
    -o "$TRANSLATE" $(pkg-config --libs alsa)
"$TRANSLATE"
# Link the same real bridge against libasound, but wrap only snd_seq_open.
# This verifies rejection of malformed MIDI without a sequencer device.
"$CC" -std=c11 -DDARLING_COREMIDI_WITH_ALSA=1 \
    -Wall -Wextra -Werror -pthread \
    -I"$ROOT/tests/regressions/coremidi-virtual/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/src" \
    $(pkg-config --cflags alsa) \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIVirtual.c" \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIAlsaBridge.c" \
    "$ROOT/tests/regressions/coremidi-alsa/host_preflight.c" \
    -Wl,--wrap=snd_seq_open -o "$PREFLIGHT" $(pkg-config --libs alsa)
"$PREFLIGHT"
if [ ! -e /dev/snd/seq ]; then
    echo "ALSA_RUNTIME_SKIP: /dev/snd/seq unavailable (WSL2 or kernel configuration)"
    exit 77
fi
"$OUT"
