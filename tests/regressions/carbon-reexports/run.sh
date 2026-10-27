#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Source-only Carbon/HIToolbox ABI regression. No submodules or Darling runtime.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
python=${PYTHON:-python3}

"$python" -B "$repo/tests/regressions/carbon-reexports/test_contract.py"
"$python" -B "$repo/tests/regressions/carbon-reexports/check_contract.py" --checkout "$repo"

echo "CARBON_REEXPORT_REGRESSION=PASS"
