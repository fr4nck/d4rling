#!/usr/bin/env python3
"""SH10: create and qualify a deterministic Darwin i386 static FFT archive.

Copyright (C) 2026 D4rling contributors. GPL-3.0-or-later.
No upstream source or SDK bundled. Not a dyld/runtime/audio test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from macho_audit import InvalidMachO, parse as parse_macho
from i386_link_gate import (
    ContractFailure, Inconclusive, EXPECTED_GLOBAL_DEFS, EXPECTED_SH08_SHA256,
    DYNAMIC_MATH, INSTALL_NAME, MAX_INPUT, compile_globals, inspect_macho,
    verify_linked,
)

MAX_ARCHIVE_BYTES = 2 * 1024 * 1024
MEMBERS = ('fft.o', 'globals.o')


def executable(name):
    located = shutil.which(name)
    if not located:
        raise Inconclusive('tool unavailable: ' + name)
    return located


def run_checked(argv, *, max_output=MAX_ARCHIVE_BYTES):
    """Bound process duration/output; never shell out or change host settings."""
    try:
        proc = subprocess.run(argv, capture_output=True, timeout=25, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Inconclusive('tool invocation failed: ' + str(exc)) from exc
    if len(proc.stdout) > max_output or len(proc.stderr) > 8192:
        raise Inconclusive('oversized tool output')
    return proc


def check_archive(path, ar, obj_bytes, globals_bytes):
    path = Path(path)
    if not path.is_file() or not (128 <= path.stat().st_size <= MAX_ARCHIVE_BYTES):
        raise ContractFailure('archive absent or outside size limits')
    raw = path.read_bytes()
    if not raw.startswith(b'!<arch>\n'):
        raise ContractFailure('archive missing standard ar signature')
    ar_tool = executable(ar)
    members = run_checked([ar_tool, 't', str(path)])
    if members.returncode:
        raise Inconclusive('llvm-ar could not list members: ' + members.stderr.decode(errors='replace')[-280:])
    try:
        names = members.stdout.decode('ascii').splitlines()
    except UnicodeDecodeError as exc:
        raise ContractFailure('non-ASCII archive member name') from exc
    if names != list(MEMBERS):
        raise ContractFailure('unexpected member ordering or count: ' + repr(names))
    index_tool = executable('llvm-objdump')
    detail = run_checked([index_tool, '--macho', '--archive-headers', str(path)])
    if detail.returncode or b'__.SYMDEF' not in detail.stdout:
        raise ContractFailure('Darwin __.SYMDEF archive index missing or unreadable')
    members_report = []
    for name, original in zip(MEMBERS, (obj_bytes, globals_bytes)):
        result = run_checked([ar_tool, 'p', str(path), name])
        if result.returncode:
            raise ContractFailure('cannot inspect archive member ' + name)
        # LLVM Darwin archive members are eight-byte aligned, with LF padding.
        padding = (-len(original)) % 8
        expected = original + b'\n' * padding
        if result.stdout != expected:
            raise ContractFailure('member changed except for documented Darwin padding: ' + name)
        try:
            info = parse_macho(result.stdout, 'i386')
        except InvalidMachO as exc:
            raise ContractFailure('invalid i386 member: ' + name) from exc
        if info['bits'] != 32 or info['filetype'] != 1 or info['has_dyld_info']:
            raise ContractFailure('archive contains non-relocatable or foreign member')
        if info['symbol_caveats'] or not info['has_symtab']:
            raise Inconclusive('member symbol table not fully qualified: ' + name)
        expected_defs = EXPECTED_GLOBAL_DEFS if name == 'globals.o' else None
        defs = set(info['exports_nlist'])
        if expected_defs is not None and defs != expected_defs:
            raise ContractFailure('companion definitions differ')
        if name == 'globals.o' and info['imports_nlist']:
            raise ContractFailure('companion has unexpected undefined imports')
        members_report.append({
            'name': name, 'arch': info['arch'], 'filetype': info['filetype'],
            'original_sha256': hashlib.sha256(original).hexdigest(),
            'original_bytes': len(original), 'stored_bytes': len(result.stdout),
            'darwin_padding_lf_bytes': padding,
            'definitions': sorted(defs), 'undefined': info['imports_nlist'],
        })
    aggregate = set(members_report[0]['undefined']) - set(members_report[1]['definitions'])
    if aggregate != DYNAMIC_MATH:
        raise ContractFailure('aggregate unresolved names not precisely sin/sinf: ' + repr(aggregate))
    return {
        'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
        'archive_format': 'darwin', 'has_symbol_index': True,
        'members': members_report, 'unresolved_after_archive': sorted(aggregate),
    }


def try_link_archive(archive, linker, folder):
    """Attempt real cctools ld64; no fake linker or Mach-O output is accepted."""
    name = executable(linker)
    flags = (['-platform_version', 'macos', '10.5', '10.5']
             if Path(name).name.startswith('ld64.lld') else ['-macosx_version_min', '10.5'])
    product = folder / 'libSH09OriginalFFT.dylib'
    cmd = [name, '-arch', 'i386', '-dylib', *flags,
           '-undefined', 'dynamic_lookup', '-install_name', INSTALL_NAME,
           '-all_load', str(archive), '-o', str(product)]
    proc = run_checked(cmd, max_output=100000)
    if proc.returncode:
        return {
            'status': 'LINK_TOOLCHAIN_BLOCKED', 'linker_returncode': proc.returncode,
            'linker_stderr_tail': proc.stderr.decode(errors='replace').strip()[-500:],
        }
    if not product.is_file():
        raise ContractFailure('linker returned success without output')
    try:
        linked = verify_linked(product)
    except Inconclusive as exc:
        # A real dylib may use LC_DYLD_INFO, which the current bounded
        # reader intentionally refuses to treat as a resolved ABI.
        return {'status': 'LINK_UNVERIFIED', 'reason': str(exc),
                'observed_output_bytes': product.stat().st_size}
    return {'status': 'LINK_STRUCTURE_PASS', 'linked': linked}


def qualify(object_path, expected_sha256=EXPECTED_SH08_SHA256, *,
            clang='clang', ar='llvm-ar', linker=None, output=None):
    original_info = inspect_macho(object_path, expected_sha256)
    original = Path(object_path).read_bytes()
    if hashlib.sha256(original).hexdigest() != original_info['sha256']:
        raise Inconclusive('original SH08 object changed after verification')
    with tempfile.TemporaryDirectory(prefix='d4rl-sh10-') as tmp:
        folder = Path(tmp)
        in_obj = folder / MEMBERS[0]
        in_obj.write_bytes(original)
        globals_obj = compile_globals(clang, folder)
        comp = globals_obj.read_bytes()
        archive_globals = folder / MEMBERS[1]
        archive_globals.write_bytes(comp)
        archive = folder / 'libSoundHackFFT_i386.a'
        tool = executable(ar)
        proc = run_checked([tool, '--format=darwin', 'rcD', str(archive), str(in_obj), str(archive_globals)])
        if proc.returncode:
            raise Inconclusive('Darwin archive tool failed: ' + proc.stderr.decode(errors='replace')[-400:])
        info = check_archive(archive, ar, original, comp)
        result = {
            'status': 'DARWIN_ARCHIVE_PASS',
            'scope': 'static archive with authentic SH08 FFT MH_OBJECT; NOT linked dylib, guest or audio',
            'source_object': original_info, 'archive': info,
        }
        if linker:
            link_result = try_link_archive(archive, linker, folder)
            result['link_attempt'] = link_result
            result['status'] = link_result['status']
        if output is not None:
            dest = Path(output)
            try:
                # Create only after all checks, exclusive no-overwrite or symlink following.
                with dest.open('xb') as fd:
                    fd.write(archive.read_bytes())
            except OSError as exc:
                raise Inconclusive('archive output not created: ' + str(exc)) from exc
            result['saved_archive'] = str(dest)
    # Ensure the supplied original SH08 object was never modified.
    if hashlib.sha256(Path(object_path).read_bytes()).hexdigest() != original_info['sha256']:
        raise ContractFailure('source object modified during archive qualification')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--object', required=True, help='legitimate SH08 target i386 object')
    parser.add_argument('--expected-sha256', default=EXPECTED_SH08_SHA256)
    parser.add_argument('--clang', default='clang')
    parser.add_argument('--llvm-ar', default='llvm-ar')
    parser.add_argument('--ld64', default=None, help='optional installed cctools-port ld64 executable path')
    parser.add_argument('--output', default=None, help='optional new archive path; never overwrites')
    args = parser.parse_args(argv)
    try:
        result = qualify(args.object, args.expected_sha256,
                         clang=args.clang, ar=args.llvm_ar, linker=args.ld64,
                         output=args.output)
    except ContractFailure as exc:
        result, status = {'status': 'TARGET_CONTRACT_FAIL', 'error': str(exc)}, 2
    except (Inconclusive, InvalidMachO, ValueError, OSError) as exc:
        result, status = {'status': 'INCONCLUSIVE', 'error': str(exc)}, 3
    else:
        status = 0 if result['status'] in ('DARWIN_ARCHIVE_PASS', 'LINK_STRUCTURE_PASS') else 3
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return status


if __name__ == '__main__':
    sys.exit(main())
