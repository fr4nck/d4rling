#!/usr/bin/env python3
"""FAT64 / issue #18 : fichiers universels synthétiques à partir de deux Mach-O minces (i386, x86_64).
usage: makefat.py I386 X86_64 OUTDIR"""
import os, struct, sys
i386, x64 = (open(p, 'rb').read() for p in sys.argv[1:3]); out = sys.argv[3]
X86, X86_64 = 7, 0x01000007
ALIGN = 1 << 12
def build(name, recs, wide=False, big=True, count=None, trunc=None):
    """recs : (cputype, blob ou None, offset forcé ou None, taille forcée ou None)"""
    e = '>' if big else '<'
    magic = (0xcafebabf if wide else 0xcafebabe)
    width = 32 if wide else 20
    pos = ALIGN; body = b''; rows = []
    for cpu, blob, off, size in recs:
        o = pos if off is None else off
        if blob is not None:
            body += b'\0' * (pos - ALIGN - len(body)) + blob
            pos = (pos + len(blob) + ALIGN - 1) // ALIGN * ALIGN
        s = len(blob) if size is None else size
        if wide: rows.append(struct.pack(e + 'IIQQII', cpu, 3, o, s, 12, 0))
        else:    rows.append(struct.pack(e + 'IIIII', cpu, 3, o, s, 12))
    hdr = struct.pack('>I', magic) if big else struct.pack('<I', magic)
    hdr += struct.pack(e + 'I', len(recs) if count is None else count) + b''.join(rows)
    data = hdr + b'\0' * (ALIGN - len(hdr)) + body
    if trunc is not None: data = data[:trunc]
    p = os.path.join(out, name)
    open(p, 'wb').write(data); os.chmod(p, 0o755)
    print(f"{name} size={len(data)} magic={data[:4].hex()} nrec={len(recs)} count={len(recs) if count is None else count}")
both = [(X86, i386, None, None), (X86_64, x64, None, None)]
build('fat32-both', both)
build('fat64-both', both, wide=True)
build('fat64le-both', both, wide=True, big=False)
build('fat32-i386', [(X86, i386, None, None)])
build('fat64-i386', [(X86, i386, None, None)], wide=True)
# premier enregistrement x86_64 hors du fichier, second i386 valide
build('fat32-bad-x86_64', [(X86, i386, None, None), (X86_64, None, ALIGN, 1 << 30)])
build('fat64-past-eof', [(X86_64, x64, None, len(x64) + (1 << 20))], wide=True)
build('fat32-hugecount', both, count=0xffffffff)
