#!/usr/bin/env python3
"""Bounded host WAV PCM16 notch using *unchanged* SoundHack RealFFT.

D4rling SH07 fixture, GPL-3.0-or-later. Not a Darling guest, not
SoundHack.app and not evidence of real audio device output.
"""

import argparse
import contextlib
import ctypes
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

from fft_host_probe import require_pinned, SOURCE_SHA, HEADER_SHA, Inconclusive as FFTInconclusive

MAX_INPUT_BYTES = 1024 * 1024
MAX_SAMPLES = 384000  # at most 8 s @ 48 kHz, 1-channel PCM16
FFT_SIZES = (256, 512, 1024, 2048)


class Inconclusive(Exception):
    pass


def read_wav(path):
    source = Path(path)
    if not source.is_file():
        raise Inconclusive("WAV input absent")
    if source.stat().st_size > MAX_INPUT_BYTES:
        raise Inconclusive("WAV input exceeds 1 MiB limit")
    try:
        with wave.open(str(source), "rb") as wav:
            if (wav.getnchannels() != 1 or wav.getsampwidth() != 2 or
                    wav.getcomptype() != "NONE"):
                raise Inconclusive("only mono, uncompressed, 16-bit PCM WAV supported")
            rate = wav.getframerate()
            n = wav.getnframes()
            if not (8000 <= rate <= 192000 and 1 <= n <= MAX_SAMPLES):
                raise Inconclusive("WAV sample-rate or frame-count out of bounds")
            raw = wav.readframes(n)
            if len(raw) != 2*n:
                raise Inconclusive("WAV payload truncated")
    except (EOFError, wave.Error, struct.error, OSError) as exc:
        raise Inconclusive("invalid WAV container: " + str(exc)) from exc
    ints = struct.unpack("<" + str(n) + "h", raw)
    return rate, [v / 32768.0 for v in ints]


def validate(rate, samples, notch_hz, fft_size, radius):
    if fft_size not in FFT_SIZES:
        raise Inconclusive("FFT size must be 256, 512, 1024 or 2048")
    if not math.isfinite(notch_hz) or notch_hz <= 0 or notch_hz >= rate/2:
        raise Inconclusive("notch frequency must be strictly between 0 and Nyquist")
    if isinstance(radius, bool) or not isinstance(radius, int) or not 0 <= radius <= 6:
        raise Inconclusive("notch radius must be an integer 0..6")
    central = round(notch_hz * fft_size / rate)
    if central - radius < 1 or central + radius >= fft_size//2:
        raise Inconclusive("notch bin range would touch DC or Nyquist")
    if len(samples) < 1 or len(samples) > MAX_SAMPLES:
        raise Inconclusive("sample count out of bounds")
    return central


@contextlib.contextmanager
def compiled_fft(math_dir, compiler=None):
    path = Path(math_dir)
    cpath = path / "FFT.c"
    hpath = path / "FFT.h"
    try:
        require_pinned(cpath, SOURCE_SHA)
        require_pinned(hpath, HEADER_SHA)
    except FFTInconclusive as exc:
        raise Inconclusive(str(exc)) from exc
    cc = compiler or shutil.which("cc")
    if not cc or not shutil.which(cc):
        raise Inconclusive("host C compiler unavailable")
    with tempfile.TemporaryDirectory(prefix="sh07-fft-") as tmp:
        helper = Path(tmp) / "globals.c"
        helper.write_text("float Pi = 3.14159265358979323846f;\n"
                          "float twoPi = 6.28318530717958647692f;\n", encoding="ascii")
        library = Path(tmp) / "soundhack_fft.so"
        try:
            result = subprocess.run([cc, "-std=c99", "-O1", "-fPIC", "-shared",
                                     "-o", str(library), str(cpath), str(helper), "-lm"],
                                    capture_output=True, text=True, timeout=30,
                                    check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Inconclusive("host C compilation failed: " + str(exc)) from exc
        if result.returncode:
            raise Inconclusive("host C compilation returned nonzero: " + result.stderr[-350:])
        try:
            lib = ctypes.CDLL(str(library))
            lib.InitFFTTable.argtypes = []
            lib.InitFFTTable.restype = None
            lib.RealFFT.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_long, ctypes.c_short]
            lib.RealFFT.restype = None
            lib.InitFFTTable()
        except (AttributeError, OSError) as exc:
            raise Inconclusive("invalid host DSP library: " + str(exc)) from exc
        yield lib


