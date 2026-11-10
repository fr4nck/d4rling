#!/usr/bin/env python3
"""R4-B: read-only Mach-O i386 segment inspection; never executes the guest."""
import argparse
import hashlib
import pathlib
import struct
import sys

MH_MAGIC = 0xfeedface
MH_CIGAM = 0xcefaedfe
FAT_MAGIC = 0xcafebabe
FAT_CIGAM = 0xbebafeca
CPU_I386 = 7
LC_SEGMENT = 1
MH_PIE = 0x200000


def inspect(data):
    if len(data) < 28:
        raise ValueError("truncated Mach-O header")
    magic = data[:4]
    if magic in (b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"):
        endian = ">" if magic == b"\xca\xfe\xba\xbe" else "<"
        if len(data) < 8:
            raise ValueError("truncated FAT header")
        nfat = struct.unpack_from(endian + "I", data, 4)[0]
        if nfat > 256 or 8 + nfat * 20 > len(data):
            raise ValueError("invalid FAT architecture table")
        slices = []
        for i in range(nfat):
            cpu, subtype, offset, size, align = struct.unpack_from(endian + "IIIII", data, 8 + i * 20)
            if cpu == CPU_I386:
                if offset < 8 + nfat * 20 or offset > len(data) or size > len(data) - offset:
                    raise ValueError("invalid FAT i386 bounds")
                slices.append(data[offset:offset + size])
        if len(slices) != 1:
            raise ValueError("expected exactly one i386 FAT slice")
        data = slices[0]
        magic = data[:4]
    if magic == b"\xce\xfa\xed\xfe":
        endian = "<"
    elif magic == b"\xfe\xed\xfa\xce":
        endian = ">"
    else:
        raise ValueError("not a 32-bit Mach-O executable")
    if len(data) < 28:
        raise ValueError("truncated Mach-O header")
    cpu, subtype, filetype, ncmds, sizeofcmds, flags = struct.unpack_from(endian + "IIIIII", data, 4)
    if cpu != CPU_I386:
        raise ValueError("Mach-O slice is not i386")
    if ncmds > 100000 or sizeofcmds > len(data) - 28:
        raise ValueError("invalid Mach-O command table")
    print("CPU=i386 FILETYPE=%d PIE=%s NCMDS=%d FLAGS=0x%x" %
          (filetype, bool(flags & MH_PIE), ncmds, flags))
    pos = 28
    end = pos + sizeofcmds
    count = 0
    for _ in range(ncmds):
        if pos + 8 > end:
            raise ValueError("truncated load command")
        cmd, size = struct.unpack_from(endian + "II", data, pos)
        if size < 8 or pos + size > end:
            raise ValueError("invalid load command size")
        if cmd == LC_SEGMENT:
            if size < 56:
                raise ValueError("truncated LC_SEGMENT")
            name, vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, sflags = struct.unpack_from(
                endian + "16sIIIIIIII", data, pos + 8)
            name = name.split(b"\x00", 1)[0].decode("ascii", "replace")
            print("SEGMENT=%s VMADDR=0x%x VMSIZE=0x%x FILEOFF=0x%x FILESIZE=0x%x INITPROT=0x%x MAXPROT=0x%x" %
                  (name, vmaddr, vmsize, fileoff, filesize, initprot, maxprot))
            count += 1
        pos += size
    if pos != end:
        raise ValueError("load commands do not consume sizeofcmds")
    if not count:
        raise ValueError("no LC_SEGMENT found")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("binary", type=pathlib.Path, help="existing Mach-O i386 binary")
    ap.add_argument("--stderr", type=pathlib.Path, help="existing R3 .stderr file")
    ap.add_argument("--loader", type=pathlib.Path, help="existing private mldr32 copy")
    args = ap.parse_args()
    for p in (args.binary, args.stderr, args.loader):
        if p is not None and (not p.is_file() or p.is_symlink()):
            ap.error("missing file or symlink refused: %s" % p)
    data = args.binary.read_bytes()
    print("BINARY=%s SHA256=%s" % (args.binary, hashlib.sha256(data).hexdigest()))
    inspect(data)
    if args.stderr:
        lines = args.stderr.read_text(errors="replace").splitlines()
        matches = [x for x in lines if "Cannot mmap segment" in x or "Library not loaded:" in x]
        print("STDERR_MATCHES=%d" % len(matches))
        for x in matches[:8]:
            print("STDERR=%s" % x[:400])
    if args.loader:
        print("LOADER=%s SHA256=%s" % (args.loader, hashlib.sha256(args.loader.read_bytes()).hexdigest()))
    try:
        print("MMAP_MIN_ADDR=%s" % pathlib.Path("/proc/sys/vm/mmap_min_addr").read_text().strip())
    except OSError:
        print("MMAP_MIN_ADDR=UNAVAILABLE")
    print("NOTE: vmaddr is the original Mach-O address; effective mapping may include slide.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, struct.error) as exc:
        print("BLOCKED: %s" % exc, file=sys.stderr)
        sys.exit(2)
