#!/usr/bin/env bash
# B13-INT: private CMake/Ninja gui_stubs build of master (B13 worktree), same cache options as
# the B11E build (quicktime-b11e-20261114/tools/build-gui.sh). Writes only $T/mbuild.
set -Eeuo pipefail
T=$HOME/d4wrling-work/validation/audiotoolbox-b13-20261115
B=$T/mbuild
mkdir -p "$B"; cd "$B"
case "${1:-build}" in
configure)
  cmake -G Ninja -S "$T/src" -B "$B" \
    -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=/usr/bin/clang-19 -DCMAKE_CXX_COMPILER=/usr/bin/clang++-19 \
    -DCMAKE_INSTALL_PREFIX="$B/private-install" -DCOMPONENTS=gui_stubs \
    -DD4RLING_MLDR_I386_MMAP_DIAG=OFF -DDEBIAN_PACKAGING=ON -DENABLE_METAL=OFF -DENABLE_TESTS=OFF \
    -DREGENERATE_SDK=OFF -DTARGET_ARM64=OFF -DTARGET_i386=ON -DTARGET_x86_64=ON ;;
build) ninja -j 14 ;;
install) ninja -j 14 install ;;
*) ninja -j 14 "$@" ;;
esac
