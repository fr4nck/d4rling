#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Host contract tests compiling the real CarbonCore/Gestalt.cpp translation unit.

A test-only sysctl shim supplies the Darwin release. No Apple SDK, Darling
installation, guest runtime, Carbon feature claims, or production mutation.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'src/frameworks/CoreServices/src/CarbonCore/Gestalt.cpp'
HEADERS = ROOT / 'src/frameworks/CoreServices/include'
HEADER_BLOB = '127736fadc13fd6d64a8d87b9f912613660acfbd'


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def run(source: Path, compiler: str, expect_source_blob: str | None) -> int:
    if not source.is_file():
        raise RuntimeError('Gestalt source missing')
    raw = source.read_bytes()
    if len(raw) > 64 * 1024:
        raise RuntimeError('Gestalt source exceeds the file bound')
    blob = git_blob(raw)
    if expect_source_blob is not None and blob != expect_source_blob:
        raise RuntimeError('Gestalt source Git blob differs: ' + blob)
    header = HEADERS / 'CarbonCore/Gestalt.h'
    if git_blob(header.read_bytes()) != HEADER_BLOB:
        raise RuntimeError('Gestalt selector header changed: requalify test')
    cxx = shutil.which(compiler)
    if not cxx:
        raise RuntimeError('C++ compiler absent')
    with tempfile.TemporaryDirectory(prefix='d4-carbon-gestalt-') as temp:
        root = Path(temp)
        (root / 'include/CarbonCore').mkdir(parents=True)
        (root / 'include/sys').mkdir()
        (root / 'include/CarbonCore/MacErrors.h').write_text(
            '#pragma once\nconstexpr OSStatus unimpErr = -4;\nconstexpr OSStatus paramErr = -50;\n', encoding='utf8')
        (root / 'include/sys/sysctl.h').write_text('''#pragma once
#include <cstddef>
#define CTL_KERN 1
#define KERN_OSRELEASE 2
extern "C" int sysctl(const int*, unsigned int, void*, size_t*, const void*, size_t);
''', encoding='utf8')
        (root / 'include/prelude.h').write_text('''#pragma once
#include <cstdint>
using OSStatus = int;
''', encoding='utf8')
        (root / 'contract.cpp').write_text(r'''#include <CarbonCore/Gestalt.h>
#include <sys/sysctl.h>
#include <cstdio>
#include <cstring>

static const char* mock_release = "20.4.0";
static int sysctl_calls = 0;
static int sysctl_mode = 0;
extern "C" int sysctl(const int* name, unsigned int n, void* dst, size_t* len,
                      const void*, size_t) {
  ++sysctl_calls;
  if (n != 2 || name[0] != CTL_KERN || name[1] != KERN_OSRELEASE || !len) return -1;
  if (sysctl_mode == 1) return -1;
  if (sysctl_mode == 2) { *len = 0; return 0; }
  if (sysctl_mode == 3) { *len = 999; return 0; }
  const size_t needed = std::strlen(mock_release) + 1;
  if (!dst || *len < needed) return -1;
  if (sysctl_mode == 5) {
    std::memcpy(dst, mock_release, needed - 1); // non-NUL-terminated kernel output
    *len = needed - 1;
  } else {
    std::memcpy(dst, mock_release, needed);
    *len = needed;
  }
  return 0;
}

static int passed = 0;
static int failed = 0;
static void check(const char* label, uint32_t selector, int error, int value,
                  int expected_sysctls) {
  int out = 0x5555;
  const int before = sysctl_calls;
  const int rc = Gestalt(selector, &out);
  const int calls = sysctl_calls - before;
  if (rc != error || out != value || calls != expected_sysctls) {
    std::fprintf(stderr, "FAIL %s: rc=%d value=%d calls=%d; expected %d %d %d\n",
                 label, rc, out, calls, error, value, expected_sysctls);
    ++failed;
  } else {
    ++passed;
  }
}
int main() {
  // These are the existing Darwin-kernel-based values, NOT macOS versions.
  check("sysv 20.4.0", gestaltSystemVersion, 0, 0x1440, 1);
  check("sys1 20.4.0", gestaltSystemVersionMajor, 0, 20, 1);
  check("sys2 20.4.0", gestaltSystemVersionMinor, 0, 4, 1);
  check("sys3 20.4.0", gestaltSystemVersionPatch, 0, 0, 1);
  mock_release = "19.6.3";
  check("sysv 19.6.3", gestaltSystemVersion, 0, 0x1360, 1);
  check("sys1 19.6.3", gestaltSystemVersionMajor, 0, 19, 1);
  check("sys2 19.6.3", gestaltSystemVersionMinor, 0, 6, 1);
  check("sys3 19.6.3", gestaltSystemVersionPatch, 0, 3, 1);
  check("architecture unchanged", gestaltSysArchitecture, 0, gestaltIntel, 0);
  check("unknown selector", 0x7a7a7a7au, -4, 0, 0);
  check("Carbon unimplemented", 0x63626f6eu, -4, 0, 0);
  sysctl_mode = 1;
  check("sysctl failure", gestaltSystemVersion, -4, 0, 1);
  sysctl_mode = 2;
  check("empty kernel release", gestaltSystemVersionMajor, -4, 0, 1);
  sysctl_mode = 3;
  check("invalid reported size", gestaltSystemVersionMinor, -4, 0, 1);
  sysctl_mode = 0;
  mock_release = "20.invalid.0";
  check("malformed kernel release", gestaltSystemVersionPatch, -4, 0, 1);
  mock_release = "20.-1.0";
  check("negative kernel release part", gestaltSystemVersion, -4, 0, 1);
  mock_release = "20.4.0";
  sysctl_mode = 5;
  check("unterminated kernel release", gestaltSystemVersion, 0, 0x1440, 1);
  sysctl_mode = 0;
  const int prior_calls = sysctl_calls;
  if (Gestalt(gestaltSystemVersion, nullptr) != -50 || sysctl_calls != prior_calls) {
    std::fprintf(stderr, "FAIL null output parameter\n");
    ++failed;
  } else {
    ++passed;
  }
  std::printf("GESTALT_HOST: %d PASS, %d FAIL\n", passed, failed);
  return failed ? 1 : 0;
}
''', encoding='utf8')
        output = root / 'contract'
        build = subprocess.run([cxx, '-std=c++17', '-O0', '-Wall', '-Wextra',
                                '-Werror=implicit-fallthrough', '-Wno-multichar',
                                '-I' + str(root / 'include'), '-I' + str(HEADERS),
                                '-include', str(root / 'include/prelude.h'),
                                str(source), str(root / 'contract.cpp'), '-o', str(output)],
                               text=True, capture_output=True, check=False, timeout=25)
        if build.returncode:
            raise RuntimeError('compile failed:\n' + build.stderr[-1600:])
        result = subprocess.run([str(output)], capture_output=True, text=True,
                                check=False, timeout=5)
        if result.returncode or result.stderr or 'GESTALT_HOST: 18 PASS, 0 FAIL' not in result.stdout:
            raise RuntimeError('host contract failed:\n' + result.stdout + result.stderr)
        print('PASS: exact header blob', HEADER_BLOB)
        print('PASS: Gestalt source blob', blob)
        print(result.stdout.strip())
        print('PASS: host C++ compile and execution, no production edits')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--expected-source-blob')
    parser.add_argument('--compiler', default='c++')
    args = parser.parse_args()
    try:
        return run(args.source, args.compiler, args.expected_source_blob)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as err:
        print('FAIL:', err, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
