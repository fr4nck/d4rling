#!/usr/bin/env bash
# Build the Mach-O i386 dyld-dispatcher probe (lot X2).
# Required environment:
#   SDK      macOS SDK root providing usr/include (headers only)
#   LD64     cctools ld64 built by Darling (…/cctools/ld64/src/x86_64-apple-darwin20-ld)
#   SYSROOT  <darling install>/libexec/darling (link-time libSystem only)
# Usage: build-probe.sh OUT_DIR   (OUT_DIR must not exist)
set -Eeuo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="${1:?usage: build-probe.sh OUT_DIR}"
: "${SDK:?SDK is required}" "${LD64:?LD64 is required}" "${SYSROOT:?SYSROOT is required}"
test ! -e "$out"
mkdir -p "$out"
clang-19 -target i386-apple-darwin -mmacosx-version-min=10.9 -isysroot "$SDK" -O1 -g0 \
	-Wall -Wextra -Wno-deprecated-declarations -fno-stack-protector \
	-c "$here/dyld-dispatcher-probe.c" -o "$out/dyld-dispatcher-probe.o"
"$LD64" -arch i386 -macosx_version_min 10.9 -sdk_version 10.9 -syslibroot "$SYSROOT" \
	-L "$SYSROOT/usr/lib" -undefined error -o "$out/dyld-dispatcher-probe" "$out/dyld-dispatcher-probe.o" -lSystem
(cd "$out" && sha256sum dyld-dispatcher-probe) | tee "$out/SHA256SUMS"
