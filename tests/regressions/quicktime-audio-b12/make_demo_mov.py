#!/usr/bin/env python3
"""QT-B12-B: original synthetic demonstration MOV and its oracle.

  make_demo_mov.py OUT_DIR

Writes demo.mov (QuickTime file: ftyp, mdat, moov with one 'soun' track,
'twos' 16-bit big-endian stereo PCM at 44100 Hz, self-contained 'alis' data
reference) and demo.json (oracle: frame count, duration, format, per-note
segments, SHA-256 of the PCM payload, FNV-1a 64 of the PCM).

Signal: A-major arpeggio A4 440 Hz, C#5 554.365 Hz, E5 659.255 Hz, A5 880 Hz,
0.5 s each (22050 frames), peak 8192 (-12 dBFS), 10 ms raised-cosine attack
and release. Note 1 and 4 on both channels, note 2 left only, note 3 right
only. 88200 frames = 2.0 s: with 1024-frame device buffers the last block is
partial (136 frames).
"""
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

RATE, CH, FRAMES_PER_NOTE, PEAK, RAMP = 44100, 2, 22050, 8192, 441
NOTES = [(440.0, (1, 1)), (554.365, (1, 0)), (659.255, (0, 1)), (880.0, (1, 1))]


def pcm_bytes():
    out = bytearray()
    for freq, (left, right) in NOTES:
        for n in range(FRAMES_PER_NOTE):
            env = 1.0
            if n < RAMP:
                env = 0.5 - 0.5 * math.cos(math.pi * n / RAMP)
            elif n >= FRAMES_PER_NOTE - RAMP:
                env = 0.5 - 0.5 * math.cos(math.pi * (FRAMES_PER_NOTE - 1 - n) / RAMP)
            v = int(round(PEAK * env * math.sin(2.0 * math.pi * freq * n / RATE)))
            out += struct.pack(">hh", v * left, v * right)
    return bytes(out)


def atom(kind, payload):
    return struct.pack(">I", 8 + len(payload)) + kind + payload


def full(kind, payload, version_flags=0):
    return atom(kind, struct.pack(">I", version_flags) + payload)


def build(pcm):
    frames = len(pcm) // (2 * CH)
    ftyp = atom(b"ftyp", b"qt  " + struct.pack(">I", 0x20050300) + b"qt  ")
    mdat_header = 8
    pcm_offset = len(ftyp) + mdat_header
    mdat = atom(b"mdat", pcm)
    movie_scale, movie_duration = 600, frames * 600 // RATE
    matrix = struct.pack(">9I", 0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000)
    mvhd = full(b"mvhd", struct.pack(">IIII", 0, 0, movie_scale, movie_duration) + struct.pack(">IH", 0x10000, 0x100)
                + bytes(10) + matrix + bytes(24) + struct.pack(">I", 2))
    tkhd = full(b"tkhd", struct.pack(">IIIII", 0, 0, 1, 0, movie_duration) + bytes(8) + struct.pack(">HHHH", 0, 0, 0x100, 0)
                + matrix + struct.pack(">II", 0, 0), version_flags=0xF)
    mdhd = full(b"mdhd", struct.pack(">IIIIHH", 0, 0, RATE, frames, 0, 0))
    hdlr = full(b"hdlr", b"mhlr" + b"soun" + bytes(12) + b"\x00")
    smhd = full(b"smhd", struct.pack(">HH", 0, 0))
    dref = full(b"dref", struct.pack(">I", 1) + full(b"alis", b"", version_flags=1))
    dinf = atom(b"dinf", dref)
    entry = atom(b"twos", bytes(6) + struct.pack(">H", 1) + struct.pack(">HHI", 0, 0, 0)
                 + struct.pack(">HHHHI", CH, 16, 0, 0, RATE << 16))
    stsd = full(b"stsd", struct.pack(">I", 1) + entry)
    stts = full(b"stts", struct.pack(">III", 1, frames, 1))
    stsc = full(b"stsc", struct.pack(">IIII", 1, 1, frames, 1))
    stsz = full(b"stsz", struct.pack(">II", 2 * CH, frames))
    stco = full(b"stco", struct.pack(">II", 1, pcm_offset))
    stbl = atom(b"stbl", stsd + stts + stsc + stsz + stco)
    minf = atom(b"minf", smhd + dinf + stbl)
    mdia = atom(b"mdia", mdhd + hdlr + minf)
    trak = atom(b"trak", tkhd + mdia)
    moov = atom(b"moov", mvhd + trak)
    data = ftyp + mdat + moov
    assert data[pcm_offset:pcm_offset + len(pcm)] == pcm
    return data, pcm_offset, movie_scale, movie_duration


def fnv64(b):
    h = 0xcbf29ce484222325
    for x in b:
        h = ((h ^ x) * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return f"{h:016x}"


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    pcm = pcm_bytes()
    mov, offset, mscale, mdur = build(pcm)
    (out / "demo.mov").write_bytes(mov)
    frames = len(pcm) // 4
    oracle = {
        "file_bytes": len(mov), "file_sha256": hashlib.sha256(mov).hexdigest(),
        "format": "twos", "rate": RATE, "channels": CH, "bits": 16, "big_endian": True,
        "frames": frames, "duration_s": frames / RATE, "movie_time_scale": mscale, "movie_duration": mdur,
        "pcm_offset": offset, "pcm_bytes": len(pcm), "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
        "pcm_fnv64": fnv64(pcm), "peak": PEAK,
        "notes": [{"hz": f, "left": l, "right": r, "start_frame": i * FRAMES_PER_NOTE, "frames": FRAMES_PER_NOTE}
                  for i, (f, (l, r)) in enumerate(NOTES)],
        "device_buffer_frames": 1024, "last_partial_block_frames": frames % 1024,
        "getmediasample_max_bytes": 65536, "getmediasample_calls": -(-len(pcm) // 65536),
        "getmediasample_last_bytes": len(pcm) - (len(pcm) // 65536) * 65536,
    }
    (out / "demo.json").write_text(json.dumps(oracle, indent=1) + "\n")
    print(json.dumps({k: oracle[k] for k in ("file_bytes", "frames", "pcm_sha256", "pcm_fnv64",
                                             "last_partial_block_frames", "getmediasample_calls",
                                             "getmediasample_last_bytes")}))


if __name__ == "__main__":
    main()
