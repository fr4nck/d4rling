#!/bin/sh
# Isolated source test (does not require Darling runtime or a MIDI device).
set -eu
cd "$(dirname "$0")/../../.."
ROOT=$(pwd)
CC=${CC:-clang}
OUT=$(mktemp "${TMPDIR:-/tmp}/d4rling-midi-XXXXXX")
REENTRANT=$(mktemp "${TMPDIR:-/tmp}/d4rling-midi-reentrant-XXXXXX")
trap 'rm -f "$OUT" "$REENTRANT"' EXIT HUP INT TERM
"$CC" -std=c11 -Wall -Wextra -Werror -pthread \
  -I"$ROOT/tests/regressions/coremidi-virtual/include" \
  -I"$ROOT/src/frameworks/CoreMIDI/include" \
  -x c "$ROOT/src/frameworks/CoreMIDI/src/MIDIVirtual.c" \
  "$ROOT/src/frameworks/CoreMIDI/src/MIDIAlsaBridge.c" \
  "$ROOT/tests/regressions/coremidi-virtual/test.c" -o "$OUT"
"$OUT"
# Reentrant callbacks must not invoke stale disconnected recipients.
"$CC" -std=c11 -Wall -Wextra -Werror -pthread \
  -I"$ROOT/tests/regressions/coremidi-virtual/include" \
  -I"$ROOT/src/frameworks/CoreMIDI/include" \
  -x c "$ROOT/src/frameworks/CoreMIDI/src/MIDIVirtual.c" \
  "$ROOT/src/frameworks/CoreMIDI/src/MIDIAlsaBridge.c" \
  "$ROOT/tests/regressions/coremidi-virtual/reentrant.c" -o "$REENTRANT"
"$REENTRANT"
