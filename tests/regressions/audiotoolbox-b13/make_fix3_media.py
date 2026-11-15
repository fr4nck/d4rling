#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ATB-FIX3: media for the format recognition oracle, derived from the B13 media (make_b13_media.py).
Usage: make_fix3_media.py B13_MEDIA_DIR OUT_DIR
  demo-s16.aifc    a real AIFF-C file (FORM AIFC, FVER, COMM with compression 'NONE') holding the
                   same big-endian 16-bit samples as demo-s16.aiff
  demo-s16.aif     demo-s16.aiff under the other AIFF extension
  bad-garbage.zzzq bad-garbage.wav under an extension no component declares
  bad-empty.zzzq   an empty file under that extension
Writes fix3-media.json (SHA-256 of every file)."""
import hashlib, json, struct, sys
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)

aiff = (src / 'demo-s16.aiff').read_bytes()
assert aiff[:4] == b'FORM' and aiff[8:12] == b'AIFF'
chunks, pos = {}, 12
while pos + 8 <= len(aiff):
    cid, size = aiff[pos:pos + 4], struct.unpack('>I', aiff[pos + 4:pos + 8])[0]
    chunks[cid] = aiff[pos + 8:pos + 8 + size]
    pos += 8 + size + (size & 1)
comm, ssnd = chunks[b'COMM'], chunks[b'SSND']
assert len(comm) == 18

def chunk(cid, data):
    return cid + struct.pack('>I', len(data)) + data + (b'\0' if len(data) & 1 else b'')

name = b'not compressed'
pstring = bytes([len(name)]) + name
if len(pstring) & 1:
    pstring += b'\0'
body = b'AIFC' + chunk(b'FVER', struct.pack('>I', 0xA2805140)) + chunk(b'COMM', comm + b'NONE' + pstring) + chunk(b'SSND', ssnd)
files = {
    'demo-s16.aifc': b'FORM' + struct.pack('>I', len(body)) + body,
    'demo-s16.aif': aiff,
    'bad-garbage.zzzq': (src / 'bad-garbage.wav').read_bytes(),
    'bad-empty.zzzq': b'',
}
for n, d in files.items():
    (out / n).write_bytes(d)
meta = {n: {'bytes': len(d), 'sha256': hashlib.sha256(d).hexdigest()} for n, d in files.items()}
meta['source'] = {n: hashlib.sha256((src / n).read_bytes()).hexdigest() for n in ['demo-s16.aiff', 'bad-garbage.wav']}
(out / 'fix3-media.json').write_text(json.dumps(meta, indent=2) + '\n')
print(json.dumps(meta))
