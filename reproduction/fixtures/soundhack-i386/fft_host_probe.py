#!/usr/bin/env python3
"""Host-only, numerical qualification of Tom Erbe's *unaltered* SoundHack FFT.c.

Copyright (C) 2026 D4rling contributors; GPL-3.0-or-later.
This program does not embed or redistribute upstream SoundHack source.
"""
import argparse
import ctypes
import hashlib
import json
import math
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_SHA = "b132ab450a71b451f5ae9e5649c98a6a41c9f9e9"
HEADER_SHA = "f31c2d41526d3768ad7cb0f10993847d2bd6ae84"
SIZES = (2, 4, 8, 16, 32, 64)
SPECTRAL_LIMIT = 1e-4
ROUNDTRIP_LIMIT = 2e-5
MAX_SOURCE_BYTES = 256 * 1024


class Inconclusive(Exception):
    """Missing or unqualified input, not a DSP test result."""


def git_blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\x00" + data).hexdigest()


def require_pinned(path, expected):
    if not path.is_file():
        raise Inconclusive(f"missing source: {path.name}")
    data = path.read_bytes()
    if not data or len(data) > MAX_SOURCE_BYTES:
        raise Inconclusive(f"empty/oversized source: {path.name}")
    actual = git_blob_sha(data)
    if actual != expected:
        raise Inconclusive(f"unexpected Git blob for {path.name}: {actual} != {expected}")
    return actual


def dft(values):
    """Independent double-precision DFT oracle; SoundHack forward uses +i."""
    n = len(values)
    return [sum(v * complex(math.cos(2.0 * math.pi * k * j / n),
                            math.sin(2.0 * math.pi * k * j / n))
                for j, v in enumerate(values)) for k in range(n)]


def as_float_array(values):
    return (ctypes.c_float * len(values))(*values)


def complex_spectrum(array, n):
    return [complex(array[2 * k], array[2 * k + 1]) for k in range(n)]


def real_spectrum(array, n):
    # RealFFT has a packed DC/Nyquist convention; positive bins in pairs.
    return ([complex(array[0], 0)]
            + [complex(array[2*k], array[2*k+1]) for k in range(1, n)]
            + [complex(array[1], 0)])


def abs_error(actual, expected):
    values = [abs(a - b) for a, b in zip(actual, expected)]
    if not values or not all(math.isfinite(value) for value in values):
        return 1e30  # non-finite/corrupt output is always an explicit failure
    return max(values)


def test_corpus(lib):
    for name in ("FFT", "RealFFT"):
        method = getattr(lib, name, None)
        if method is None:
            raise Inconclusive(f"missing entry point: {name}")
        method.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_long, ctypes.c_short]
        method.restype = None
    if not hasattr(lib, "InitFFTTable"):
        raise Inconclusive("missing entry point: InitFFTTable")
    lib.InitFFTTable()
    cases = []
    for n in SIZES:
        for kind in ("impulse", "mixed"):
            if kind == "impulse":
                samples = [complex(0.75, 0.125)] + [0j] * (n-1)
            else:
                samples = [complex(0.5*math.cos(j*0.13) + 0.1*math.sin(j*0.7),
                                   0.25*math.cos(j*0.8) - 0.15*math.sin(j*0.5))
                           for j in range(n)]
            raw = as_float_array([v for z in samples for v in (z.real, z.imag)])
            lib.FFT(raw, n, 1)
            spec_err = abs_error(complex_spectrum(raw, n), dft(samples))
            lib.FFT(raw, n, 0)
            inverse_err = abs_error(complex_spectrum(raw, n), samples)
            cases.append({"algorithm": "FFT", "points": n, "case": kind,
                          "spectral_abs_error": spec_err,
                          "roundtrip_abs_error": inverse_err,
                          "pass": spec_err <= SPECTRAL_LIMIT and inverse_err <= ROUNDTRIP_LIMIT})
            if kind == "impulse":
                real = [0.75] + [0.0] * (2*n-1)
            else:
                real = [math.sin(0.37*j) + 0.25*math.cos(1.13*j) for j in range(2*n)]
            raw = as_float_array(real)
            lib.RealFFT(raw, n, 1)
            spec_err = abs_error(real_spectrum(raw, n), dft(real)[:n+1])
            lib.RealFFT(raw, n, 0)
            inverse_err = abs_error(raw, real)
            cases.append({"algorithm": "RealFFT", "points": 2*n, "case": kind,
                          "spectral_abs_error": spec_err,
                          "roundtrip_abs_error": inverse_err,
                          "pass": spec_err <= SPECTRAL_LIMIT and inverse_err <= ROUNDTRIP_LIMIT})
    return cases


