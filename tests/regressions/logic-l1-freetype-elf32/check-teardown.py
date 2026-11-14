#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Observe teardown of this run's PID namespace only; never signal a process."""
import json
from pathlib import Path
import sys
import time
out = Path(sys.argv[1])
namespace = (out / 'pid-namespace').read_text().strip()
assert namespace.startswith('pid:[')
remaining = []
for attempt in range(151):
    remaining = []
    for p in Path('/proc').glob('[0-9]*/ns/pid'):
        try:
            if str(p.readlink()) == namespace:
                remaining.append(p.parent.parent.name)
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    if not remaining:
        break
    time.sleep(.02)
(out / 'process-teardown.json').write_text(json.dumps({'namespace': namespace,
    'remaining_pids': remaining, 'polls': attempt + 1, 'status': 'PASS' if not remaining else 'FAIL'}, indent=2) + '\n')
assert not remaining, remaining
