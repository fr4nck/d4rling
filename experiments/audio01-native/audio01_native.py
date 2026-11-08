#!/usr/bin/env python3
"""D4RLING-AUDIO-01: native Linux -> PulseAudio sound-path qualification.

Read-only relative to D4RLING and the OS; Python standard library only.
--probe: inspect Linux/WSLg and PulseAudio client library without contacting a server.
--play: send 1.25 s / 440 Hz quiet stereo PCM16LE to PulseAudio using libpulse-simple.
--self-test: verify PCM synthesis and ctypes ABI, with no sound.

This DOES NOT run Mach-O, CoreAudio, Darwin, or JACK. A successful drain
means PulseAudio accepted the PCM stream, not that somebody heard it.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import hashlib
import json
import math
import os
import platform
import socket
import stat
import struct
import sys
import time
from pathlib import Path

RATE_HZ = 44100
CHANNELS = 2
FREQUENCY_HZ = 440
DURATION_S = 1.25
AMPLITUDE = 0.09  # 9% of full-scale; moderate amplitude, including headphones
PA_SAMPLE_S16LE = 3  # pa_sample_format_t from PulseAudio sample.h
PA_STREAM_PLAYBACK = 1  # pa_stream_direction_t from PulseAudio def.h


class PASampleSpec(ctypes.Structure):
    _fields_ = [
        ("format", ctypes.c_int),
        ("rate", ctypes.c_uint32),
        ("channels", ctypes.c_uint8),
    ]


def tone_pcm16le() -> bytes:
    """A quiet, click-reduced, interleaved stereo tone, generated in RAM."""
    frames = round(DURATION_S * RATE_HZ)
    result = bytearray(frames * CHANNELS * 2)
    fade_frames = round(RATE_HZ * 0.015)
    for index in range(frames):
        fade = min(1.0, index / fade_frames, (frames - 1 - index) / fade_frames)
        value = round(32767.0 * AMPLITUDE * fade * math.sin(
            2.0 * math.pi * FREQUENCY_HZ * index / RATE_HZ
        ))
        struct.pack_into("<hh", result, index * 4, value, value)
    return bytes(result)


def wslg_audio_socket() -> str:
    path = Path("/mnt/wslg/PulseServer")
    try:
        mode = path.stat().st_mode
    except OSError:
        return "not_present"
    return "unix_socket" if stat.S_ISSOCK(mode) else "present_not_socket"


def load_pulse_libraries():
    simple_name = ctypes.util.find_library("pulse-simple") or "libpulse-simple.so.0"
    pulse_name = ctypes.util.find_library("pulse") or "libpulse.so.0"
    simple = ctypes.CDLL(simple_name)
    pulse = ctypes.CDLL(pulse_name)
    simple.pa_simple_new.argtypes = [
        ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int,
        ctypes.c_char_p, ctypes.c_char_p,
        ctypes.POINTER(PASampleSpec), ctypes.c_void_p, ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    simple.pa_simple_new.restype = ctypes.c_void_p
    simple.pa_simple_write.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_int),
    ]
    simple.pa_simple_write.restype = ctypes.c_int
    simple.pa_simple_drain.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
    simple.pa_simple_drain.restype = ctypes.c_int
    simple.pa_simple_free.argtypes = [ctypes.c_void_p]
    simple.pa_simple_free.restype = None
    pulse.pa_strerror.argtypes = [ctypes.c_int]
    pulse.pa_strerror.restype = ctypes.c_char_p
    return simple, pulse


def error_text(pulse, code: int) -> str:
    msg = pulse.pa_strerror(code)
    return msg.decode("utf-8", "replace") if msg else f"PulseAudio error {code}"


def play_audio(simple, pulse, pcm: bytes) -> dict:
    spec = PASampleSpec(format=PA_SAMPLE_S16LE, rate=RATE_HZ, channels=CHANNELS)
    error = ctypes.c_int(0)
    handle = simple.pa_simple_new(
        None, b"D4RLING-AUDIO-01", PA_STREAM_PLAYBACK, None,
        b"Native PulseAudio 440Hz witness", ctypes.byref(spec), None, None,
        ctypes.byref(error),
    )
    if not handle:
        return {"status": "ERROR_PULSE_CONNECTION", "detail": error_text(pulse, error.value)}
    try:
        data = ctypes.create_string_buffer(pcm)
        result = simple.pa_simple_write(handle, data, len(pcm), ctypes.byref(error))
        if result < 0:
            return {"status": "ERROR_PULSE_WRITE", "detail": error_text(pulse, error.value)}
        result = simple.pa_simple_drain(handle, ctypes.byref(error))
        if result < 0:
            return {"status": "ERROR_PULSE_DRAIN", "detail": error_text(pulse, error.value)}
        return {
            "status": "PCM_SENT_TO_PULSE_SERVER_AUDIBILITY_UNVERIFIED",
            "bytes_written": len(pcm),
            "server_drain_success": True,
            "sound_heard_by_user": "not_observed",
        }
    finally:
        simple.pa_simple_free(handle)


def base_report(mode: str) -> dict:
    release = platform.release().lower()
    return {
        "experiment": "D4RLING-AUDIO-01",
        "mode": mode,
        "scope": "Linux native PulseAudio only; no Mach-O/CoreAudio/Darwin/JACK",
        "machine": platform.machine(),
        "python": platform.python_version(),
        "wsl_detected": "microsoft" in release or "wsl" in release,
        "pulse_server_env": os.environ.get("PULSE_SERVER") or "unset",
        "wslg_pulse_socket": wslg_audio_socket(),
        "tone": {
            "hz": FREQUENCY_HZ,
            "duration_ms": round(DURATION_S * 1000),
            "rate_hz": RATE_HZ,
            "channels": CHANNELS,
            "sample_format": "S16LE",
            "amplitude_pct_full_scale": round(AMPLITUDE * 100),
        },
    }


def self_test():
    pcm = tone_pcm16le()
    expected_frames = round(DURATION_S * RATE_HZ)
    assert len(pcm) == expected_frames * CHANNELS * 2
    assert ctypes.sizeof(PASampleSpec) == 12
    assert pcm[:4] == b"\x00\x00\x00\x00"
    assert pcm[-4:] == b"\x00\x00\x00\x00"
    sample = struct.unpack_from("<hh", pcm, 1000 * 4)
    assert sample[0] == sample[1]
    assert len(set(pcm)) > 5
    assert max(abs(struct.unpack_from("<h", pcm, i * 2)[0]) for i in range(0, min(5000, len(pcm) // 2))) <= 32767 * AMPLITUDE + 1
    return {"status": "SELF_TEST_PASS", "frames": expected_frames,
            "bytes": len(pcm), "sample_spec_size": ctypes.sizeof(PASampleSpec),
            "pcm_sha256": hashlib.sha256(pcm).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--probe", action="store_true", help="Inspect audio prerequisites without playing sound")
    options.add_argument("--play", action="store_true", help="Play quiet tone via native PulseAudio")
    options.add_argument("--self-test", action="store_true", help="Validate generator and ctypes ABI without playing sound")
    args = parser.parse_args()
    mode = "self-test" if args.self_test else "play" if args.play else "probe"
    report = base_report(mode)
    if args.self_test:
        report.update(self_test())
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    try:
        simple, pulse = load_pulse_libraries()
        report["native_libpulse_simple"] = "loaded"
    except (OSError, AttributeError) as exc:
        report.update(status="BLOCKED_NATIVE_LIBPULSE_MISSING", detail=str(exc))
        print(json.dumps(report, indent=2, sort_keys=True))
        return 2
    if args.probe:
        report["status"] = "READY_TO_ATTEMPT_NATIVE_PLAYBACK_SERVER_UNTESTED"
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    started = time.monotonic()
    pcm = tone_pcm16le()
    report["pcm_sha256"] = hashlib.sha256(pcm).hexdigest()
    try:
        report.update(play_audio(simple, pulse, pcm))
    except (OSError, ValueError) as exc:
        report.update(status="ERROR_NATIVE_PLAYBACK", detail=str(exc))
    report["elapsed_ms"] = round((time.monotonic() - started) * 1000)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PCM_SENT_TO_PULSE_SERVER_AUDIBILITY_UNVERIFIED" else 3


if __name__ == "__main__":
    sys.exit(main())
