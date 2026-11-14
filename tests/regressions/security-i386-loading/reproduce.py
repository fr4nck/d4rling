#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify or replay the preserved 5700X Security loading qualification.

Requires the private stage and the qualified upstream-sync build already present.
Does not install, fetch, delete, or alter a historical prefix or canonical tree.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--stage', required=True, type=Path)
parser.add_argument('--run', action='store_true', help='run native cases in new private prefixes')
parser.add_argument('--rebuild-links', action='store_true', help='replay final links/signing and smoke builds first')
args = parser.parse_args()
stage = args.stage.resolve()
assert stage.name == 'security-i386-20261114'
assert stage.parent.name == 'validation'

def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()

for name, relative in [('protected-before.json', False),
                       ('frozen-build-inputs.json', False),
                       ('artifacts-manifest.json', True)]:
    for path, expected in json.loads((stage / name).read_text()).items():
        actual = stage / path if relative else Path(path)
        assert digest(actual) == expected, str(actual)
security = stage / 'src/src/external/security'
head = subprocess.check_output(['git', '-C', str(security), 'rev-parse', 'HEAD'], text=True).strip()
assert head == 'a536cfff5b857b214d939415cf6040e347fcf785'
assert not subprocess.check_output(['git', '-C', str(security), 'status', '--porcelain'], text=True)
print('FROZEN_INPUTS_AND_ARTIFACTS_PASS', flush=True)

if args.rebuild_links:
    names = ['Security_i386-path-alias', 'Security_x86_64-path-alias', 'coretls-final',
             'Security_i386-adhoc-sign', 'Security_x86_64-adhoc-sign', 'coretls-final-adhoc-sign',
             'Security-final-fat', 'security-smoke-i386-compile', 'security-smoke-i386-link',
             'security-smoke-x86_64-compile', 'security-smoke-x86_64-link']
    build = stage.parent / 'upstream-sync-20261114/build-gui-i386'
    for name in names:
        command = json.loads((stage / 'commands' / (name + '.json')).read_text())
        for flag in ('-o', '-MF', '-output'):
            if flag in command:
                assert Path(command[command.index(flag) + 1]).is_relative_to(stage)
        subprocess.run(command, cwd=build, check=True)
    root = stage / 'runtime/libexec/darling'
    shutil.copy2(stage / 'artifacts/Security-final', root / 'System/Library/Frameworks/Security.framework/Versions/A/Security')
    shutil.copy2(stage / 'artifacts/libcoretls_cfhelpers.dylib', root / 'usr/lib/libcoretls_cfhelpers.dylib')
    print('FINAL_LINKS_AND_SIGNING_PASS', flush=True)

if args.run:
    cases = [
        ('candidate', 'home', 'witness', 'normal', 0, 'HOME_RES_I386_PASS checks=88 failures=0'),
        ('candidate', 'bypass', 'witness', 'bypass', 0, 'HOME_RES_I386_PASS checks=88 failures=0'),
        ('candidate', 'carbon', 'carbon', 'normal', 0, 'D4RLING-CARBON-EVENT-I386-OK'),
        ('candidate', 'api-i386', 'security-smoke-i386', 'normal', 0, 'SECURITY_SMOKE_PASS failures=0'),
        ('candidate', 'api-x64', 'security-smoke-x86_64', 'normal', 0, 'SECURITY_SMOKE_PASS failures=0'),
        ('candidate', 'load', 'symbol-probe', 'normal', 0, 'HOME_RES_SYMBOL_PRESENT=1'),
        ('candidate-no-security', 'no-security', 'symbol-probe', 'normal', 2, 'Reason: image not found'),
        ('candidate-no-helper', 'no-helper', 'symbol-probe', 'normal', 2, 'libcoretls_cfhelpers.dylib'),
        ('candidate-pruned-no-security', 'stripped', 'witness', 'normal', 0, 'HOME_RES_I386_PASS checks=88 failures=0'),
    ]
    tag = 'replay-' + str(time.time_ns())
    for variant, name, program, mode, expected, marker in cases:
        label = tag + '-' + name
        subprocess.run(['bash', str(stage / 'run-deleg.sh'), variant, label, program, mode], check=True)
        result = stage / 'runs' / label
        assert int((result / 'rc').read_text()) == expected, label
        log = (result / 'stdout.log').read_text() + (result / 'stderr.log').read_text()
        assert marker in log, label
        meta = dict(line.split('=', 1) for line in (result / 'meta.txt').read_text().splitlines() if '=' in line)
        assert meta['host_mounts_before'] == meta['host_mounts_after'], label
        assert meta['darlingserver_before'] == meta['darlingserver_after'] == '0', label
    print('NATIVE_LOADING_QUALIFICATION_PASS', flush=True)
