#!/usr/bin/env bash
# D4rling SH14: reuse an existing 10400 cctools-port linker and pinned SH10 ZIP.
# No downloads, installation, cleanup, framework changes or destructive Git operations.
# Writes only one new output folder inside the 10400 project after preflight.
set -Eeuo pipefail
umask 077
export LC_ALL=C GIT_OPTIONAL_LOCKS=0 GIT_NO_LAZY_FETCH=1 GIT_TERMINAL_PROMPT=0 PYTHONDONTWRITEBYTECODE=1

ROOT="${D4RLING_10400_ROOT:-$HOME/atelier/d4rling-10400}"
REPO="${D4RLING_REPO:-$HOME/atelier/d4rling}"
BUILD="${D4RLING_BUILD_ROOT:-$ROOT/build-core-i386}"
PIN='d9456c221e1f462e17c0b3297748bc089d5a861e'
SH13='41893aae4bedfe4de0eb25a316ef535561891e79'
fail() { printf 'SH14 INCONCLUSIVE: %s\n' "$*" >&2; exit 3; }

[[ ( -d "$REPO/.git" || -f "$REPO/.git" ) && -f "$REPO/reproduction/fixtures/soundhack-i386/sh12_cctools_replay.py" ]] || fail "canonical checkout missing: $REPO"
[[ "$(git -C "$REPO" rev-parse --abbrev-ref HEAD)" == master ]] || fail 'checkout must be on master'
GIT_HEAD="$(git -C "$REPO" rev-parse HEAD)"
git -C "$REPO" merge-base --is-ancestor "$SH13" "$GIT_HEAD" || fail "SH13 missing on current checkout; update safely before retrying"
[[ -f "$BUILD/CMakeCache.txt" ]] || fail "configured build not found: $BUILD"
SOURCE="$(sed -n 's/^CMAKE_HOME_DIRECTORY:INTERNAL=//p' "$BUILD/CMakeCache.txt")"
[[ -n "$SOURCE" && "$SOURCE" == "$ROOT"/* && -f "$SOURCE/D4RLING-REPRODUCTION.json" ]] || fail 'build is not from the expected isolated historical source'
[[ -d "$SOURCE/src/external/cctools-port/.git" || -f "$SOURCE/src/external/cctools-port/.git" ]] || fail 'cctools-port submodule absent'
ACTUAL="$(git -C "$SOURCE/src/external/cctools-port" rev-parse HEAD)"
[[ "$ACTUAL" == "$PIN" ]] || fail "cctools-port submodule SHA mismatch: $ACTUAL"
command -v python3 >/dev/null || fail 'python3 missing'
command -v llvm-ar >/dev/null || fail 'llvm-ar missing'
command -v clang >/dev/null || fail 'clang missing'

printf 'SH14 PREFLIGHT\nrepo_HEAD=%s\nbuild=%s\nsource=%s\nsubmodule=%s\n' "$GIT_HEAD" "$BUILD" "$SOURCE" "$ACTUAL"
python3 - "$REPO" "$BUILD" <<'PY'
import json
import sys
from pathlib import Path
root = Path(sys.argv[1]) / 'reproduction/fixtures/soundhack-i386'
sys.path.insert(0, str(root))
from sh12_cctools_replay import find_linkers
candidates = find_linkers(Path(sys.argv[2]))
print(json.dumps({'ld64_candidates': candidates}, sort_keys=True))
if len(candidates) != 1:
    print('SH14 LINKER_ABSENT_OR_AMBIGUOUS: no unique native cctools ld64', file=sys.stderr)
    sys.exit(3)
PY

candidates=()
if [[ -n "${SH10_PACKAGE:-}" ]]; then
    candidates+=("$SH10_PACKAGE")
else
    SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
    for name in "$SCRIPT_DIR/d4rling-SH10-archive-i386.zip" "$ROOT/d4rling-SH10-archive-i386.zip" "$ROOT/validation/d4rling-SH10-archive-i386.zip" "$HOME/Downloads/d4rling-SH10-archive-i386.zip"; do
        [[ -f "$name" && ! -L "$name" ]] && candidates+=("$name")
    done
fi
[[ "${#candidates[@]}" == 1 ]] || fail 'supply one authentic SH10 ZIP via SH10_PACKAGE=/absolute/file.zip (none or several candidates)'
ZIP="${candidates[0]}"
[[ -f "$ZIP" && ! -L "$ZIP" ]] || fail "package missing or symlink: $ZIP"
EXPECTED_PACKAGE_SHA='2fb5c48ecc0ab879a2f60285574f275dd320bc076a1d3ad587a9584adc2d542b'
ACTUAL_PACKAGE_SHA="$(sha256sum "$ZIP" | cut -d' ' -f1)"
[[ "$ACTUAL_PACKAGE_SHA" == "$EXPECTED_PACKAGE_SHA" ]] || fail "SH10 ZIP SHA-256 mismatch: $ACTUAL_PACKAGE_SHA"
OUTDIR="$ROOT/validation/soundhack-sh14"
OUTPUT="$OUTDIR/libSoundHackFFT_i386.dylib"
[[ ! -e "$OUTPUT" && ! -L "$OUTPUT" ]] || fail "existing output protected: $OUTPUT"
mkdir -p -- "$OUTDIR"
printf 'SH14 LINK ATTEMPT using package=%s\n' "$ZIP"
if python3 "$REPO/reproduction/fixtures/soundhack-i386/sh12_cctools_replay.py" \
    --sh10-package "$ZIP" --build-root "$BUILD" --linked-output "$OUTPUT"; then
    printf 'SH14 LINK_STRUCTURE_PASS: saved candidate %s (guest/audio remain untested)\n' "$OUTPUT"
else
    status=$?
    printf 'SH14 LINK_NOT_QUALIFIED: exit=%s; see JSON above\n' "$status" >&2
    exit "$status"
fi