def spectral_notch(lib):
    """Transform an original two-tone signal using SoundHack's RealFFT."""
    n = 64
    count = 2 * n
    wanted = [0.6 * math.sin(2 * math.pi * 5 * j / count) for j in range(count)]
    unwanted = [0.25 * math.sin(2 * math.pi * 19 * j / count) for j in range(count)]
    before = [a + b for a, b in zip(wanted, unwanted)]
    array = as_float_array(before)
    lib.RealFFT(array, n, 1)
    spectral_err = abs_error(real_spectrum(array, n), dft(before)[:n + 1])
    # The real FFT stores only positive bins; its inverse restores conjugates.
    array[2 * 19] = 0.0
    array[2 * 19 + 1] = 0.0
    lib.RealFFT(array, n, 0)
    output_error = abs_error(array, wanted)
    return {"case": "remove_bin_19_keep_bin_5", "points": count,
            "spectral_abs_error": spectral_err,
            "processed_abs_error": output_error,
            "pass": spectral_err <= SPECTRAL_LIMIT and output_error <= ROUNDTRIP_LIMIT}


def run(source_dir, source_sha=SOURCE_SHA, header_sha=HEADER_SHA, compiler=None):
    directory = Path(source_dir)
    source = directory / "FFT.c"
    header = directory / "FFT.h"
    require_pinned(source, source_sha)
    require_pinned(header, header_sha)
    tool = compiler if compiler is not None else shutil.which("cc")
    if not tool or not shutil.which(tool):
        raise Inconclusive("C compiler not available")
    with tempfile.TemporaryDirectory(prefix="sh-fft-host-") as temp:
        helper = Path(temp) / "fft_globals.c"
        helper.write_text("float Pi = 3.14159265358979323846f;\n"
                          "float twoPi = 6.28318530717958647692f;\n", encoding="ascii")
        output = Path(temp) / "libshfft.so"
        command = [tool, "-std=c99", "-O1", "-fPIC", "-shared", "-o", str(output),
                   str(source), str(helper), "-lm"]
        try:
            compile_result = subprocess.run(command, capture_output=True, text=True, timeout=30,
                                            check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Inconclusive("host compilation failed: " + str(exc)) from exc
        if compile_result.returncode:
            raise Inconclusive("host compiler returned nonzero: " + compile_result.stderr[-900:])
        try:
            lib = ctypes.CDLL(str(output))
            cases = test_corpus(lib)
            processing = spectral_notch(lib)
        except (OSError, AttributeError) as exc:
            raise Inconclusive("cannot inspect host library: " + str(exc)) from exc
    success = all(case["pass"] for case in cases) and processing["pass"]
    return {
        "status": "HOST_DSP_PASS" if success else "HOST_DSP_FAIL",
        "scope": "unaltered upstream FFT.c compiled for host; NOT D4rling guest DSP/audio",
        "source_blob": source_sha, "header_blob": header_sha,
        "host_machine": platform.machine(), "host_long_bits": ctypes.sizeof(ctypes.c_long) * 8,
        "cases": len(cases), "passed": sum(bool(c["pass"]) for c in cases),
        "spectral_abs_max": max(c["spectral_abs_error"] for c in cases),
        "roundtrip_abs_max": max(c["roundtrip_abs_error"] for c in cases),
        "spectral_limit": SPECTRAL_LIMIT, "roundtrip_limit": ROUNDTRIP_LIMIT,
        "results": cases, "spectral_processing": processing,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, help="existing upstream Math directory with FFT.c/FFT.h")
    parser.add_argument("--expected-source-blob", default=SOURCE_SHA)
    parser.add_argument("--expected-header-blob", default=HEADER_SHA)
    parser.add_argument("--cc", default=None, help="already installed host C compiler")
    args = parser.parse_args(argv)
    try:
        result = run(args.source_dir, args.expected_source_blob, args.expected_header_blob, args.cc)
    except (Inconclusive, OSError, ValueError) as exc:
        result = {"status": "INCONCLUSIVE", "error": str(exc)}
        code = 3
    else:
        code = 0 if result["status"] == "HOST_DSP_PASS" else 2
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
