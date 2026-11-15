#!/usr/bin/env bash
# AUDIO-I386 guest run: same installation and bench as QT-B12 run.sh, plus LDCACHE.
# Usage: run-ldc.sh LABEL PROGRAM normal|bypass SECONDS [ARGS...]   (keep LABEL short)
set -Eeuo pipefail
W=${AUDIO_STAGE:-$HOME/d4wrling-work/validation/audio-i386-deps-20261114}
B=${B12_STAGE:-$HOME/d4wrling-work/validation/quicktime-b12-20261114}
export INST=${INST:-$HOME/d4wrling-work/validation/quicktime-b11e-20261114/build-gui/private-install}
export SGPROBE=${SGPROBE:-$HOME/d4wrling-work/validation/xnu-e72d43f-integration-20261114/replay-build/setgroups-probe}
export OUT_ROOT=$W/runs/guest PREFIX_ROOT=$B/p
mkdir -p "$OUT_ROOT" "$PREFIX_ROOT"
exec bash "$W/tools/run-guest-ldc.sh" "$@"
