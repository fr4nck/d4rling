#!/bin/sh
# Shared ELF linkage smoke: host-built, not a Darling Mach-O framework build.
set -eu
cd "$(dirname "$0")/../../.."
ROOT=$(pwd)
CC=${CC:-cc}
if ! command -v pkg-config >/dev/null 2>&1 || ! pkg-config --exists alsa; then
    echo "COREMIDI_SHARED_SKIP: ALSA development files not available"
    exit 77
fi
WORK=$(mktemp -d "${TMPDIR:-/tmp}/d4rling-coremidi-shared-XXXXXX")
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
INCLUDE="-I$ROOT/tests/regressions/coremidi-virtual/include"
CORE="-I$ROOT/src/frameworks/CoreMIDI/include"
INTERNAL="-I$ROOT/src/frameworks/CoreMIDI/src"
VIRTUAL="$ROOT/src/frameworks/CoreMIDI/src/MIDIVirtual.c"
BRIDGE="$ROOT/src/frameworks/CoreMIDI/src/MIDIAlsaBridge.c"
HOST="$ROOT/tests/regressions/coremidi-shared/host_dynamic.c"

# Fail the shared-library link on unresolved references (two build modes).
"$CC" -std=c11 -Wall -Wextra -Werror -fPIC -pthread \
    $INCLUDE $CORE $INTERNAL -shared -Wl,-z,defs \
    "$VIRTUAL" "$BRIDGE" -o "$WORK/coremidi-noalsa.so"
"$CC" -std=c11 -Wall -Wextra -Werror -fPIC -pthread \
    -DDARLING_COREMIDI_WITH_ALSA=1 $INCLUDE $CORE $INTERNAL \
    $(pkg-config --cflags alsa) -shared -Wl,-z,defs \
    "$VIRTUAL" "$BRIDGE" -o "$WORK/coremidi-alsa.so" \
    $(pkg-config --libs alsa)
"$CC" -std=c11 -Wall -Wextra -Werror -pthread \
    $INCLUDE $CORE "$HOST" -o "$WORK/host-dynamic" -ldl
"$WORK/host-dynamic" "$WORK/coremidi-noalsa.so"
"$WORK/host-dynamic" "$WORK/coremidi-alsa.so"
echo "COREMIDI_SHARED_PASS: PIC/ELF linked in ALSA off/on configurations"
