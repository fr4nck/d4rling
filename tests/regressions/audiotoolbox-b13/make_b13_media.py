#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""B13: original deterministic audio files for AudioToolbox, and their oracle.

  make_b13_media.py OUT_DIR

Signal: the QT-B12 arpeggio (A4, C#5, E5, A5; 0.5 s each; peak 8192; 10 ms
raised-cosine ramps; note 2 left only, note 3 right only), 44 100 Hz stereo,
88 200 frames. Containers are written here from their public specifications,
without FFmpeg or any audio library:
  demo-s16.wav    RIFF/WAVE, PCM 16-bit little-endian
  demo-s16.aiff   AIFF, PCM 16-bit big-endian
  demo-s16.caf    CAF, 'lpcm' 16-bit big-endian
  demo-ulaw.wav   RIFF/WAVE, G.711 mu-law (format tag 7) with a 'fact' chunk
  bad-garbage.wav 4 096 bytes of a fixed LCG sequence (not audio)
  bad-trunc.wav   demo-s16.wav cut to 40 % of its length (header unchanged)
  bad-empty.wav   0 bytes
The oracle (b13-oracle.json) gives, for every file, the expected stream format
and the SHA-256 of the expected samples, computed here independently:
  - PCM files: the generated samples in the file's own byte order;
  - mu-law: G.711 decoding (ITU-T formula) of the encoded bytes, as S16LE;
  - Float32 view: s / 32768 for each S16 sample (exact in binary32);
  - 48 kHz Float32: the same note schedule evaluated analytically at 48 kHz
    (reference only; the comparison tolerance is defined in the oracle).
"""
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

RATE, CH, FPN, PEAK, RAMP = 44100, 2, 22050, 8192, 441
NOTES = [(440.0, (1, 1)), (554.365, (1, 0)), (659.255, (0, 1)), (880.0, (1, 1))]


def env(n, frames, ramp):
    if n < ramp:
        return 0.5 - 0.5 * math.cos(math.pi * n / ramp)
    if n >= frames - ramp:
        return 0.5 - 0.5 * math.cos(math.pi * (frames - 1 - n) / ramp)
    return 1.0


def samples():
    out = []
    for freq, (l, r) in NOTES:
        for n in range(FPN):
            v = int(round(PEAK * env(n, FPN, RAMP) * math.sin(2.0 * math.pi * freq * n / RATE)))
            out += [v * l, v * r]
    return out


def analytic(rate):
    """Continuous-time version of the schedule, sampled at RATE' (float, unit = 1.0 full scale)."""
    fpn = FPN * rate / RATE
    out = []
    total = int(round(len(NOTES) * fpn))
    for k in range(total):
        t = k / rate
        i = min(int(t / 0.5), 3)
        tn = t - 0.5 * i
        n = tn * RATE  # position in source frames within the note
        freq, (l, r) = NOTES[i]
        if n < RAMP:
            e = 0.5 - 0.5 * math.cos(math.pi * n / RAMP)
        elif n >= FPN - 1 - RAMP:
            e = max(0.0, 0.5 - 0.5 * math.cos(math.pi * max(0.0, FPN - 1 - n) / RAMP))
        else:
            e = 1.0
        v = PEAK * e * math.sin(2.0 * math.pi * freq * tn) / 32768.0
        out += [v * l, v * r]
    return out


# ---- G.711 mu-law (ITU-T G.711, Sun reference algorithm) ---------------------
def ulaw_encode(s):
    BIAS, CLIP = 0x84, 32635
    sign = 0x80 if s < 0 else 0
    if s < 0:
        s = -s
    s = min(s, CLIP) + BIAS
    exp = 7
    mask = 0x4000
    while exp > 0 and not (s & mask):
        exp -= 1
        mask >>= 1
    mant = (s >> (exp + 3)) & 0x0F
    return ~(sign | (exp << 4) | mant) & 0xFF


def ulaw_decode(u):
    u = ~u & 0xFF
    sign, exp, mant = u & 0x80, (u >> 4) & 0x07, u & 0x0F
    v = (((mant << 3) + 0x84) << exp) - 0x84
    return -v if sign else v


def chunk(cid, data):
    pad = b"\x00" if len(data) % 2 else b""
    return cid + struct.pack("<I", len(data)) + data + pad


def wav_pcm(raw):
    fmt = struct.pack("<HHIIHH", 1, CH, RATE, RATE * CH * 2, CH * 2, 16)
    body = b"WAVE" + chunk(b"fmt ", fmt) + chunk(b"data", raw)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def wav_ulaw(raw, frames):
    fmt = struct.pack("<HHIIHHH", 7, CH, RATE, RATE * CH, CH, 8, 0)
    body = b"WAVE" + chunk(b"fmt ", fmt) + chunk(b"fact", struct.pack("<I", frames)) + chunk(b"data", raw)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def ext80(x):
    """IEEE 754 80-bit extended, big-endian (AIFF sample rate)."""
    e = int(math.floor(math.log2(x)))
    mant = int(x * (1 << (63 - e)))
    return struct.pack(">HQ", 16383 + e, mant)


