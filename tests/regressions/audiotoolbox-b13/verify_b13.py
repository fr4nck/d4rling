#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""B13: compare what the guest decoded with the independent oracle.

  verify_b13.py MEDIA_DIR OUT_DIR GUEST_STDOUT

Criteria are those written in b13-oracle.json before any run. Prints one
VERIFY line per criterion and VERIFY_SUMMARY; exit status 0 only if every
applicable criterion passes. A criterion whose data are absent is FAIL, never
skipped silently.
"""
import hashlib
import json
import math
import re
import struct
import sys
from pathlib import Path

media, out, log = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]).read_text()
o = json.loads((media / "b13-oracle.json").read_text())
E, V, TOL = o["expect"], o["views"], o["tolerances"]
results = []


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def verdict(name, ok, detail):
    results.append(ok)
    print(f"VERIFY {name} {'PASS' if ok else 'FAIL'} {detail}")


# ---- B: AudioFile -------------------------------------------------------------
for name in ["demo-s16.wav", "demo-s16.aiff", "demo-s16.caf", "demo-ulaw.wav"]:
    e = E[name]
    p = out / f"{name}.packets"
    verdict(f"packets_bytes[{name}]", sha(p) == e["packets_sha256"],
            f"sha={str(sha(p))[:16]} expected={e['packets_sha256'][:16]} bytes={p.stat().st_size if p.exists() else None}")
    m = re.search(rf"B13_PROPS {re.escape(name)} (.*)", log)
    props = dict(kv.split("=", 1) for kv in m.group(1).split()) if m else {}
    ok = bool(m) and props.get("format") == e["format"] and int(props.get("packets", -1)) == e["packets"] \
        and int(props.get("data_bytes", -1)) == e["data_bytes"] and int(props.get("bits", -1)) == e["bits"]
    if ok and e["format"] == "lpcm":
        flags = int(props["flags"], 16)
        ok = bool(flags & 0x4) == e["flags_signed"] and bool(flags & 0x2) == e["big_endian"]
    verdict(f"properties[{name}]", ok, f"format={props.get('format')} packets={props.get('packets')} data_bytes={props.get('data_bytes')} "
            f"bits={props.get('bits')} flags={props.get('flags')} file_type={props.get('file_type')} (written as {e['file_type']})")
    pd = out / f"{name}.pd1000"
    if p.exists() and pd.exists():
        bpp = 1 if e["bits"] == 8 else 2
        bpp *= 2
        ref = p.read_bytes()[1000 * bpp:(1000 + 2048) * bpp]
        verdict(f"readpacketdata_offset[{name}]", pd.read_bytes() == ref, f"bytes={pd.stat().st_size} packets 1000..3047")
    else:
        verdict(f"readpacketdata_offset[{name}]", False, "missing output")


def obs(name):
    m = re.search(rf"B13_OBS {re.escape(name)} (.*)", log)
    return dict(kv.split("=", 1) for kv in m.group(1).split() if "=" in kv) if m else None


m = obs("missing.wav")
verdict("negative[missing]", bool(m) and m["open_status"] == "-43" and m["handle"] == "null", f"{m}")
for n in ["bad-garbage.wav", "bad-empty.wav"]:
    m = obs(n)
    verdict(f"negative[{n}]", bool(m) and m.get("open_status") not in (None, "0") and m.get("handle") == "null", f"{m}")
m = obs("bad-trunc.wav")
t = E["bad-trunc.wav"]
p = out / "bad-trunc.wav.packets"
ok = bool(m) and m.get("open_status") == "0" and int(m.get("packets_read", -1)) <= t["available_frames"] \
    and p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == hashlib.sha256(
        (out / "demo-s16.wav.packets").read_bytes()[:p.stat().st_size]).hexdigest() \
    and int(m.get("packets_reported", -1)) == t["available_frames"]
verdict("negative[bad-trunc.wav]", ok, f"{m} available_frames={t['available_frames']} (criterion: truthful count, no data beyond the cut, prefix identical)")

# ---- C: ExtAudioFile / AudioConverter ---------------------------------------------------
verdict("ext[wav-f32] exact s/32768", sha(out / "ext-wav-f32.raw") == V["f32le_sha256"], f"sha={str(sha(out / 'ext-wav-f32.raw'))[:16]}")
verdict("ext[aiff-s16le] exact byteswap", sha(out / "ext-aiff-s16le.raw") == V["s16le_sha256"], f"sha={str(sha(out / 'ext-aiff-s16le.raw'))[:16]}")
verdict("ext[ulaw-s16] exact G.711", sha(out / "ext-ulaw-s16.raw") == V["ulaw_decoded_s16le_sha256"], f"sha={str(sha(out / 'ext-ulaw-s16.raw'))[:16]}")
verdict("converter[s16le->f32] exact s/32768", sha(out / "conv-s16le-f32.raw") == V["f32le_sha256"], f"sha={str(sha(out / 'conv-s16le-f32.raw'))[:16]}")

# resampling: frames, best lag, SNR against the analytic 48 kHz signal, note frequencies
r = TOL["resample_44k1_to_48k_f32"]
p = out / "ext-wav-f32-48k.raw"
if p.exists():
    got = struct.unpack("<%df" % (p.stat().st_size // 4), p.read_bytes())
    ref = struct.unpack("<%df" % ((media / "ref-48k-f32le.raw").stat().st_size // 4), (media / "ref-48k-f32le.raw").read_bytes())
    nf = len(got) // 2
    lo, hi = r["interior_skip_frames"], min(nf, len(ref) // 2) - r["interior_skip_frames"]
    best = None
    for lag in range(-r["max_lag_search"], r["max_lag_search"] + 1, 1):
        a = max(lo, lo - lag)
        b = min(hi, hi - lag)
        step = 61
        err = sig = 0.0
        for k in range(a, b, step):
            for c in (0, 1):
                g, s = got[2 * (k + lag) + c], ref[2 * k + c]
                err += (g - s) ** 2
                sig += s * s
        snr = 10 * math.log10(sig / err) if err > 0 else 999
        if best is None or snr > best[1]:
            best = (lag, snr)
    lag = best[0]
    err = sig = 0.0
    for k in range(lo, hi):
        if 0 <= k + lag < nf:
            for c in (0, 1):
                g, s = got[2 * (k + lag) + c], ref[2 * k + c]
                err += (g - s) ** 2
                sig += s * s
    snr = 10 * math.log10(sig / err) if err > 0 else 999
    verdict("ext[wav-f32-48k] frames", abs(nf - r["frames"]) <= r["frames_tolerance"], f"frames={nf} expected={r['frames']}±{r['frames_tolerance']}")
    verdict("ext[wav-f32-48k] snr", snr >= r["min_snr_db_vs_analytic"], f"lag={lag} snr_db={snr:.2f} min={r['min_snr_db_vs_analytic']}")
    fpn = 24000
    for i, note in enumerate(o["signal"]["notes"]):
        c = 0 if note["left"] else 1
        a, b = i * fpn + 2000 + lag, (i + 1) * fpn - 2000 + lag
        xs = [got[2 * k + c] for k in range(a, b)]
        zc = [k for k in range(1, len(xs)) if xs[k - 1] < 0 <= xs[k]]
        f = 48000 * (len(zc) - 1) / ((zc[-1] - zc[0]) if len(zc) > 1 else 1)
        rms = math.sqrt(sum(x * x for x in xs) / len(xs))
        rrms = math.sqrt(sum(ref[2 * (k - lag) + c] ** 2 for k in range(a, b)) / len(xs))
        db = 20 * math.log10(rms / rrms) if rms > 0 and rrms > 0 else 99
        verdict(f"ext[wav-f32-48k] note{i + 1}", abs(f / note["hz"] - 1) <= r["note_freq_rel_tolerance"] and abs(db) <= r["note_level_db_tolerance"],
                f"hz={f:.3f} expected={note['hz']} level_db={db:+.3f}")
else:
    verdict("ext[wav-f32-48k]", False, "missing output")

print(f"VERIFY_SUMMARY pass={sum(results)} fail={len(results) - sum(results)}")
sys.exit(0 if all(results) else 1)
