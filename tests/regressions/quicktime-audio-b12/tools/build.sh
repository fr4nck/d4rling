#!/usr/bin/env bash
# QT-B12: Mach-O witness against the frameworks INSTALLED by the private build.
# Usage: build.sh i386|x86_64 OUT_DIR SOURCE.c [frameworks...]
set -Eeuo pipefail
Q=/home/Deniel/d4wrling-work/validation/quicktime-b11e-20261114
INST=$Q/build-gui/private-install/libexec/darling
LD=$Q/build-gui/src/external/cctools-port/cctools/ld64/src/x86_64-apple-darwin20-ld
SDK=/home/Deniel/d4rling-ui/d4rling-carbon-qualif/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
S=$Q/src
A=$1; OUT=$2; SRC=$(realpath "$3"); shift 3
case $A in i386) T=(-target i386-apple-darwin -mmacosx-version-min=10.9);; x86_64) T=(-target x86_64-apple-macosx10.9 -DPLATFORM_MacOSX);; *) exit 2;; esac
mkdir -p "$OUT"; n=$(basename "$SRC" .c)
fw=(); for f in "$@"; do fw+=(-framework "$f"); done
LANGF=(-std=gnu11); [ "${CXX:-0}" = 1 ] && LANGF=(-x c++ -std=gnu++17)
clang-19 "${T[@]}" "${LANGF[@]}" ${EXTRA_CFLAGS:-} -O1 -g -fno-stack-protector -isysroot "$SDK" \
  -I "$S/src/frameworks/QuickTime/include" -I "$S/src/frameworks/CoreServices/include" -I "$S/basic-headers" \
  -Wall -Werror=implicit-function-declaration -c "$SRC" -o "$OUT/$n-$A.o" 2> "$OUT/$n-$A-compile.log"
"$LD" -arch $A -macosx_version_min 10.9 -sdk_version 11.0 -syslibroot "$INST" -L "$INST/usr/lib" -F "$INST/System/Library/Frameworks" \
  -pie -e _main -o "$OUT/$n-$A" "$OUT/$n-$A.o" "${fw[@]}" "$INST/usr/lib/libSystem.B.dylib" ${CXX:+"$INST/usr/lib/libc++.1.dylib"} 2> "$OUT/$n-$A-link.log"
sha256sum "$SRC" "$OUT/$n-$A" > "$OUT/$n-$A.SHA256SUMS"
echo "BUILT $OUT/$n-$A"