def aiff(raw, frames):
    comm = struct.pack(">hIh", CH, frames, 16) + ext80(RATE)
    ssnd = struct.pack(">II", 0, 0) + raw
    body = b"AIFF" + b"COMM" + struct.pack(">I", len(comm)) + comm + b"SSND" + struct.pack(">I", len(ssnd)) + ssnd
    return b"FORM" + struct.pack(">I", len(body)) + body


def caf(raw):
    desc = struct.pack(">d", float(RATE)) + b"lpcm" + struct.pack(">IIIII", 0, CH * 2, 1, CH, 16)
    data = struct.pack(">I", 0) + raw
    return (b"caff" + struct.pack(">HH", 1, 0) + b"desc" + struct.pack(">q", len(desc)) + desc
            + b"data" + struct.pack(">q", len(data)) + data)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    s = samples()
    frames = len(s) // CH
    le = struct.pack("<%dh" % len(s), *s)
    be = struct.pack(">%dh" % len(s), *s)
    u = bytes(ulaw_encode(x) for x in s)
    udec = [ulaw_decode(x) for x in u]
    udec_le = struct.pack("<%dh" % len(udec), *udec)
    f32 = struct.pack("<%df" % len(s), *[x / 32768.0 for x in s])
    assert all(ulaw_decode(ulaw_encode(v)) == ulaw_decode(ulaw_encode(v)) for v in (-32768, -1, 0, 1, 32767))
    files = {
        "demo-s16.wav": wav_pcm(le),
        "demo-s16.aiff": aiff(be, frames),
        "demo-s16.caf": caf(be),
        "demo-ulaw.wav": wav_ulaw(u, frames),
    }
    x = 12345
    garbage = bytearray()
    for _ in range(4096):
        x = (1103515245 * x + 12345) & 0x7FFFFFFF
        garbage.append((x >> 16) & 0xFF)
    files["bad-garbage.wav"] = bytes(garbage)
    files["bad-trunc.wav"] = files["demo-s16.wav"][: int(len(files["demo-s16.wav"]) * 0.4)]
    files["bad-empty.wav"] = b""
    for name, data in files.items():
        (out / name).write_bytes(data)
    trunc_payload = len(files["bad-trunc.wav"]) - 44
    a48 = analytic(48000)
    (out / "ref-48k-f32le.raw").write_bytes(struct.pack("<%df" % len(a48), *a48))
    oracle = {
        "signal": {"rate": RATE, "channels": CH, "frames": frames, "peak": PEAK,
                   "notes": [{"hz": f, "left": l, "right": r, "start_frame": i * FPN, "frames": FPN}
                             for i, (f, (l, r)) in enumerate(NOTES)]},
        "files": {n: {"bytes": len(d), "sha256": sha(d)} for n, d in files.items()},
        "expect": {
            "demo-s16.wav": {"file_type": "WAVE", "format": "lpcm", "flags_signed": True, "big_endian": False, "bits": 16,
                             "packets": frames, "data_bytes": len(le), "packets_sha256": sha(le)},
            "demo-s16.aiff": {"file_type": "AIFF", "format": "lpcm", "flags_signed": True, "big_endian": True, "bits": 16,
                              "packets": frames, "data_bytes": len(be), "packets_sha256": sha(be)},
            "demo-s16.caf": {"file_type": "caff", "format": "lpcm", "flags_signed": True, "big_endian": True, "bits": 16,
                             "packets": frames, "data_bytes": len(be), "packets_sha256": sha(be)},
            "demo-ulaw.wav": {"file_type": "WAVE", "format": "ulaw", "bits": 8, "packets": frames,
                              "data_bytes": len(u), "packets_sha256": sha(u),
                              "decoded_s16le_sha256": sha(udec_le)},
            "bad-trunc.wav": {"available_payload_bytes": trunc_payload,
                              "available_frames": trunc_payload // 4,
                              "prefix_sha256": sha(le[: (trunc_payload // 4) * 4])},
        },
        "views": {"s16le_sha256": sha(le), "s16be_sha256": sha(be), "f32le_sha256": sha(f32),
                  "ulaw_decoded_s16le_sha256": sha(udec_le), "ulaw_decoded_s16be_sha256":
                      sha(struct.pack(">%dh" % len(udec), *udec))},
        "tolerances": {
            "s16_to_f32": "exact: every output sample equals s/32768 (binary32), 0 differences",
            "ulaw_to_s16": "exact: every output sample equals the G.711 decoding, 0 differences",
            "s16_byteswap": "exact: identical bytes after swapping",
            "resample_44k1_to_48k_f32": {
                "frames": 96000, "frames_tolerance": 64, "max_lag_search": 512,
                "interior_skip_frames": 1024, "min_snr_db_vs_analytic": 50.0,
                "note_freq_rel_tolerance": 0.002, "note_level_db_tolerance": 0.5},
        },
        "ref_48k_f32le_sha256": sha((out / "ref-48k-f32le.raw").read_bytes()),
    }
    (out / "b13-oracle.json").write_text(json.dumps(oracle, indent=2) + "\n")
    for n, d in files.items():
        print(f"{n:16} {len(d):8} {sha(d)}")


if __name__ == "__main__":
    main()
