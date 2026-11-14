#!/usr/bin/env python3
"""QT-B12: is the sink-monitor capture (S16LE) sample-identical to the MOV PCM
(S16BE), at some alignment? Usage: bitexact.py MOV_PCM CAPTURE.raw [min_start]"""
import struct, sys
pcm = open(sys.argv[1], "rb").read()
cap = open(sys.argv[2], "rb").read()
start = int(sys.argv[3]) if len(sys.argv) > 3 else 0
n = len(pcm) // 4
ref = struct.unpack(">%dh" % (2 * n), pcm)
m = len(cap) // 4
got = struct.unpack("<%dh" % (2 * m), cap[:4 * m])
first_ref = next(i for i in range(n) if ref[2 * i] or ref[2 * i + 1])
key = ref[2 * first_ref: 2 * first_ref + 64]
hits = [j for j in range(start, m - 32) if got[2 * j: 2 * j + 64] == key]
if not hits:
    print("BITEXACT NO_ALIGNMENT"); sys.exit(1)
off = hits[0] - first_ref
same = sum(1 for i in range(n) if 0 <= off + i < m and got[2 * (off + i)] == ref[2 * i] and got[2 * (off + i) + 1] == ref[2 * i + 1])
print(f"BITEXACT alignment_frame={off} identical_frames={same}/{n} {'IDENTICAL' if same == n else 'DIFFERENT'}")
sys.exit(0 if same == n else 1)
