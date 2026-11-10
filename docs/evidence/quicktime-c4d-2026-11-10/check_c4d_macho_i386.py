#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""C4-D-M2: read-only i386 Mach-O gate for the QuickTime reexport chain.

Reuses the pinned SoundHack Mach-O reader. This is NOT a dyld, ABI,
GetMediaSample behavior, memory-safety, audio, or Logic Studio 8 test.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PARSER = ROOT / 'reproduction/fixtures/soundhack-i386/macho_audit.py'
PARSER_BLOB = '0ac6e95301ed563bfb12cadabb444fda520f3c09'
SYMS = ('_GetHandleSize', '_SetHandleSize', '_MemError')
FRAMEWORKS = ('QuickTime', 'CoreServices', 'CarbonCore')


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()


def load_reader():
    data = PARSER.read_bytes()
    if git_blob(data) != PARSER_BLOB:
        raise ValueError('shared Mach-O reader changed: requalify pinned Git blob')
    spec = importlib.util.spec_from_file_location('d4rling_c4d_m2_reader', PARSER)
    if spec is None or spec.loader is None:
        raise ValueError('shared Mach-O reader unavailable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def framework_path(name: object, framework: str) -> bool:
    """Identify a framework by its full path suffix, not basename alone."""
    if not isinstance(name, str):
        return False
    parts = name.split('/')
    if len(parts) >= 2 and parts[-2:] == [framework + '.framework', framework]:
        return True
    return (len(parts) >= 4 and parts[-4] == framework + '.framework'
            and parts[-3] == 'Versions' and bool(parts[-2]) and parts[-1] == framework)


def assess(images: dict[str, dict]) -> dict:
    """Classify only observable load commands and nlist records.

    exit=0: structurally consistent nlist gate, not a successful dyld bind.
    exit=2: demonstrable contract violation.
    exit=3: necessary static evidence is unavailable or ambiguous.
    """
    errors: list[str] = []
    unknown: list[str] = []
    evidence: dict[str, object] = {}
    for framework in FRAMEWORKS:
        if framework not in images:
            unknown.append(f'{framework}: image unavailable')
            continue
        info = images[framework]
        if info.get('arch') != 'i386' or info.get('bits') != 32 or info.get('cputype') != 7:
            errors.append(f'{framework}: expected Mach-O i386 32-bit slice')
        if info.get('filetype') != 6:
            errors.append(f'{framework}: expected MH_DYLIB')
        if not framework_path(info.get('install_name'), framework):
            errors.append(f'{framework}: missing/incorrect LC_ID_DYLIB')
        if not isinstance(info.get('dylibs'), list):
            unknown.append(f'{framework}: dependency commands unavailable')
        evidence[framework] = {
            'install_name': info.get('install_name'),
            'has_symtab': info.get('has_symtab', False),
            'has_dyld_info': info.get('has_dyld_info', False),
        }
    if len(images) != len(FRAMEWORKS) or unknown:
        return {'status': 'STATIC_FAIL' if errors else 'STATIC_INCONCLUSIVE',
                'exit_code': 2 if errors else 3, 'errors': errors,
                'inconclusive': unknown, 'evidence': evidence}

    # The shared reader does not decode dyld bind/export opcodes. A complete
    # nlist cannot certify that the dyld-visible dependency set is complete.
    # Keep explicit structural violations authoritative (FAIL before UNKNOWN).
    for framework in FRAMEWORKS:
        if images[framework].get('has_dyld_info'):
            unknown.append(f'{framework}: LC_DYLD_INFO present; bind/export opcodes uninspected')

    qt, cs, cc = (images[name] for name in FRAMEWORKS)
    def find_dep(source: dict, target: str) -> list[dict]:
        return [dep for dep in source['dylibs'] if framework_path(dep.get('name'), target)]

    qc = find_dep(qt, 'CoreServices')
    rc = find_dep(cs, 'CarbonCore')
    direct_cc = find_dep(qt, 'CarbonCore')
    if len(qc) != 1 or qc[0].get('kind') not in {'load', 'reexport'}:
        errors.append('QuickTime: expected one LC_LOAD_DYLIB to CoreServices')
    elif qc[0].get('name') != cs.get('install_name'):
        unknown.append('QuickTime: CoreServices dependency differs from its LC_ID_DYLIB')
    if len(rc) != 1 or rc[0].get('kind') != 'reexport':
        errors.append('CoreServices: expected one LC_REEXPORT_DYLIB to CarbonCore')
    elif rc[0].get('name') != cc.get('install_name'):
        unknown.append('CoreServices: CarbonCore reexport differs from its LC_ID_DYLIB')
    if direct_cc:
        errors.append('QuickTime: unexpected direct CarbonCore dependency')
    evidence['chain'] = {
        'quicktime_to_coreservices': qc,
        'coreservices_reexports_carboncore': rc,
        'direct_quicktime_to_carboncore': direct_cc,
    }

    for framework, expected in [('QuickTime', ('_GetMediaSample',)),
                                ('CarbonCore', SYMS)]:
        info = images[framework]
        if not info.get('has_symtab'):
            unknown.append(f'{framework}: LC_SYMTAB unavailable')
            continue
        exports = set(info.get('exports_nlist', []))
        for symbol in expected:
            if symbol not in exports:
                # nlist may be stripped while dyld exports exist; no export-trie
                # parser is included, so absence alone cannot prove a stub.
                unknown.append(f'{framework}: {symbol} not visible in nlist exports')
    if not qt.get('two_level_namespace'):
        unknown.append('QuickTime: two-level namespace unavailable')
    if not qt.get('has_symtab'):
        unknown.append('QuickTime: cannot inspect nlist imports')
    else:
        details = qt.get('imports_detail', [])
        for symbol in SYMS:
            matched = [d for d in details if d.get('name') == symbol]
            if not matched:
                unknown.append(f'QuickTime: {symbol} not observable as nlist import')
            elif len(matched) > 1:
                unknown.append(f'QuickTime: {symbol} has multiple nlist entries')
            else:
                imp = matched[0]
                if imp.get('lookup') != 'library':
                    unknown.append(f'QuickTime: {symbol} uses non-library lookup')
                elif imp.get('library_name') != cs.get('install_name'):
                    errors.append(f'QuickTime: {symbol} references wrong dylib ordinal')
                if imp.get('common_or_prebound') or imp.get('reference_to_weak'):
                    unknown.append(f'QuickTime: {symbol} uses ambiguous/common/weak-reference encoding')
                if imp.get('weak_import'):
                    errors.append(f'QuickTime: {symbol} unexpectedly weak-imported')
    evidence['nlist_required'] = {'QuickTime': ['_GetMediaSample'], 'CarbonCore': list(SYMS),
                                  'QuickTime_imports': list(SYMS)}
    status = 'STATIC_FAIL' if errors else ('STATIC_INCONCLUSIVE' if unknown else 'STATIC_GATE_PASS')
    return {
        'status': status, 'exit_code': 2 if errors else (3 if unknown else 0),
        'errors': errors, 'inconclusive': unknown, 'evidence': evidence,
        'limitations': ['nlist and load commands only; export trie/bind opcodes not resolved',
                        'no C4 ABI, GetMediaSample behavior, guest execution, audio or Logic validation',
                        'three inputs must be from one coherent authorized build: provenance is not proven'],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in FRAMEWORKS:
        parser.add_argument('--' + name.lower(), required=True, type=Path)
    args = parser.parse_args(argv)
    paths = {name: getattr(args, name.lower()) for name in FRAMEWORKS}
    if len({str(path.resolve()) for path in paths.values()}) != len(paths):
        print(json.dumps({'status': 'BLOCKED', 'error': 'distinct dylib files required'}))
        return 3
    try:
        reader = load_reader()
        inspected = {name: reader.inspect(path, 'i386') for name, path in paths.items()}
        result = assess(inspected)
        result['inputs'] = {name: {'file': inspected[name]['file'],
                                    'sha256': inspected[name]['sha256']}
                            for name in FRAMEWORKS}
        result['shared_parser_git_blob'] = PARSER_BLOB
    except (OSError, ValueError) as exc:
        result = {'status': 'BLOCKED', 'exit_code': 3, 'error': str(exc)}
    print(json.dumps(result, sort_keys=True, indent=2))
    return result['exit_code']


if __name__ == '__main__':
    sys.exit(main())
