#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Host-only regression tests compiling the real CarbonCore/Gestalt.cpp and Gestalt.h.

The only substitutions are MacErrors.h and sys/sysctl.h plus an injected
sysctlbyname implementation. No SDK, Darling installation, guest or audio.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'src/frameworks/CoreServices/src/CarbonCore/Gestalt.cpp'
HEADERS = ROOT / 'src/frameworks/CoreServices/include'
HEADER_BLOB = '1d465bdb2fe1511d976f87f2d19769aa98ba1847'


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


HARNESS = r'''#include <CarbonCore/Gestalt.h>
#include <sys/sysctl.h>
#include <climits>
#include <cstdio>
#include <cstring>

static const char* mock_product = "11.7.4";
static int sysctl_calls = 0;
static int sysctl_mode = 0;
extern "C" int sysctlbyname(const char* name, void* dst, size_t* len,
                             const void*, size_t) {
    ++sysctl_calls;
    if (!name || std::strcmp(name, "kern.osproductversion") != 0 || !dst || !len)
        return -1;
    if (sysctl_mode == 1) return -1;
    if (sysctl_mode == 2) { *len = 0; return 0; }
    if (sysctl_mode == 3) { *len = 999; return 0; }
    if (sysctl_mode == 5) {
        const char embedded[] = {'1', '1', '\0', '.', '7', '.', '4', '\0'};
        if (*len < sizeof(embedded)) return -1;
        std::memcpy(dst, embedded, sizeof(embedded));
        *len = sizeof(embedded);
        return 0;
    }
    const size_t required = std::strlen(mock_product) + 1;
    if (*len < required) return -1;
    std::memcpy(dst, mock_product, required);
    if (sysctl_mode == 4) {
        static_cast<char*>(dst)[required - 1] = 'x';
        *len = required;
    } else if (sysctl_mode == 6) {
        *len = 64; // An embedded terminating NUL, then unused bytes.
    } else {
        *len = required;
    }
    return 0;
}

static int passed = 0;
static int failed = 0;
static void check(const char* label, const char* product, uint32_t selector,
                  int error, int expected, int mode = 0, int calls = 1) {
    mock_product = product;
    sysctl_mode = mode;
    int out = 0x5555;
    const int before = sysctl_calls;
    const int rc = Gestalt(selector, &out);
    const int actual_calls = sysctl_calls - before;
    if (rc != error || out != expected || actual_calls != calls) {
        std::fprintf(stderr,
                     "FAIL %s: rc=%d value=%d calls=%d; expected %d %d %d\n",
                     label, rc, out, actual_calls, error, expected, calls);
        ++failed;
    } else {
        ++passed;
    }
}

int main() {
    // Product version, not the Darwin release (20.6.0 in the pinned XNU).
    check("macOS 11.7.4", "11.7.4", gestaltSystemVersion, 0, 0x1174);
    check("major 11", "11.7.4", gestaltSystemVersionMajor, 0, 11);
    check("minor 7", "11.7.4", gestaltSystemVersionMinor, 0, 7);
    check("patch 4", "11.7.4", gestaltSystemVersionPatch, 0, 4);
    check("bugfix alias", "11.7.4", gestaltSystemVersionBugFix, 0, 4);
    check("compatibility 10.16", "10.16", gestaltSystemVersion, 0, 0x1090);
    check("compat major", "10.16", gestaltSystemVersionMajor, 0, 10);
    check("compat minor", "10.16", gestaltSystemVersionMinor, 0, 16);
    check("compat missing patch", "10.16", gestaltSystemVersionPatch, 0, 0);
    check("10.3.15 clamped", "10.3.15", gestaltSystemVersion, 0, 0x1039);
    check("10.3.15 patch", "10.3.15", gestaltSystemVersionPatch, 0, 15);
    check("10.10.5 clamped", "10.10.5", gestaltSystemVersion, 0, 0x1095);
    check("10.10.5 minor", "10.10.5", gestaltSystemVersionMinor, 0, 10);
    check("10.4.0 Apple example", "10.4.0", gestaltSystemVersion, 0, 0x1040);
    check("SoundHack 8.6.0", "8.6.0", gestaltSystemVersion, 0, 0x0860);
    check("8.6.0 major", "8.6.0", gestaltSystemVersionMajor, 0, 8);
    check("8.6.0 minor", "8.6.0", gestaltSystemVersionMinor, 0, 6);
    check("8.6.0 patch", "8.6.0", gestaltSystemVersionPatch, 0, 0);
    check("7.0.1 classic", "7.0.1", gestaltSystemVersion, 0, 0x0701);
    check("one digit major", "1.0.0", gestaltSystemVersion, 0, 0x0100);
    check("two digit major", "99.99.99", gestaltSystemVersion, 0, 0x9999);
    check("separate version count", "99.99.99", gestaltSystemVersionMinor, 0, 99);
    check("no patch format", "10.6", gestaltSystemVersion, 0, 0x1060);
    check("leading zeros", "00010.006.000", gestaltSystemVersion, 0, 0x1060);
    check("three-digit major refused", "100.2.3", gestaltSystemVersion, -5550, 0);
    check("three-digit major separately", "100.2.3", gestaltSystemVersionMajor, 0, 100);
    check("intmax major separately", "2147483647.0.0", gestaltSystemVersionMajor, 0, INT_MAX);
    check("intmax major legacy refusal", "2147483647.0.0", gestaltSystemVersion, -5550, 0);
    check("intmax minor separately", "10.2147483647.0", gestaltSystemVersionMinor, 0, INT_MAX);
    check("intmax minor legacy clamp", "10.2147483647.0", gestaltSystemVersion, 0, 0x1090);
    check("intmax patch separately", "10.0.2147483647", gestaltSystemVersionPatch, 0, INT_MAX);
    check("intmax patch legacy clamp", "10.0.2147483647", gestaltSystemVersion, 0, 0x1009);
    check("architecture no sysctl", "11.7.4", gestaltSysArchitecture, 0, gestaltIntel, 0, 0);
    check("unknown selector historical", "11.7.4", 0x7a7a7a7au, -5551, 0, 0, 0);
    check("Carbon not claimed", "11.7.4", gestaltCarbonVersion, -5551, 0, 0, 0);
    check("sysctl failure", "11.7.4", gestaltSystemVersion, -5550, 0, 1);
    check("sysctl empty buffer", "11.7.4", gestaltSystemVersionMajor, -5550, 0, 2);
    check("sysctl oversized length", "11.7.4", gestaltSystemVersionMinor, -5550, 0, 3);
    check("sysctl unterminated", "11.7.4", gestaltSystemVersion, -5550, 0, 4);
    check("sysctl embedded NUL", "11.7.4", gestaltSystemVersion, -5550, 0, 5);
    check("sysctl trailing unused bytes", "11.7.4", gestaltSystemVersion, -5550, 0, 6);
    check("bad minor", "20.invalid.0", gestaltSystemVersionPatch, -5550, 0);
    check("negative minor", "20.-1.0", gestaltSystemVersion, -5550, 0);
    check("suffix rejected", "10.4.0-extra", gestaltSystemVersion, -5550, 0);
    check("fourth component", "10.4.0.1", gestaltSystemVersion, -5550, 0);
    check("trailing space", "10.4.0 ", gestaltSystemVersion, -5550, 0);
    check("leading space", " 10.4.0", gestaltSystemVersion, -5550, 0);
    check("leading plus", "+10.4.0", gestaltSystemVersion, -5550, 0);
    check("minor plus", "10.+4.0", gestaltSystemVersion, -5550, 0);
    check("negative patch", "10.4.-2", gestaltSystemVersion, -5550, 0);
    check("empty patch", "10.4.", gestaltSystemVersion, -5550, 0);
    check("missing minor", "10.", gestaltSystemVersion, -5550, 0);
    check("missing dot", "10", gestaltSystemVersion, -5550, 0);
    check("empty product", "", gestaltSystemVersion, -5550, 0);
    check("newline suffix", "10.4.0\n", gestaltSystemVersion, -5550, 0);
    check("hex prefix", "0x10.4.0", gestaltSystemVersion, -5550, 0);
    check("zero major", "0.0.0", gestaltSystemVersion, -5550, 0);
    check("missing major", ".4.0", gestaltSystemVersion, -5550, 0);
    check("major overflow", "2147483648.4.0", gestaltSystemVersionMajor, -5550, 0);
    check("minor overflow", "10.2147483648.0", gestaltSystemVersionMinor, -5550, 0);
    check("patch overflow", "10.4.2147483648", gestaltSystemVersionPatch, -5550, 0);
    const int before = sysctl_calls;
    if (Gestalt(gestaltSystemVersion, nullptr) == -50 && sysctl_calls == before)
        ++passed;
    else { ++failed; std::fprintf(stderr, "FAIL null output parameter\n"); }
    std::printf("GESTALT_HOST: %d PASS, %d FAIL\n", passed, failed);
    return failed ? 1 : 0;
}
'''


