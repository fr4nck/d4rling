#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# QT-MOV-02 / R6-CROSS-01. Read source tree; write temporary build only.
set -Eeuo pipefail
umask 077
export LC_ALL=C GIT_OPTIONAL_LOCKS=0 GIT_NO_LAZY_FETCH=1
export GIT_TERMINAL_PROMPT=0 PYTHONDONTWRITEBYTECODE=1
REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
cd "$REPO"
test "$(git rev-parse --show-toplevel)" = "$REPO"
test "$(git branch --show-current)" = master
case "$(git remote get-url origin)" in
  *fr4nck/d4rling*) ;;
  *) echo 'BLOCKED: not canonical fr4nck/d4rling origin' >&2; exit 3 ;;
esac
SRC='src/frameworks/QuickTime/src'
test "$(git hash-object "$SRC/qt_mov_pcm.c")" = cdb35c2f882caaf1954e79baf97191cdd5816eb9
test "$(git hash-object "$SRC/qt_mov_pcm.h")" = 42aa7d3322a83045822567c941be31d0ba6fe952
test "$(git hash-object "$SRC/qt_mov_probe.c")" = 6d1fcd89a7396a120da7b4d456bd708a9bcfdecd
test "$(git hash-object "$SRC/qt_mov_probe.h")" = d04d0a72edc554b9281ee7c1a60120c230c8940e
command -v clang >/dev/null
command -v python3 >/dev/null
command -v llvm-objdump >/dev/null
printf '=== QT-MOV R6 / Darwin i386 Mach-O object-only cross compile ===\n'
printf 'repo=%s\nhead=%s\n' "$REPO" "$(git rev-parse HEAD)"
git status --short
clang --version | head -1
WORK="$(mktemp -d "${TMPDIR:-/tmp}/d4rling-qt-i386-obj.XXXXXXXX")"
trap 'rm -rf -- "$WORK"' EXIT
mkdir -p "$WORK/include"
cat > "$WORK/include/string.h" <<'EOF'
/* Test-only C declarations, NOT a Darwin SDK or production source. */
#ifndef D4RL_QT_TEST_ONLY_STRING_H
#define D4RL_QT_TEST_ONLY_STRING_H
#include <stddef.h>
int memcmp(const void *, const void *, size_t);
void *memcpy(void *, const void *, size_t);
void *memset(void *, int, size_t);
#endif
EOF
RES="$(clang -print-resource-dir)"
test -f "$RES/include/stdint.h"
test -f "$RES/include/stddef.h"
FLAGS=(-ffreestanding -nostdinc -isystem "$RES/include" -I "$WORK/include" -I "$REPO/$SRC" -std=c11 -O1 -Wall -Wextra -Werror -fvisibility=hidden -fno-stack-protector -c)
for NAME in qt_mov_pcm qt_mov_probe; do
  clang -target i386-apple-darwin9 "${FLAGS[@]}" "$SRC/$NAME.c" -o "$WORK/$NAME.i386.macho.o"
done
clang -target i386-linux-gnu "${FLAGS[@]}" "$SRC/qt_mov_pcm.c" -o "$WORK/negative.i386.elf.o"
clang -target x86_64-apple-darwin9 "${FLAGS[@]}" "$SRC/qt_mov_pcm.c" -o "$WORK/negative.x64.macho.o"
python3 -B "$(dirname -- "${BASH_SOURCE[0]}")/verify_i386_macho_objects.py" \
  --pcm "$WORK/qt_mov_pcm.i386.macho.o" \
  --probe "$WORK/qt_mov_probe.i386.macho.o" \
  --elf-negative "$WORK/negative.i386.elf.o" \
  --x64-negative "$WORK/negative.x64.macho.o"
for NAME in qt_mov_pcm qt_mov_probe; do
  llvm-objdump --macho --private-headers "$WORK/$NAME.i386.macho.o" | grep -m1 'MH_MAGIC.*I386.*OBJECT'
  sha256sum "$WORK/$NAME.i386.macho.o"
done
printf 'QT-MOV-R6-CROSS-I386-OBJECT-PASS (not a dylib, guest, or Logic qualification)\n'
