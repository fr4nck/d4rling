#!/usr/bin/env bash
# SH15 portable, offline replay of the pinned SoundHack SH10 i386 FFT artifact.
# Uses existing source/build on i5-10400. Never updates a repo or installs tools.
# Copyright (C) 2026 D4rling contributors. GPL-3.0-or-later.
set -Eeuo pipefail
umask 077
export LC_ALL=C GIT_OPTIONAL_LOCKS=0 GIT_NO_LAZY_FETCH=1 GIT_TERMINAL_PROMPT=0 PYTHONDONTWRITEBYTECODE=1

fail() { printf 'SH15 INCONCLUSIVE: %s\n' "$*" >&2; exit 3; }
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || fail 'kit directory unreadable'
ROOT="${D4RLING_10400_ROOT:-$HOME/atelier/d4rling-10400}"
BUILD="${D4RLING_BUILD_ROOT:-$ROOT/build-core-i386}"
PIN='d9456c221e1f462e17c0b3297748bc089d5a861e'
BASE='b7d0cb6a79fe196657deb9711647f8486bcc5e5e'
ZIP_SHA='2fb5c48ecc0ab879a2f60285574f275dd320bc076a1d3ad587a9584adc2d542b'

for tool in git python3 sha256sum clang llvm-ar llvm-objdump; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing already-installed tool: $tool"
done

# Reject bundled script substitutions before doing anything in the user's build.
while read -r name expected; do
    [[ -f "$HERE/$name" && ! -L "$HERE/$name" ]] || fail "missing or symlinked kit module: $name"
    actual="$(git hash-object --no-filters -- "$HERE/$name")" || fail "cannot hash $name"
    [[ "$actual" == "$expected" ]] || fail "module modified: $name ($actual)"
done <<'PINS'
sh12_cctools_replay.py a4961c03b2c449a34e08f2d2736f36a599dfba6a
darwin_archive_gate.py 1c0229ccf6de6870add174a831837427e77a00b4
i386_link_gate.py 746855c0c9013aa0ee701035a2b1b5ffd7f8eac8
macho_audit.py 0ac6e95301ed563bfb12cadabb444fda520f3c09
PINS
ZIP="$HERE/d4rling-SH10-archive-i386.zip"
[[ -f "$ZIP" && ! -L "$ZIP" ]] || fail 'authentic SH10 ZIP missing or symlinked'
[[ "$(sha256sum "$ZIP" | cut -d' ' -f1)" == "$ZIP_SHA" ]] || fail 'SH10 ZIP SHA-256 mismatch'

[[ -d "$ROOT" && ! -L "$ROOT" ]] || fail "historical 10400 root missing or symlinked: $ROOT"
[[ -f "$BUILD/CMakeCache.txt" && ! -L "$BUILD" ]] || fail "CMake build missing or symlinked: $BUILD"

# Confirm this build belongs to the historical isolated source tree and pinned submodule.
SOURCE="$(sed -n 's/^CMAKE_HOME_DIRECTORY:INTERNAL=//p' "$BUILD/CMakeCache.txt")"
[[ -n "$SOURCE" && -d "$SOURCE" && ! -L "$SOURCE" ]] || fail 'CMAKE_HOME_DIRECTORY unavailable'
python3 - "$ROOT" "$BUILD" "$SOURCE" "$BASE" <<'PY' || fail 'historical source/build identity mismatch'
import json,sys
from pathlib import Path
root = Path(sys.argv[1]).resolve(strict=True)
build = Path(sys.argv[2]).resolve(strict=True)
source = Path(sys.argv[3]).resolve(strict=True)
expected = sys.argv[4]
if root not in build.parents or root not in source.parents or source == build:
    raise SystemExit('source/build outside authorized 10400 root')
state = json.loads((source/'D4RLING-REPRODUCTION.json').read_text())
if state.get('base') != expected or not state.get('historical_local_overlay'):
    raise SystemExit('wrong historical reconstruction')
PY
[[ -d "$SOURCE/src/external/cctools-port/.git" || -f "$SOURCE/src/external/cctools-port/.git" ]] || fail 'cctools-port submodule missing'
ACTUAL="$(git -C "$SOURCE/src/external/cctools-port" rev-parse HEAD)" || fail 'submodule identity unavailable'
[[ "$ACTUAL" == "$PIN" ]] || fail "cctools-port revision mismatch: $ACTUAL"

# Import the exact pinned GitHub tool copies from this kit, not an old master checkout.
python3 - "$HERE" "$BUILD" <<'PY' || fail 'no single qualified native cctools linker in 10400 build'
import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from sh12_cctools_replay import find_linkers
candidates = find_linkers(Path(sys.argv[2]))
print(json.dumps({'sh15_linker_candidates':candidates},indent=2,sort_keys=True))
if len(candidates) != 1:
    raise SystemExit(3)
PY

OUTDIR="$ROOT/validation/soundhack-sh15"
OUTPUT="$OUTDIR/libSoundHackFFT_i386.dylib"
[[ ! -L "$ROOT/validation" && ! -L "$OUTDIR" ]] || fail 'output parent symlink refused'
[[ ! -e "$OUTPUT" && ! -L "$OUTPUT" ]] || fail "existing output protected: $OUTPUT"
mkdir -p -- "$OUTDIR" || fail 'cannot create output folder'
printf 'SH15: starting authentic cctools link from pinned SH10 ZIP\n'
if python3 "$HERE/sh12_cctools_replay.py" --sh10-package "$ZIP" \
      --build-root "$BUILD" --linked-output "$OUTPUT"; then
    printf 'SH15 LINK_STRUCTURE_PASS: %s\n' "$OUTPUT"
    sha256sum "$OUTPUT"
else
    status=$?
    printf 'SH15 LINK_NOT_QUALIFIED: exit=%s, no guest/audio claim\n' "$status" >&2
    exit "$status"
fi
