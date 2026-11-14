#!/usr/bin/env bash
# QT-B11E guest run through the versioned rootless bench
# (reproduction/fixtures/bsd-i386-syscall-fb8f932/run-guest.sh, copied in
# fixture/ with its SHA-256 checked). INST = private install of the B11E
# CMake/Ninja build; no overlay layer. Usage: run-guest.sh LABEL PROGRAM normal|bypass SECONDS [ARGS...]
set -Eeuo pipefail
Q=/home/Deniel/d4wrling-work/validation/quicktime-b11e-20261114
F=$Q/src/reproduction/fixtures/bsd-i386-syscall-fb8f932
grep -q " run-guest.sh$" "$F/SHA256SUMS" && (cd "$F" && grep " run-guest.sh$" SHA256SUMS | sha256sum -c --quiet -)
export INST=$Q/build-gui/private-install
export SGPROBE=/home/Deniel/d4wrling-work/validation/xnu-e72d43f-integration-20261114/replay-build/setgroups-probe
export OUT_ROOT=$Q/runs/guest
export PREFIX_ROOT=$Q/p
mkdir -p "$OUT_ROOT" "$PREFIX_ROOT"
exec bash "$F/run-guest.sh" "$@"
