#!/usr/bin/env bash
# R4-F: isolated current-master mldr32 build; no installation or guest execution.
set -Eeuo pipefail
umask 077
ulimit -c 0
export GIT_TERMINAL_PROMPT=0

if [ "$#" -ne 2 ]; then
  echo "usage: bash reproduction/qualify-mldr32-current.sh SOURCE NEW_BUILD" >&2
  exit 2
fi

SOURCE="$(realpath "$1")"
BUILD="$(realpath -m "$2")"
test -f "$SOURCE/src/startup/mldr/loader.c" || { echo "NO_LOADER_SOURCE" >&2; exit 2; }
test -f "$SOURCE/src/startup/mldr/CMakeLists.txt" || { echo "NO_MLDR_CMAKE" >&2; exit 2; }
test ! -e "$BUILD" && test ! -L "$BUILD" || { echo "REFUSE_EXISTING_BUILD" >&2; exit 2; }
case "$BUILD/" in "$SOURCE/"*) echo "REFUSE_IN_SOURCE_BUILD" >&2; exit 2;; esac
test -d "$(dirname "$BUILD")" || { echo "BUILD_PARENT_MISSING" >&2; exit 2; }

HEAD="$(git -C "$SOURCE" rev-parse HEAD)"
BRANCH="$(git -C "$SOURCE" symbolic-ref --quiet --short HEAD || true)"
test "$BRANCH" = master || { echo "REFUSE_NON_MASTER_BRANCH: $BRANCH" >&2; exit 2; }
test -z "$(git -C "$SOURCE" status --porcelain --untracked-files=no)" || {
  echo "REFUSE_MODIFIED_TRACKED_SOURCE" >&2; exit 2;
}
grep -q 'option(D4RLING_MLDR_I386_MMAP_DIAG.* OFF)' "$SOURCE/src/startup/mldr/CMakeLists.txt" || {
  echo "R4F_OPTION_MISSING" >&2; exit 2;
}
grep -q '#undef MLDR_MMAP_DIAG' "$SOURCE/src/startup/mldr/loader.c" || {
  echo "R4F_TEMPLATE_CLEANUP_MISSING" >&2; exit 2;
}

echo "SOURCE_HEAD=$HEAD"
echo "SOURCE_BRANCH=$BRANCH"
echo "BUILD=$BUILD"
echo "NO_INSTALL=1 NO_GUEST=1"
mkdir "$BUILD"
printf '%s\n' "$HEAD" > "$BUILD/source-head.txt"

cmake -S "$SOURCE" -B "$BUILD" -G Ninja \
  -DCMAKE_C_COMPILER=/usr/bin/clang-19 \
  -DCMAKE_CXX_COMPILER=/usr/bin/clang++-19 \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCOMPONENTS=core \
  -DTARGET_x86_64=ON \
  -DTARGET_i386=ON \
  -DD4RLING_MLDR_I386_MMAP_DIAG=ON \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DCMAKE_INSTALL_PREFIX="$BUILD/private-install" \
  -DDEBIAN_PACKAGING=ON \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 \
  -DCOMPILE_PY2_BYTECODE=OFF \
  -DENABLE_METAL=OFF 2>&1 | tee "$BUILD/configure.log"

python3 - "$BUILD/compile_commands.json" <<'PY'
import json, sys
from pathlib import Path
p=Path(sys.argv[1])
if not p.is_file():
    raise SystemExit("NO_COMPILE_COMMANDS")
commands=json.loads(p.read_text())
rows=[x for x in commands if Path(x["file"]).name=="mldr.c"]
if not rows:
    raise SystemExit("NO_MLDR_COMPILE_COMMAND")
for x in rows:
    cmd=x.get("command") or " ".join(x.get("arguments", []))
    print("MLDR_COMPILE", cmd)
enabled=[x for x in rows if "D4RLING_MLDR_I386_MMAP_DIAG" in
         (x.get("command") or " ".join(x.get("arguments", [])))]
if len(enabled)!=1:
    raise SystemExit(f"EXPECTED_ONE_INSTRUMENTED_MLDR_COMPILE_FOUND_{len(enabled)}")
cmd=enabled[0].get("command") or " ".join(enabled[0].get("arguments", []))
if "-m32" not in cmd:
    raise SystemExit("INSTRUMENTED_MLDR_NOT_32BIT")
if len(rows)>1 and any("D4RLING_MLDR_I386_MMAP_DIAG" in
    (x.get("command") or " ".join(x.get("arguments", [])))
    for x in rows if x is not enabled[0]):
    raise SystemExit("DIAGNOSTIC_LEAKED_TO_OTHER_TARGET")
print("R4F_COMPILE_DEFINITION_SCOPE_PASS")
PY

cmake --build "$BUILD" --target mldr32 --parallel 2 2>&1 | tee "$BUILD/build-mldr32.log"
BIN="$(find "$BUILD" -type f -name mldr32 -perm /111 -print -quit)"
test -n "$BIN" || { echo "NO_MLDR32_BINARY" >&2; exit 1; }
file "$BIN"
file "$BIN" | grep -q 'ELF 32-bit' || { echo "MLDR32_NOT_ELF32" >&2; exit 1; }
echo "R4F_CURRENT_MASTER_MLDR32_BUILD_PASS"
echo "SOURCE_HEAD=$HEAD"
echo "BINARY=$BIN"