def notch_pcm(lib, samples, sample_rate, notch_hz, fft_size=1024, radius=2):
    """Periodic Hann, 1/4-hop WOLA; output retains input length."""
    central = validate(sample_rate, samples, notch_hz, fft_size, radius)
    hop = fft_size//4
    half = fft_size//2
    pad = [0.0] * half + list(samples) + [0.0] * (half + hop)
    synth = [0.0] * len(pad)
    norm = [0.0] * len(pad)
    window = [0.5 - 0.5*math.cos(2.0*math.pi*i/fft_size) for i in range(fft_size)]
    arr_type = ctypes.c_float * fft_size
    for start in range(0, len(pad) - fft_size + 1, hop):
        frame = arr_type(*(pad[start+i] * window[i] for i in range(fft_size)))
        lib.RealFFT(frame, fft_size//2, 1)
        for k in range(central-radius, central+radius+1):
            frame[2*k] = 0.0
            frame[2*k+1] = 0.0
        lib.RealFFT(frame, fft_size//2, 0)
        for i in range(fft_size):
            j = start + i
            w = window[i]
            synth[j] += frame[i] * w
            norm[j] += w*w
    out = []
    for i in range(half, half + len(samples)):
        if norm[i] <= 1e-12:
            raise Inconclusive("WOLA uncovered output sample")
        value = synth[i] / norm[i]
        if not math.isfinite(value) or abs(value) > 8:
            raise Inconclusive("non-finite or extreme DSP output")
        out.append(value)
    return out, central * sample_rate / fft_size


def write_wav_exclusive(path, sample_rate, samples):
    dest = Path(path)
    payload = b"".join(struct.pack("<h", max(-32768, min(32767, round(v*32768.0))))
                       for v in samples)
    created = False
    try:
        with dest.open("xb") as stream:
            created = True
            with wave.open(stream, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(payload)
    except (OSError, wave.Error) as exc:
        if created:
            dest.unlink(missing_ok=True)
        raise Inconclusive("could not create WAV exclusively: " + str(exc)) from exc


def render(math_dir, wav_input, wav_output, notch_hz, fft_size=1024, radius=2, compiler=None):
    rate, samples = read_wav(wav_input)
    validate(rate, samples, notch_hz, fft_size, radius)
    if Path(wav_output).exists() or Path(wav_output).is_symlink():
        raise Inconclusive("destination already exists; refusing overwrite")
    with compiled_fft(math_dir, compiler) as lib:
        processed, actual_hz = notch_pcm(lib, samples, rate, notch_hz, fft_size, radius)
    write_wav_exclusive(wav_output, rate, processed)
    return {"status": "HOST_WAV_RENDERED", "scope": "unaltered SoundHack RealFFT; host PCM16 mono WAV only",
            "source_blob": SOURCE_SHA, "header_blob": HEADER_SHA,
            "sample_rate": rate, "frames": len(samples), "fft_size": fft_size,
            "notch_requested_hz": notch_hz, "notch_centre_bin_hz": actual_hz,
            "notch_radius_bins": radius, "output": str(wav_output)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--math-dir", required=True, help="pre-existing, pinned SoundHack Math dir")
    parser.add_argument("--input", required=True, help="mono PCM16 WAV path")
    parser.add_argument("--output", required=True, help="new WAV path (must not exist)")
    parser.add_argument("--notch-hz", type=float, required=True)
    parser.add_argument("--fft-size", type=int, default=1024, choices=FFT_SIZES)
    parser.add_argument("--radius-bins", type=int, default=2)
    parser.add_argument("--cc", default=None)
    args = parser.parse_args(argv)
    try:
        info = render(args.math_dir, args.input, args.output, args.notch_hz,
                      args.fft_size, args.radius_bins, args.cc)
        exit_code = 0
    except (Inconclusive, OSError, ValueError, OverflowError) as exc:
        info = {"status": "INCONCLUSIVE", "reason": str(exc)}
        exit_code = 3
    print(json.dumps(info, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
