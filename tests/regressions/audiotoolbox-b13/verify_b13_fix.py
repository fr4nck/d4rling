#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""B13 fixes: compare b13-fix outputs with b13-oracle.json.
  verify_b13_fix.py MEDIA_DIR OUT_DIR fix1|fix2"""
import hashlib, json, sys
from pathlib import Path
media, out, which = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
v = json.loads((media / "b13-oracle.json").read_text())["views"]
want = {"fix1": {"fix1-ulaw_s16.s16le": v["ulaw_decoded_s16le_sha256"], "fix1-ulaw_s16_after_cookie.s16le": v["ulaw_decoded_s16le_sha256"]},
        "fix2": {"fix2-convertbuffer-s16be.raw": v["s16be_sha256"], "fix2-complexbuffer-s16be-varchunks.raw": v["s16be_sha256"],
                 "fix2-convertbuffer-f32.raw": v["f32le_sha256"], "fix2-convertbuffer-f32-varchunks.raw": v["f32le_sha256"]}}[which]
ok = True
for name, h in want.items():
    p = out / name
    got = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    ok &= got == h
    print(f"VERIFY {name} {'PASS' if got == h else 'FAIL'} sha={str(got)[:16]} expected={h[:16]}")
print(f"VERIFY_SUMMARY {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