def run(source: Path, compiler: str, expected_blob: str | None) -> int:
    if not source.is_file() or not (HEADERS / 'CarbonCore/Gestalt.h').is_file():
        raise RuntimeError('Gestalt production source/header missing')
    raw = source.read_bytes()
    if len(raw) > 64 * 1024:
        raise RuntimeError('Gestalt production source exceeds bound')
    source_blob = git_blob(raw)
    if expected_blob and source_blob != expected_blob:
        raise RuntimeError(f'Gestalt source blob mismatch: {source_blob} != {expected_blob}')
    if git_blob((HEADERS / 'CarbonCore/Gestalt.h').read_bytes()) != HEADER_BLOB:
        raise RuntimeError('real Gestalt.h changed: requalify regression harness')
    cxx = shutil.which(compiler)
    if not cxx:
        raise RuntimeError(f'compiler unavailable: {compiler}')

    with tempfile.TemporaryDirectory(prefix='d4-carbon-gestalt-g4-') as temp:
        folder = Path(temp)
        (folder / 'include/CarbonCore').mkdir(parents=True)
        (folder / 'include/sys').mkdir()
        (folder / 'include/CarbonCore/MacErrors.h').write_text(
            '#pragma once\nconstexpr OSStatus paramErr = -50;\n'
            'constexpr OSStatus gestaltUnknownErr = -5550;\n'
            'constexpr OSStatus gestaltUndefSelectorErr = -5551;\n', encoding='utf-8')
        (folder / 'include/sys/sysctl.h').write_text(
            '#pragma once\n#include <cstddef>\n'
            'extern "C" int sysctlbyname(const char*, void*, size_t*, const void*, size_t);\n',
            encoding='utf-8')
        (folder / 'include/prelude.h').write_text(
            '#pragma once\n#include <cstdint>\nusing OSStatus = int;\n', encoding='utf-8')
        harness = folder / 'contract.cpp'
        harness.write_text(HARNESS, encoding='utf-8')
        output = folder / 'contract'
        cmd = [cxx, '-std=c++17', '-O0', '-Wall', '-Wextra',
               '-Werror=implicit-fallthrough', '-Wno-multichar',
               '-I' + str(folder / 'include'), '-I' + str(HEADERS),
               '-include', str(folder / 'include/prelude.h'),
               str(source), str(harness), '-o', str(output)]
        build = subprocess.run(cmd, capture_output=True, text=True, timeout=25, check=False)
        if build.returncode:
            raise RuntimeError('host compile failed:\n' + build.stderr[-2000:])
        result = subprocess.run([str(output)], capture_output=True, text=True,
                                timeout=10, check=False)
        counts = re.search(r'GESTALT_HOST: (\d+) PASS, (\d+) FAIL', result.stdout)
        if result.returncode or result.stderr or not counts or int(counts[2]):
            raise RuntimeError('host contract failed:\n' + result.stdout + result.stderr)
        if int(counts[1]) < 60:
            raise RuntimeError('test count unexpectedly reduced')

        text = raw.decode('utf-8')
        mutants = [
            ("return *cursor == '\\0';", 'return true;', 'FAIL suffix rejected'),
            ('"kern.osproductversion"', '"kern.osrelease"', 'FAIL macOS 11.7.4'),
        ]
        for index, (anchor, replacement, expected_failure) in enumerate(mutants, 1):
            if text.count(anchor) != 1:
                raise RuntimeError(f'mutation {index} anchor missing or ambiguous')
            mutant_src = folder / f'mutant-{index}.cpp'
            mutant_bin = folder / f'mutant-{index}'
            mutant_src.write_text(text.replace(anchor, replacement, 1), encoding='utf-8')
            mutant_cmd = [str(mutant_src) if item == str(source) else
                          str(mutant_bin) if item == str(output) else item for item in cmd]
            mutation_build = subprocess.run(mutant_cmd, capture_output=True, text=True,
                                            timeout=25, check=False)
            if mutation_build.returncode:
                raise RuntimeError(f'negative fixture {index} compile failed:\n' + mutation_build.stderr[-1000:])
            mutation_run = subprocess.run([str(mutant_bin)], capture_output=True,
                                          text=True, timeout=10, check=False)
            if mutation_run.returncode == 0 or expected_failure not in mutation_run.stderr:
                raise RuntimeError(f'mutation {index} survived:\n' + mutation_run.stderr[-1000:])
            print(f'PASS: mutant {index} rejected ({expected_failure})')
        print('PASS: pinned public selector header', HEADER_BLOB)
        print('PASS: production Gestalt.cpp Git blob', source_blob)
        print(result.stdout.strip())
        print('PASS: production TU on host; no guest, no audio, no installed Darling')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--expected-source-blob')
    parser.add_argument('--compiler', default='c++')
    args = parser.parse_args()
    try:
        return run(args.source, args.compiler, args.expected_source_blob)
    except (OSError, RuntimeError, subprocess.TimeoutExpired, UnicodeError) as exc:
        print('FAIL:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
