#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reproduce L1's bounded dependency failures; never launches Logic or Apple frameworks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--stage', required=True, type=Path)
parser.add_argument('--run', action='store_true')
parser.add_argument('--rebuild', action='store_true', help='build new authored witnesses in a fresh output directory')
args = parser.parse_args()
stage = args.stage.resolve()
assert stage.name == 'security-s4-logic-l1-20261114' and stage.parent.name == 'validation'

def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1048576), b''):
            result.update(block)
    return result.hexdigest()

for name in ['l1-frozen-inputs.json', 'private/logic-input-sha256.json']:
    for path, expected in json.loads((stage / name).read_text()).items():
        assert digest(path) == expected, path
for name in ['logic-load-probe.c', 'native-freetype-probe.c', 'logic-system-symbols.c']:
    assert (Path(__file__).parent / name).read_bytes() == (stage / name).read_bytes(), name
print('L1_PRIVATE_INPUTS_AND_WITNESSES_VERIFIED', flush=True)

stamp = 'l1-replay-' + str(time.time_ns())
output = stage / stamp
output.mkdir()
(output / 'logs').mkdir()
runner = stage / 'run-deleg.sh'
if args.rebuild:
    (output / 'bin').mkdir()
    programs = ['logic-load-probe', 'native-freetype-i386', 'native-freetype-x86_64', 'logic-system-symbols']
    for program in programs:
        for step in ['compile', 'link']:
            command = json.loads((stage / 'commands' / (program + '-' + step + '.json')).read_text())
            command = [str(output / 'bin' / Path(value).name)
                       if value.startswith(str(stage / 'bin') + '/') else value for value in command]
            for flag in ['-o', '-MF']:
                if flag in command:
                    assert Path(command[command.index(flag) + 1]).is_relative_to(output)
            result = subprocess.run(command, cwd=output, capture_output=True, text=True)
            (output / 'logs' / (program + '-' + step + '.log')).write_text(result.stdout + result.stderr)
            (output / 'logs' / (program + '-' + step + '.json')).write_text(json.dumps(command, indent=2) + '\n')
            assert result.returncode == 0, (program, step, result.stderr[-2000:])
    text = runner.read_text()
    original = 'H="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"'
    assert original in text
    text = text.replace(original, 'H=' + shlex.quote(str(stage)) + '\nREPLAY_BIN=' + shlex.quote(str(output / 'bin')), 1)
    assert 'executable="$H/bin/$program"' in text
    text = text.replace('executable="$H/bin/$program"', 'executable="$REPLAY_BIN/$program"')
    runner = output / 'run-deleg.sh'
    runner.write_text(text)
    print('L1_AUTHORED_WITNESSES_REBUILT', flush=True)

if args.run:
    cases = [
        ('candidate', 'carbon-before', 'logic-load-probe', 20, 'image not found'),
        ('logic-candidate', 'carbon-present', 'logic-load-probe', 134, 'Cannot load libfreetype.so.6 (ELF)'),
        ('logic-candidate', 'freetype-i386', 'native-freetype-i386', 134, 'Cannot load libfreetype.so.6 (ELF)'),
        ('logic-candidate', 'freetype-x64', 'native-freetype-x86_64', 0, 'NATIVE_FREETYPE_LOAD_PASS'),
        ('candidate', 'symbols', 'logic-system-symbols', 0, 'LOGIC_SYMBOL_LOOKUP_COMPLETE checked=689 missing=9'),
    ]
    records = []
    for variant, name, program, expected, marker in cases:
        label = stamp + '-' + name
        result = subprocess.run(['bash', str(runner), variant, label, program, 'normal'], capture_output=True, text=True)
        assert result.returncode == 0, (label, result.stderr[-2000:])
        run = stage / 'runs' / label
        rc = int((run / 'rc').read_text())
        logs = (run / 'stdout.log').read_text() + (run / 'stderr.log').read_text()
        records.append({'label': label, 'program': program, 'expected_returncode': expected,
                        'actual_returncode': rc, 'marker_present': marker in logs,
                        'binary_sha256': digest((output / 'bin' if args.rebuild else stage / 'bin') / program)})
        (output / 'results.json').write_text(json.dumps(records, indent=2) + '\n')
        assert rc == expected and marker in logs, (label, rc, 'environment may have changed')
        meta = dict(line.split('=', 1) for line in (run / 'meta.txt').read_text().splitlines() if '=' in line)
        assert meta['host_mounts_before'] == meta['host_mounts_after'], label
        assert meta['darlingserver_before'] == meta['darlingserver_after'], label
        print('L1_OBSERVATION_REPRODUCED', name, rc, flush=True)
    print('L1_BASELINE_OBSTACLES_REPRODUCED; L2 REMAINS BLOCKED', flush=True)
