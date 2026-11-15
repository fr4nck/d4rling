#!/usr/bin/env bash
# B13 guest run: B12/AUDIO-I386 bench (delegated ids, private mount namespace, optional
# LDCACHE and LAYER), installation of the B11E/B12 private build. Outputs in the B13 stage.
# Usage: run-b13.sh LABEL PROGRAM normal|bypass SECONDS [ARGS...]   (keep LABEL short)
set -Eeuo pipefail
T=${B13_STAGE:-$HOME/d4wrling-work/validation/audiotoolbox-b13-20261115}
export INST=${INST:-$HOME/d4wrling-work/validation/quicktime-b11e-20261114/build-gui/private-install}
export SGPROBE=${SGPROBE:-$HOME/d4wrling-work/validation/xnu-e72d43f-integration-20261114/replay-build/setgroups-probe}
export OUT_ROOT=$T/runs/guest PREFIX_ROOT=$T/p
mkdir -p "$OUT_ROOT" "$PREFIX_ROOT"
exec bash "$T/tools/run-guest-ldc.sh" "$@"
