#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate a tiny fixed-address i386 Mach-O executable without a Darwin SDK.

This is a loader smoke fixture. It calls Linux i386 int 0x80 directly and
must NOT be interpreted as a test of Darwin/libSystem syscall translation.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import struct
from pathlib import Path

MH_MAGIC = 0xFEEDFACE
CPU_TYPE_I386 = 7
CPU_SUBTYPE_I386_ALL = 3
MH_EXECUTE = 2
MH_NOUNDEFS = 1
LC_SEGMENT = 1
LC_UNIXTHREAD = 5
X86_THREAD_STATE32 = 1
THREAD_STATE32_WORDS = 16
PAGE_SIZE = 4096
CODE_OFFSET = 0x200
EXIT_STATUS = 43
MARKER = b"D4RLING_I386_MACHO_OK\n"


def _pack_name(name: str) -> bytes:
    encoded = name.encode("ascii")
    if len(encoded) > 16:
        raise ValueError("Mach-O name too long")
    return encoded.ljust(16, b"\0")


def _segment(
    name: str,
    vmaddr: int,
    vmsize: int,
    fileoff: int,
    filesize: int,
    maxprot: int,
    initprot: int,
    sections: bytes = b"",
) -> bytes:
    if len(sections) % 68:
        raise ValueError("invalid 32-bit section length")
    return struct.pack(
        "<II16s8I",
        LC_SEGMENT,
        56 + len(sections),
        _pack_name(name),
        vmaddr,
        vmsize,
        fileoff,
        filesize,
        maxprot,
        initprot,
        len(sections) // 68,
        0,
    ) + sections


def make_binary(base: int = 0x100000) -> bytes:
    """Return a deterministic, one-page Mach-O i386 executable.

    Entry is specified via LC_UNIXTHREAD, not a dyld or libSystem dependency.
    A successful guest run prints MARKER and exits with EXIT_STATUS.
    """
    if (
        not isinstance(base, int)
        or base < 0x10000
        or base % PAGE_SIZE
        or base > 0xFFFFFFFF - PAGE_SIZE
    ):
        raise ValueError("base must be page-aligned between 0x10000 and 0xffffefff")

    # mov eax,4; mov ebx,1; mov ecx,address; mov edx,len; int 0x80;
    # mov eax,1; mov ebx,43; int 0x80; ud2
    # Linux i386 syscalls, not Darwin syscalls.
    code = (
        b"\xb8\x04\x00\x00\x00"
        b"\xbb\x01\x00\x00\x00"
        b"\xb9" + struct.pack("<I", base + CODE_OFFSET + 36)
        + b"\xba" + struct.pack("<I", len(MARKER))
        + b"\xcd\x80"
        + b"\xb8\x01\x00\x00\x00"
        + b"\xbb" + struct.pack("<I", EXIT_STATUS)
        + b"\xcd\x80\x0f\x0b"
    )
    if len(code) != 36:
        raise AssertionError("unexpected instruction size")

    section = struct.pack(
        "<16s16s9I",
        _pack_name("__text"),
        _pack_name("__TEXT"),
        base + CODE_OFFSET,
        len(code),
        CODE_OFFSET,
        4,
        0,
        0,
        0x80000400,
        0,
        0,
    )
    pagezero = _segment("__PAGEZERO", 0, base, 0, 0, 0, 0)
    text = _segment("__TEXT", base, PAGE_SIZE, 0, PAGE_SIZE, 7, 5, section)

    # x86_thread_state32_t: EIP is index 10 of 16 uint32 registers.
    registers = [0] * THREAD_STATE32_WORDS
    registers[10] = base + CODE_OFFSET
    thread = struct.pack("<4I", LC_UNIXTHREAD, 80, X86_THREAD_STATE32,
                         THREAD_STATE32_WORDS) + struct.pack("<16I", *registers)
    commands = pagezero + text + thread
    header = struct.pack(
        "<7I", MH_MAGIC, CPU_TYPE_I386, CPU_SUBTYPE_I386_ALL,
        MH_EXECUTE, 3, len(commands), MH_NOUNDEFS,
    )
    if len(header) + len(commands) > CODE_OFFSET:
        raise AssertionError("load commands overlap entry")
    if CODE_OFFSET + len(code) + len(MARKER) > PAGE_SIZE:
        raise AssertionError("fixture exceeds the text page")

    data = bytearray(PAGE_SIZE)
    data[:len(header)] = header
    data[len(header):len(header) + len(commands)] = commands
    data[CODE_OFFSET:CODE_OFFSET + len(code)] = code
    data[CODE_OFFSET + len(code):CODE_OFFSET + len(code) + len(MARKER)] = MARKER
    return bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="new fixture path; refuses to replace existing files")
    parser.add_argument("--base", type=lambda raw: int(raw, 0), default=0x100000,
                        help="page-aligned i386 VM base, e.g. 0x100000")
    args = parser.parse_args()
    try:
        binary = make_binary(args.base)
        # O_EXCL avoids clobbering a user file or following a leaf symlink.
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(binary)
                stream.flush()
                os.fchmod(stream.fileno(), 0o755)
        except BaseException:
            args.output.unlink(missing_ok=True)
            raise
    except (ValueError, OSError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(f"output={args.output}")
    print(f"base=0x{args.base:x}")
    print(f"entry=0x{args.base + CODE_OFFSET:x}")
    print(f"sha256={hashlib.sha256(binary).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
