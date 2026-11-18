#!/usr/bin/env python3
"""FAT64 / issue #18 : variantes d'en-tête d'un dyld universel FAT32, tranches inchangées.
usage: makedyld.py DYLD OUTDIR"""
import os, struct, sys
src = open(sys.argv[1], 'rb').read(); out = sys.argv[2]
magic, n = struct.unpack('>II', src[:8]); assert magic == 0xcafebabe, hex(magic)
recs = [struct.unpack('>IIIII', src[8 + 20 * i: 28 + 20 * i]) for i in range(n)]
first = min(r[2] for r in recs); assert 8 + 32 * n <= first
def emit(name, hdr):
    data = hdr + src[len(hdr):]
    assert data[first:] == src[first:]
    os.makedirs(os.path.join(out, name, 'usr/lib'), exist_ok=True)
    p = os.path.join(out, name, 'usr/lib/dyld'); open(p, 'wb').write(data); os.chmod(p, 0o755)
    print(name, data[:4].hex(), [(hex(c), o, s) for c, _, o, s, _ in recs])
def pad(h): return h + b'\0' * (first - len(h)) if len(h) <= first else None
emit('dyld-fat64', pad(struct.pack('>II', 0xcafebabf, n) + b''.join(struct.pack('>IIQQII', c, sc, o, s, a, 0) for c, sc, o, s, a in recs)))
emit('dyld-fat64le', pad(struct.pack('<II', 0xcafebabf, n) + b''.join(struct.pack('<IIQQII', c, sc, o, s, a, 0) for c, sc, o, s, a in recs)))
emit('dyld-fat32le', pad(struct.pack('<II', 0xcafebabe, n) + b''.join(struct.pack('<IIIII', *r) for r in recs)))
emit('dyld-hugecount', pad(struct.pack('>II', 0xcafebabe, 0xffffffff) + b''.join(struct.pack('>IIIII', *r) for r in recs)))
bad = [(c, sc, o, (len(src) - o + 4096) if c == 0x01000007 else s, a) for c, sc, o, s, a in recs]
emit('dyld-x64-past-eof', pad(struct.pack('>II', 0xcafebabe, n) + b''.join(struct.pack('>IIIII', *r) for r in bad)))
