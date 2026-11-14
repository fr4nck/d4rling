#!/usr/bin/env bash
# QT-B12 guest run: B11E private install of master 2f837e88 (official libdyld);
# LAYER=$B/layers/libdyld-tlvfs selects the private TLV-fixed libdyld overlay.
# Usage: run.sh LABEL PROGRAM normal|bypass SECONDS [ARGS...]   (keep LABEL short)
set -Eeuo pipefail
B=/home/Deniel/d4wrling-work/validation/quicktime-b12-20261114
export INST=/home/Deniel/d4wrling-work/validation/quicktime-b11e-20261114/build-gui/private-install
export SGPROBE=/home/Deniel/d4wrling-work/validation/xnu-e72d43f-integration-20261114/replay-build/setgroups-probe
export OUT_ROOT=$B/runs/guest PREFIX_ROOT=$B/p
mkdir -p "$OUT_ROOT" "$PREFIX_ROOT"
exec bash "$B/tools/run-guest-audio.sh" "$@"
