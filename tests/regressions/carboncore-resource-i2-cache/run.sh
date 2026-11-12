#!/usr/bin/env bash
# D4rling CarbonCore I2-A: Linux host-extracted lookup cache contracts.
# Reads the checkout's Resources.cpp and writes only to temporary directories.
set -Eeuo pipefail
umask 077
ulimit -c 0
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO="$(cd -- "$HERE/../../.." && pwd -P)"
SOURCE="$REPO/src/frameworks/CoreServices/src/CarbonCore/Resources.cpp"
CHECK="$HERE/check_caches.py"
command -v git >/dev/null && command -v python3 >/dev/null
[[ -f "$SOURCE" && -f "$CHECK" ]] || { echo 'BLOCKED: missing production source or regression script' >&2; exit 2; }
# The Python runner pins the Git blob of the extracted production functions.
for CXX in g++ clang++; do
    command -v "$CXX" >/dev/null || { echo "BLOCKED: missing $CXX" >&2; exit 2; }
    for OPT in -O0 -O2; do
        python3 -B "$CHECK" --compiler "$CXX" --opt="$OPT"
    done
    for MUT in no-clear-list no-clear-id no-clear-name wrong-name-cache; do
        python3 -B "$CHECK" --compiler "$CXX" --opt=-O0 --mutation "$MUT" --expect-fail
        printf 'NEGATIVE PASS: %s %s\n' "$CXX" "$MUT"
    done
done
printf 'CARBONCORE_I2_CACHE_HOST: PASS, 21/21 x4, 4/4 mutations per compiler\n'
