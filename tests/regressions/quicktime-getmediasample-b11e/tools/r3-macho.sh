#!/usr/bin/env bash
# QT-B11E-R3: Mach-O audit of the QuickTime framework built by CMake/Ninja,
# against the reference build of the same QuickTime sources before the change
# (validation/upstream-sync-20261114/build-gui-i386, source 4be2603c, QuickTime
# tree identical to master 0374b553). Read-only on both builds.
set -Eeuo pipefail
export LC_ALL=C
Q=/home/Deniel/d4wrling-work/validation/quicktime-b11e-20261114
OLD=/home/Deniel/d4wrling-work/validation/upstream-sync-20261114/build-gui-i386/src/frameworks/QuickTime/QuickTime
NEW=$Q/build-gui/src/frameworks/QuickTime/QuickTime
INSTQT=$Q/build-gui/private-install/libexec/darling/System/Library/Frameworks/QuickTime.framework/Versions/A/QuickTime
O=$Q/reports/r3-macho; mkdir -p "$O"
sha256sum "$OLD" "$NEW" "$INSTQT" > "$O/SHA256SUMS"
for a in i386 x86_64; do
  for w in OLD NEW; do
    f=${!w}
    llvm-nm-19 -g --defined-only --arch=$a "$f" | awk '{print $NF}' | sort > "$O/exports-$w-$a.txt"
    llvm-nm-19 -u --arch=$a "$f" | awk '{print $NF}' | sort > "$O/undefined-$w-$a.txt"
    llvm-otool-19 -arch $a -L "$f" | tail -n +2 > "$O/load-$w-$a.txt"
  done
  echo "$a exports old=$(wc -l < "$O/exports-OLD-$a.txt") new=$(wc -l < "$O/exports-NEW-$a.txt") diff=$(diff "$O/exports-OLD-$a.txt" "$O/exports-NEW-$a.txt" | grep -c '^[<>]' || true)"
  echo "$a undefined added: $(comm -13 "$O/undefined-OLD-$a.txt" "$O/undefined-NEW-$a.txt" | tr '\n' ' ')"
  echo "$a undefined removed: $(comm -23 "$O/undefined-OLD-$a.txt" "$O/undefined-NEW-$a.txt" | tr '\n' ' ')"
  echo "$a load commands diff:"; diff "$O/load-OLD-$a.txt" "$O/load-NEW-$a.txt" || true
done
llvm-lipo-19 -info "$NEW"
cmp "$NEW" "$INSTQT" && echo "installed QuickTime == build output"
