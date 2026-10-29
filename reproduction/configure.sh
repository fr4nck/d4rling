#!/usr/bin/env bash
# Configure a NEW build tree. Never installs or starts Darling.
set -Eeuo pipefail
test "$#" = 3 || { echo "usage: bash configure.sh SOURCE NEW_BUILD core-i386|core-x64|audio-x64" >&2; exit 2; }
source_dir="$(realpath "$1")"
build_dir="$(realpath -m "$2")"
profile="$3"
test -f "$source_dir/D4RLING-REPRODUCTION.json"
test ! -e "$build_dir"
test ! -L "$build_dir"
case "$build_dir/" in "$source_dir/"*) echo "out-of-source build required" >&2; exit 2;; esac
case "$profile" in
 core-i386) components=core; i386=ON; build_type=Debug;;
 core-x64) components=core; i386=OFF; build_type=Debug;;
 audio-x64) components=gui; i386=OFF; build_type=Debug;;
 *) echo "unknown profile" >&2; exit 2;;
esac
cmake -S "$source_dir" -B "$build_dir" -G Ninja \
 -DCMAKE_C_COMPILER=/usr/bin/clang-19 \
 -DCMAKE_CXX_COMPILER=/usr/bin/clang++-19 \
 -DCMAKE_BUILD_TYPE="$build_type" -DCOMPONENTS="$components" \
 -DTARGET_x86_64=ON -DTARGET_i386="$i386" \
 -DCMAKE_INSTALL_PREFIX="$build_dir/private-install" \
 -DDEBIAN_PACKAGING=ON \
 -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 \
 -DCOMPILE_PY2_BYTECODE=OFF -DENABLE_METAL=OFF
printf 'Configured %s. Build targets explicitly; no installation or runtime was performed.\n' "$build_dir"
