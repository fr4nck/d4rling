#!/usr/bin/env bash
# D4rling CarbonCore I2-B: isolated SetResInfo + real lookup cache excerpts.
# This tests function excerpts, NOT complete CarbonCore linkage or Mach-O i386.
set -Eeuo pipefail
umask 077
ulimit -c 0
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO="$(cd -- "$HERE/../../.." && pwd -P)"
SOURCE="$REPO/src/frameworks/CoreServices/src/CarbonCore/Resources.cpp"
CHECK="$HERE/check_setresinfo.py"
command -v git >/dev/null && command -v python3 >/dev/null
[[ -f "$SOURCE" && -f "$CHECK" ]] || { echo 'BLOCKED: missing Resources.cpp or I2-B tests' >&2; exit 2; }
[[ "$(git hash-object "$SOURCE")" == '3d9add9d7e1ed0125c7f2114857169c32044ba70' ]] || { echo 'BLOCKED: unexpected Resources.cpp; requalify' >&2; exit 2; }
for COMPILER in g++ clang++; do
    command -v "$COMPILER" >/dev/null || { echo "BLOCKED: missing $COMPILER" >&2; exit 2; }
    for OPT in -O0 -O2; do
        python3 -B "$CHECK" --compiler "$COMPILER" --opt="$OPT"
    done
    python3 -B "$CHECK" --compiler "$COMPILER" --opt=-O0 --mutation missing-invalidation --expect-fail
    printf 'NEGATIVE PASS: %s rejects omitted cache invalidation\n' "$COMPILER"
done
printf 'CARBONCORE_I2_SETRESINFO_HOST: PASS, 20/20 x4; 1/1 mutation per compiler\n'
