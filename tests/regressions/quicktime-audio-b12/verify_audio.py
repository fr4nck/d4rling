#!/usr/bin/env python3
"""QT-B12 independent oracles.

  verify_audio.py pcm ORACLE.json GMS.pcm
      PCM obtained in the guest through GetMediaSample == generator PCM.
  verify_audio.py capture ORACLE.json CAPTURE.raw play|stoprestart
      Analyse a capture of the default sink monitor (S16LE stereo 44100):
      note order and frequency (Goertzel), left/right pattern, duration,
      silence after the natural end (no loop) and, for stoprestart, a silent
      gap after Stop followed by a complete second playback.
Exit status 0 on PASS.
"""
import hashlib
import json
import math
import struct
import sys

RATE = 44100


def goertzel(xs, f):
    w = 2 * math.pi * f / RATE
    c = 2 * math.cos(w)
    s1 = s2 = 0.0
    for x in xs:
        s0 = x + c * s1 - s2
        s2, s1 = s1, s0
    return s1 * s1 + s2 * s2 - c * s1 * s2


def rms(xs):
    return math.sqrt(sum(x * x for x in xs) / max(1, len(xs)))


def load_capture(path):
    raw = open(path, "rb").read()
    n = len(raw) // 4
    v = struct.unpack("<%dh" % (2 * n), raw[:4 * n])
    return list(v[0::2]), list(v[1::2])


def onset(left, right, start, level):
    for i in range(start, len(left)):
        if abs(left[i]) > level or abs(right[i]) > level:
            return i
    return None


def silence_run(left, right, start, level, frames):
    """First index >= start where `frames` consecutive frames stay below level."""
    run = 0
    for i in range(start, len(left)):
        if abs(left[i]) <= level and abs(right[i]) <= level:
            run += 1
            if run >= frames:
                return i - frames + 1
        else:
            run = 0
    return None


def analyse_sequence(left, right, at, oracle, report, tag):
    ok = True
    level = 0
    for k, note in enumerate(oracle["notes"]):
        a = at + note["start_frame"] + 2205
        b = at + note["start_frame"] + note["frames"] - 2205
        segs = (left[a:b], right[a:b])
        f = note["hz"]
        res = []
        for ch, xs in zip(("L", "R"), segs):
            p, lo, hi = goertzel(xs, f), goertzel(xs, f * 0.8), goertzel(xs, f * 1.25)
            res.append((ch, rms(xs), p / max(lo, hi, 1e-9)))
        present = [r for r, want in zip(res, (note["left"], note["right"])) if want]
        absent = [r for r, want in zip(res, (note["left"], note["right"])) if not want]
        level = max(level, max(r[1] for r in present))
        good = all(r[1] > 200 and r[2] > 100 for r in present) and \
            all(r[1] < 0.05 * min(p[1] for p in present) for r in absent)
        ok &= good
        report.append(f"{tag} note{k + 1} {f}Hz " + " ".join(f"{c}:rms={v:.0f},dominance={d:.0f}" for c, v, d in res)
                      + (" OK" if good else " BAD"))
    return ok, level


def main():
    kind, oracle = sys.argv[1], json.load(open(sys.argv[2]))
    report, ok = [], True
    if kind == "pcm":
        pcm = open(sys.argv[3], "rb").read()
        ok = hashlib.sha256(pcm).hexdigest() == oracle["pcm_sha256"] and len(pcm) == oracle["pcm_bytes"]
        report.append(f"pcm bytes={len(pcm)} sha256={hashlib.sha256(pcm).hexdigest()}")
    else:
        mode = sys.argv[4]
        left, right = load_capture(sys.argv[3])
        report.append(f"capture frames={len(left)} seconds={len(left) / RATE:.2f}")
        first = onset(left, right, 0, 300)
        if first is None:
            print("VERIFY_CAPTURE FAIL no signal in capture")
            return 1
        seq = first
        if mode == "stoprestart":
            gap = silence_run(left, right, first, 30, int(0.3 * RATE))
            second = onset(left, right, gap, 300) if gap is not None else None
            if gap is None or second is None:
                print("VERIFY_CAPTURE FAIL no stop gap / no second play")
                return 1
            first_len, gap_len = (gap - first) / RATE, (second - gap) / RATE
            report.append(f"first_play_audible_s={first_len:.3f} silent_gap_after_stop_s={gap_len:.3f}")
            ok &= 0.5 < first_len < 1.2 and gap_len > 0.4
            seq = second
        good, level = analyse_sequence(left, right, seq, oracle, report, "seq")
        ok &= good
        end = seq + oracle["frames"]
        last = max((i for i in range(seq, min(len(left), end + RATE))
                    if abs(left[i]) > 0.05 * level or abs(right[i]) > 0.05 * level), default=seq)
        dur = (last - seq) / RATE
        report.append(f"sounding_duration_s={dur:.3f} expected_s={oracle['duration_s']:.3f}")
        ok &= abs(dur - oracle["duration_s"]) < 0.06
        tail = left[end + 4410:end + RATE] + right[end + 4410:end + RATE]
        report.append(f"after_end_rms={rms(tail):.1f} (window 0.1-1.0 s after end, {len(tail) // 2} frames)")
        ok &= len(tail) > 0.5 * RATE and rms(tail) < 0.01 * level
    print(("VERIFY_" + kind.upper()) + (" PASS" if ok else " FAIL"))
    for r in report:
        print("  " + r)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
