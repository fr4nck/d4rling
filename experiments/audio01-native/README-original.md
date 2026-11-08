# D4RLING-AUDIO-01 — native PulseAudio witness

## Objective and scope

Confirm the Linux-host sound path first: Python (Linux ELF64) → `libpulse-simple.so.0` → PulseAudio (WSLg if configured) → Windows audio device. The script does **not** invoke Darling, Darwin, CoreAudio, QuickTime or JACK. This is prerequisite A0, not completion of the i386 target.

The sample is generated in memory with the Python standard library. No package is downloaded/installed. The script does not touch Git, existing build trees, WSL configuration, system services, or protected working files. It does not write reports by default (JSON printed to stdout). Sound can be played only with `--play`.

### Debian 13 / WSL2

1. Save `audio01_native.py` to your Linux home, for example as `~/d4rling-audio01/audio01_native.py`. This file transfer/download is a **manual user action**.
2. Run in Bash:

```bash
# ===========================================================
# D4RLING-AUDIO-01 / 5700X / Debian 13 WSL2 / Bash
# Files touched: none. Downloads/install: none.
# ===========================================================
cd "$HOME"
python3 "$HOME/d4rling-audio01/audio01_native.py" --self-test
python3 "$HOME/d4rling-audio01/audio01_native.py" --probe
# Sound is only played on the following explicit command:
timeout --signal=TERM --kill-after=2s 12s python3 "$HOME/d4rling-audio01/audio01_native.py" --play
```

A `PCM_SENT_TO_PULSE_SERVER_AUDIBILITY_UNVERIFIED` result means PCM was accepted and drained by PulseAudio, not that sound was audible. User confirmation is required. `ERROR_PULSE_CONNECTION` indicates client/server routing failed; `BLOCKED_NATIVE_LIBPULSE_MISSING` indicates the client shared library is not installed. Do not install packages just to obtain a PASS without checking and approving them first.

### Results gates

- **A0 (native Linux)**: tone heard + stream accepted/drained: confirmed by a human and report; otherwise record the exact error. This does not validate Darling.
- **A1 (Darling x86_64)**: a guest Mach-O calls CoreAudio HAL; trace shows callback → PCM → PulseAudio, plus audible output.
- **A2 (Darling i386)**: the *same* guest API test runs through i386 Darwin ABI and an authenticated/validated audio backend; the ELF32/ELF64 dependency bridge is not assumed to exist.
- **A3 (file)**: read a small WAV/AIFF from a Darwin application; only then attempt QuickTime.

Reference: `fr4nck/d4rling/PROJECT_STATE.md`, `reproduction/README.md`, and `docs/d4rling-reprise-2026-10-29.md`. Preserving the nine locally protected files remains mandatory.
