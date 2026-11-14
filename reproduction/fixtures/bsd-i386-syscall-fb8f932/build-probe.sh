#!/usr/bin/env bash
# Build the Mach-O i386 BSD probe and the host setgroups() preflight.
#
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
	-Wall -Wno-deprecated-declarations -fno-stack-protector \
	-c "$here/bsd-i386-probe.c" -o "$out/bsd-i386-probe.o"
"$LD64" -arch i386 -macosx_version_min 10.9 -sdk_version 10.9 -syslibroot "$SYSROOT" \
	-L "$SYSROOT/usr/lib" -undefined error -o "$out/bsd-i386-probe" "$out/bsd-i386-probe.o" -lSystem
cc -O1 -Wall -o "$out/setgroups-probe" "$here/setgroups-probe.c"
(cd "$out" && sha256sum bsd-i386-probe setgroups-probe) | tee "$out/SHA256SUMS"
