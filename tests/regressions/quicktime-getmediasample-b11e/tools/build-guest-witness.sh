#!/usr/bin/env bash
# QT-B11E: build a Mach-O i386 witness linked against the QuickTime.framework
# and CoreServices.framework INSTALLED by the private CMake/Ninja build
# (build-gui/private-install), libSystem from the same installation.
# Usage: build-guest-witness.sh OUT_DIR SOURCE.c [extra cc flags...]
set -Eeuo pipefail
umask 077
Q=/home/Deniel/d4wrling-work/validation/quicktime-b11e-20261114
S=$Q/src
INST=$Q/build-gui/private-install/libexec/darling
LD=$Q/build-gui/src/external/cctools-port/cctools/ld64/src/x86_64-apple-darwin20-ld
SDK=/home/Deniel/d4rling-ui/d4rling-carbon-qualif/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
OUT=${1:?out}; SRC=$(realpath "${2:?source}"); shift 2
FW=$INST/System/Library/Frameworks
mkdir -p "$OUT"
n=$(basename "$SRC" .c)
clang-19 -target i386-apple-darwin -mmacosx-version-min=10.9 -std=gnu11 -O1 -g -fno-stack-protector \
  -isysroot "$SDK" -I "$S/src/frameworks/QuickTime/include" -I "$S/src/frameworks/QuickTime/src" \
  -I "$S/src/frameworks/CoreServices/include" -I "$S/basic-headers" \
  -Wall -Werror=implicit-function-declaration "$@" -c "$SRC" -o "$OUT/$n.o" 2> "$OUT/$n-compile.log"
"$LD" -arch i386 -macosx_version_min 10.9 -sdk_version 11.0 -syslibroot "$INST" -L "$INST/usr/lib" -F "$FW" \
  -pie -e _main -o "$OUT/$n-i386" "$OUT/$n.o" -framework QuickTime -framework CoreServices \
  "$INST/usr/lib/libSystem.B.dylib" 2> "$OUT/$n-link.log"
sha256sum "$SRC" "$OUT/$n-i386" "$FW/QuickTime.framework/Versions/A/QuickTime" > "$OUT/$n.SHA256SUMS"
echo "BUILT $OUT/$n-i386"
