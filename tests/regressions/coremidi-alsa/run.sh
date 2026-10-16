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
REVERSE=$(mktemp "${TMPDIR:-/tmp}/d4rling-midi-reverse-XXXXXX")
DELIVERY=$(mktemp "${TMPDIR:-/tmp}/d4rling-midi-delivery-XXXXXX")
SOURCE_ROUTE=$(mktemp "${TMPDIR:-/tmp}/d4rling-midi-source-route-XXXXXX")
SOURCE_LIFETIME=$(mktemp "${TMPDIR:-/tmp}/d4rling-midi-source-lifetime-XXXXXX")
SOURCE_FILTER=$(mktemp "${TMPDIR:-/tmp}/d4rling-midi-source-filter-XXXXXX")
INPUT_PUMP=$(mktemp "${TMPDIR:-/tmp}/d4rling-midi-input-pump-XXXXXX")
INPUT_SESSION=$(mktemp "${TMPDIR:-/tmp}/d4rling-midi-input-session-XXXXXX")
trap 'rm -f "$OUT" "$PREFLIGHT" "$TRANSLATE" "$REVERSE" "$DELIVERY" "$SOURCE_ROUTE" "$SOURCE_LIFETIME" "$SOURCE_FILTER" "$INPUT_PUMP" "$INPUT_SESSION"' EXIT HUP INT TERM
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
# Encode ALSA events back to complete MIDI 1.0 channel messages.
"$CC" -std=c11 -DDARLING_COREMIDI_WITH_ALSA=1 \
    -Wall -Wextra -Werror -pthread \
    -I"$ROOT/tests/regressions/coremidi-virtual/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/src" \
    $(pkg-config --cflags alsa) \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIVirtual.c" \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIAlsaBridge.c" \
    "$ROOT/tests/regressions/coremidi-alsa/host_reverse.c" \
    -o "$REVERSE" $(pkg-config --libs alsa)
"$REVERSE"
# Deliver synthetic ALSA events through MIDIReceived to connected input ports.
"$CC" -std=c11 -DDARLING_COREMIDI_WITH_ALSA=1 \
    -Wall -Wextra -Werror -pthread \
    -I"$ROOT/tests/regressions/coremidi-virtual/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/src" \
    $(pkg-config --cflags alsa) \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIVirtual.c" \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIAlsaBridge.c" \
    "$ROOT/tests/regressions/coremidi-alsa/host_delivery.c" \
    -o "$DELIVERY" $(pkg-config --libs alsa)
"$DELIVERY"
# Verify explicit ALSA sender client/port to virtual CoreMIDI source routing.
"$CC" -std=c11 -DDARLING_COREMIDI_WITH_ALSA=1 \
    -Wall -Wextra -Werror -pthread \
    -I"$ROOT/tests/regressions/coremidi-virtual/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/src" \
    $(pkg-config --cflags alsa) \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIVirtual.c" \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIAlsaBridge.c" \
    "$ROOT/tests/regressions/coremidi-alsa/host_source_route.c" \
    -o "$SOURCE_ROUTE" $(pkg-config --libs alsa)
"$SOURCE_ROUTE"
# Source IDs must be purged when a virtual endpoint or owner client is disposed.
"$CC" -std=c11 -DDARLING_COREMIDI_WITH_ALSA=1 \
    -Wall -Wextra -Werror -pthread \
    -I"$ROOT/tests/regressions/coremidi-virtual/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/src" \
    $(pkg-config --cflags alsa) \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIVirtual.c" \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIAlsaBridge.c" \
    "$ROOT/tests/regressions/coremidi-alsa/host_source_lifetime.c" \
    -o "$SOURCE_LIFETIME" $(pkg-config --libs alsa)
"$SOURCE_LIFETIME"
# Use genuine ALSA port-info types to select readable, subscribable
# sources before any real sequencer access.
"$CC" -std=c11 -DDARLING_COREMIDI_WITH_ALSA=1 \
    -Wall -Wextra -Werror -pthread \
    -I"$ROOT/tests/regressions/coremidi-virtual/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/src" \
    $(pkg-config --cflags alsa) \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIVirtual.c" \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIAlsaBridge.c" \
    "$ROOT/tests/regressions/coremidi-alsa/host_source_filter.c" \
    -o "$SOURCE_FILTER" $(pkg-config --libs alsa)
"$SOURCE_FILTER"
# Consume injected nonblocking ALSA input events without opening /dev/snd/seq.
# Intercept only snd_seq_event_input; use the genuine ALSA types/library.
"$CC" -std=c11 -DDARLING_COREMIDI_WITH_ALSA=1 \
    -Wall -Wextra -Werror -pthread \
    -I"$ROOT/tests/regressions/coremidi-virtual/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/src" \
    $(pkg-config --cflags alsa) \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIVirtual.c" \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIAlsaBridge.c" \
    "$ROOT/tests/regressions/coremidi-alsa/host_input_pump.c" \
    -Wl,--wrap=snd_seq_event_input -o "$INPUT_PUMP" $(pkg-config --libs alsa)
"$INPUT_PUMP"
# Exercise the native input session lifecycle with genuine ALSA types while
# wrapping ONLY the device-facing operations. No /dev/snd/seq is opened.
"$CC" -std=c11 -DDARLING_COREMIDI_WITH_ALSA=1 \
    -Wall -Wextra -Werror -pthread \
    -I"$ROOT/tests/regressions/coremidi-virtual/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/include" \
    -I"$ROOT/src/frameworks/CoreMIDI/src" \
    $(pkg-config --cflags alsa) \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIVirtual.c" \
    "$ROOT/src/frameworks/CoreMIDI/src/MIDIAlsaBridge.c" \
    "$ROOT/tests/regressions/coremidi-alsa/host_input_session.c" \
    -Wl,--wrap=snd_seq_open \
    -Wl,--wrap=snd_seq_set_client_name \
    -Wl,--wrap=snd_seq_create_simple_port \
    -Wl,--wrap=snd_seq_get_any_port_info \
    -Wl,--wrap=snd_seq_connect_from \
    -Wl,--wrap=snd_seq_disconnect_from \
    -Wl,--wrap=snd_seq_event_input \
    -Wl,--wrap=snd_seq_poll_descriptors_count \
    -Wl,--wrap=snd_seq_poll_descriptors \
    -Wl,--wrap=snd_seq_close \
    -o "$INPUT_SESSION" $(pkg-config --libs alsa)
"$INPUT_SESSION"
# Check PIC shared linking/loading with ALSA both disabled and enabled.
sh "$ROOT/tests/regressions/coremidi-shared/run.sh"
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
