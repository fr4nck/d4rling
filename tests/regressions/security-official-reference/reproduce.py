#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify/replay S4 using its preserved private stage; never installs or fetches."""
import argparse
import hashlib
import json
from pathlib import Path
import os
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--stage', required=True, type=Path)
parser.add_argument('--run', action='store_true')
args = parser.parse_args()
stage = args.stage.resolve()
assert stage.name == 'security-s4-logic-l1-20261114' and stage.parent.name == 'validation'

def digest(path):
    state = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1048576), b''):
            state.update(chunk)
    return state.hexdigest()

for name, relative in [('s4-frozen-inputs.json', False), ('s4-artifacts-manifest.json', True)]:
    for path, expected in json.loads((stage / name).read_text()).items():
        assert digest(stage / path if relative else Path(path)) == expected, path
module = stage / 'src/src/external/security'
environment = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
assert subprocess.check_output(['git', '-C', str(module), 'rev-parse', 'HEAD'], text=True).strip() == '84c0a3e1d25caa4cd370e850813aa527c31a2d12'
assert not subprocess.check_output(['git', '-C', str(module), 'status', '--porcelain'], text=True, env=environment)
print('S4_FROZEN_INPUTS_AND_ARTIFACTS_PASS', flush=True)
if args.run:
    cases = [
        ('candidate', 'home', 'witness', 'normal', 0, 'HOME_RES_I386_PASS checks=88 failures=0'),
        ('candidate', 'bypass', 'witness', 'bypass', 0, 'HOME_RES_I386_PASS checks=88 failures=0'),
        ('candidate', 'api-i386', 'security-smoke-i386', 'normal', 0, 'SECURITY_SMOKE_PASS failures=0'),
        ('candidate', 'api-x64', 'security-smoke-x86_64', 'normal', 0, 'SECURITY_SMOKE_PASS failures=0'),
        ('candidate', 'carbon', 'carbon', 'normal', 0, 'D4RLING-CARBON-EVENT-I386-OK'),
        ('candidate-no-security', 'no-security', 'symbol-probe', 'normal', 2, 'Reason: image not found'),
        ('candidate-no-helper', 'no-helper', 'symbol-probe', 'normal', 2, 'libcoretls_cfhelpers.dylib'),
    ]
    stamp = 's4-replay-' + str(time.time_ns())
    for variant, name, program, mode, expected, marker in cases:
        label = stamp + '-' + name
        subprocess.run(['bash', str(stage / 'run-deleg.sh'), variant, label, program, mode], check=True)
        run = stage / 'runs' / label
        assert int((run / 'rc').read_text()) == expected, label
        output = (run / 'stdout.log').read_text() + (run / 'stderr.log').read_text()
        assert marker in output, label
        meta = dict(line.split('=', 1) for line in (run / 'meta.txt').read_text().splitlines() if '=' in line)
        assert meta['host_mounts_before'] == meta['host_mounts_after'], label
        assert meta['darlingserver_before'] == meta['darlingserver_after'], label
    print('S4_NATIVE_QUALIFICATION_PASS', flush=True)
