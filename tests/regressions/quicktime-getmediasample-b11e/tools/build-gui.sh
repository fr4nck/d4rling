#!/usr/bin/env bash
# QT-B11E-R3: private CMake/Ninja gui_stubs build of the B11E worktree, same
# cache options as validation/upstream-sync-20261114/build-gui-i386.
# Writes only $Q/build-gui (and its private-install). Usage: build-gui.sh [configure|build|install]
set -Eeuo pipefail
Q=/home/Deniel/d4wrling-work/validation/quicktime-b11e-20261114
B=$Q/build-gui
mkdir -p "$B"; cd "$B"
case "${1:-build}" in
configure)
  cmake -G Ninja -S "$Q/src" -B "$B" \
    -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=/usr/bin/clang-19 -DCMAKE_CXX_COMPILER=/usr/bin/clang++-19 \
    -DCMAKE_INSTALL_PREFIX="$B/private-install" -DCOMPONENTS=gui_stubs \
    -DD4RLING_MLDR_I386_MMAP_DIAG=OFF -DDEBIAN_PACKAGING=ON -DENABLE_METAL=OFF -DENABLE_TESTS=OFF \
    -DREGENERATE_SDK=OFF -DTARGET_ARM64=OFF -DTARGET_i386=ON -DTARGET_x86_64=ON ;;
build) ninja -j 14 ;;
install) ninja -j 14 install ;;
*) ninja -j 14 "$@" ;;
esac
