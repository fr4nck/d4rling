#!/usr/bin/env python3
"""Create an offline SH15 kit from exact committed tools + one authentic SH10 ZIP.

Only reads pinned input files; exclusive-creates one output ZIP. No download,
repository mutation, tool execution, installation, or guest. GPL-3.0-or-later.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

TOOL_GIT_BLOBS = {
    'sh12_cctools_replay.py': 'a4961c03b2c449a34e08f2d2736f36a599dfba6a',
    'darwin_archive_gate.py': '1c0229ccf6de6870add174a831837427e77a00b4',
    'i386_link_gate.py': '746855c0c9013aa0ee701035a2b1b5ffd7f8eac8',
    'macho_audit.py': '0ac6e95301ed563bfb12cadabb444fda520f3c09',
}
SH10_NAME = 'd4rling-SH10-archive-i386.zip'
SH10_SHA256 = '2fb5c48ecc0ab879a2f60285574f275dd320bc076a1d3ad587a9584adc2d542b'
SHELL_NAME = 'SH15-10400-portable.sh'
MAX_BYTES = 128 * 1024


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\x00' + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_file(path, max_bytes):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f'unavailable or symlinked input: {path.name}')
    size = path.stat().st_size
    if not 1 <= size <= max_bytes:
        raise ValueError(f'input size out of bounds: {path.name}')
    content = path.read_bytes()
    if len(content) != size:
        raise ValueError(f'input changed during read: {path.name}')
    return content


def create(source_dir: Path, sh10: Path, license_file: Path, output: Path) -> dict:
    source_dir = Path(source_dir)
    output = Path(output)
    if not source_dir.is_dir() or source_dir.is_symlink():
        raise ValueError('invalid fixture source directory')
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError('output parent does not exist or is symlinked')
    if output.exists() or output.is_symlink():
        raise ValueError('output exists, refusing to overwrite')
    files = {}
    for name, want in TOOL_GIT_BLOBS.items():
        src = checked_file(source_dir / name, MAX_BYTES)
        if git_blob(src) != want:
            raise ValueError(f'unexpected committed tool version: {name}')
        files[name] = src
    shell = checked_file(source_dir / SHELL_NAME, MAX_BYTES)
    if not shell.startswith(b'#!/usr/bin/env bash\n') or b'git hash-object --no-filters' not in shell:
        raise ValueError('invalid portable entrypoint')
    files[SHELL_NAME] = shell
    blob = checked_file(sh10, 1024 * 1024)
    if sha256(blob) != SH10_SHA256:
        raise ValueError('authentic SH10 ZIP does not match pinned SHA-256')
    with zipfile.ZipFile(sh10) as old:
        if old.testzip() is not None:
            raise ValueError('SH10 ZIP CRC failed')
    files[SH10_NAME] = blob
    license_text = checked_file(license_file, 128 * 1024)
    if b'GNU GENERAL PUBLIC LICENSE' not in license_text or b'Version 3' not in license_text[:300]:
        raise ValueError('full GPL-3 license is missing')
    files['LICENSE-GPL-3.0.txt'] = license_text
    readme = (
        'D4rling / SoundHack SH15 - portable offline 10400 linker replay\n\n'
        'From one new authorized Linux/WSL2 folder, extract all files without overwriting,\n'
        'then execute: bash SH15-10400-portable.sh\n\n'
        'The build must already exist at ~/atelier/d4rling-10400/build-core-i386.\n'
        'For other paths use D4RLING_10400_ROOT and/or D4RLING_BUILD_ROOT.\n'
        'This kit does NOT need an updated ~/atelier/d4rling checkout.\n'
        'It verifies the historical submodule git HEAD, exact tool Git blobs,\n'
        'SH10 ZIP, then selects precisely one ELF host linker from the build.\n'
        'It writes a fresh dylib ONLY on checked structural link success; otherwise\n'
        'it returns INCONCLUSIVE/BLOCKED and no app, guest, audio or Logic PASS.\n'
        'All files here are from the existing D4rling fixture set. Python tools\n'
        'are GPL-3.0-or-later; the nested SH10 package contains the original MIT\n'
        'license notice of Tom Erbe; no upstream FFT sources are redistributed.\n'
    )
    files['README-SH15.txt'] = readme.encode('utf-8')
    files['SHA256SUMS.txt'] = ''.join(
        f'{sha256(payload)}  {name}\n' for name, payload in sorted(files.items())
    ).encode('ascii')
    # Fixed timestamps and stable ordering make zip output byte-reproducible.
    with output.open('xb') as destination:
        with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
            for name in sorted(files):
                entry = zipfile.ZipInfo(name, date_time=(2026, 11, 10, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = (0o100644 << 16)
                zipped.writestr(entry, files[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(output) as zipped:
        if zipped.testzip() is not None or set(zipped.namelist()) != set(files):
            raise ValueError('output verification failed')
        if any(zipped.read(name) != data for name, data in files.items()):
            raise ValueError('output byte verification failed')
    return {'status': 'PORTABLE_KIT_CREATED', 'path': str(output), 'bytes': output.stat().st_size,
            'sha256': sha256(output.read_bytes()), 'members': sorted(files)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sh10-package', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--fixture-dir', type=Path, default=Path(__file__).resolve().parent)
    p.add_argument('--license', type=Path, default=Path(__file__).resolve().parents[3] / 'LICENSE')
    args = p.parse_args()
    try:
        result = create(args.fixture_dir, args.sh10_package, args.license, args.output)
    except (OSError, ValueError, zipfile.BadZipFile) as err:
        result = {'status': 'INCONCLUSIVE', 'error': str(err)}
        code = 3
    else:
        code = 0
    print(json.dumps(result, sort_keys=True, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
