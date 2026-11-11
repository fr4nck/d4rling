#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Kill R2 contract regressions using isolated modified source files."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'src/frameworks/CoreServices/src/CarbonCore/ResourcesImpl.cpp'
RUNNER = Path(__file__).with_name('run.sh')
MUTANTS = (
    ('file attributes silently discarded',
     'store16(map, 22, static_cast<uint16_t>(m_attributes));',
     'store16(map, 22, 0);'),
    ('resource id shifted on save',
     'store16(map, refPos, static_cast<uint16_t>(entry.resource->id));',
     'store16(map, refPos, static_cast<uint16_t>(entry.resource->id + 1));'),
    ('wrong map copy of header',
     'std::copy(bytes.begin(), bytes.begin() + 16, map.begin());',
     'std::copy(bytes.begin(), bytes.begin() + 8, map.begin());'),
    ('discard disk partial write',
     'if (count > 0)\n            std::memcpy(bytes.data() + offset, buffer, static_cast<size_t>(count));',
     'if (count > 0)\n            std::memcpy(bytes.data() + offset, buffer, static_cast<size_t>(0));'),
    ('no detection of extended attributes',
     'if (attributes > 0) return wPrErr;',
     'if (attributes > 0) return noErr;'),
)

def main() -> None:
    compiler = sys.argv[1] if len(sys.argv) > 1 else 'g++'
    original = SOURCE.read_text(encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='d4-carbon-r2-mutants-') as folder:
        completed=0
        for i,(label,needle,replacement) in enumerate(MUTANTS,1):
            only = int(os.environ.get("D4_R2_MUTATION_ONLY", "0"))
            if only and i != only: continue
            if original.count(needle) != 1:
                raise RuntimeError(f'Mutant {i}: anchor missing or repeated: {label}')
            source = Path(folder) / f'mutant-{i}.cpp'
            source.write_text(original.replace(needle,replacement,1),encoding='utf-8')
            env = dict(os.environ, D4_R2_TEST_SOURCE=str(source))
            proc = subprocess.run(['bash',str(RUNNER),compiler],env=env,
                                  text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                  timeout=90,check=False)
            # The mutant must be compiled successfully and killed by a
            # contract assertion, not by a sanitizer failure or compiler error.
            if proc.returncode != 1 or 'FAIL line ' not in proc.stderr:
                raise RuntimeError(f'Mutant {i} did not fail assertions: {label}; '
                                   f'rc={proc.returncode}\n{proc.stdout[-700:]}\n{proc.stderr[-800:]}')
            completed+=1
            print(f'R2_MUTANT_{i}: KILLED ({label})', flush=True)
    print(f'R2_MUTANTS: {completed}/{len(MUTANTS)} killed by {compiler}')

if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print('BLOCKED:', error, file=sys.stderr)
        sys.exit(2)
