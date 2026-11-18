#!/usr/bin/env bash
# ABI25 : AppKit + X11 Cocotron d'une variante de source, avec les commandes exactes du build B13.
# Namespace privé (user+mount) : la source de la variante est montée en lecture seule sur le chemin
# Cocotron de B13, et tout mbuild est remonté en lecture seule ; objets/bibliothèques dans OUT.
# Usage: build_appkit.sh VARIANTE
set -Eeuo pipefail
W=$HOME/d4wrling-work/validation/r5-recovery-20261118
T=$HOME/d4wrling-work/validation/audiotoolbox-b13-20261115; G=$T/mbuild; CO=$T/src/src/external/cocotron
v=$1; SRC=$W/abi25/src-$v; OUT=$W/abi25/build-$v; test -d "$SRC"; test ! -e "$OUT"; mkdir -p "$OUT/obj"
cd "$G"
for t in AppKit X11; do ninja -t commands src/external/cocotron/AppKit/$t > "$OUT/$t.all"; done
dirA=src/external/cocotron/AppKit/CMakeFiles/
rew(){ sed -e "s#$dirA#$OUT/obj/#g" -e "s#-o src/external/cocotron/AppKit/AppKit #-o $OUT/AppKit #g" \
  -e "s#-o src/external/cocotron/AppKit/X11 #-o $OUT/X11 #g" \
  -e "s# src/external/cocotron/AppKit/AppKit # $OUT/AppKit #g" \
  -e "s#$G/src/external/cocotron/AppKit/AppKit\b#$OUT/AppKit#g" -e "s#$G/src/external/cocotron/AppKit/X11\b#$OUT/X11#g"; }
grep -F -- "-o ${dirA}AppKit.dir/" "$OUT/AppKit.all" | rew > "$OUT/compile-AppKit.sh"
grep -F -- "-o ${dirA}X11_backend.dir/" "$OUT/X11.all" | rew > "$OUT/compile-X11.sh"
grep -F -- "-o src/external/cocotron/AppKit/AppKit " "$OUT/AppKit.all" | rew > "$OUT/link-AppKit.sh"
grep -F -- "-o src/external/cocotron/AppKit/X11 " "$OUT/X11.all" | rew > "$OUT/link-X11.sh"
wc -l "$OUT"/compile-*.sh "$OUT"/link-*.sh | sed "s#$OUT/##"
if grep -q -- '-o src/\| src/external/cocotron/AppKit/CMakeFiles' "$OUT"/compile-*.sh "$OUT"/link-*.sh; then echo "SORTIE NON REDIRIGÉE" >&2; exit 3; fi
grep -oh -- "-o $OUT/obj/[^ ]*" "$OUT"/compile-*.sh | sed "s#^-o ##" | xargs -n1 dirname | sort -u | xargs -r mkdir -p
echo "REPERTOIRES_OBJETS $(find "$OUT/obj" -type d | wc -l)"
unshare --user --map-root-user --mount /bin/bash -c '
  set -Eeuo pipefail
  mount --make-rprivate /
  mount --bind "$1" "$2"; mount -o remount,bind,ro "$2"
  mount --bind "$3" "$3"; mount -o remount,bind,ro "$3"
  cd "$3"
  echo "NS_SOURCE_CHECK $(sha256sum "$2/AppKit/include/AppKit/AppKitIvarLayout.h" | cut -c1-16)"
  for t in AppKit X11; do
    tr "\n" "\0" < "$4/compile-$t.sh" | xargs -0 -P 14 -I{} bash -c "{} 2>>$4/compile-$t.err || { echo FAIL >> $4/compile-$t.fail; }"
    test ! -s "$4/compile-$t.fail" || { echo "COMPILE $t ÉCHEC"; exit 4; }
    echo "COMPILE $t OK ($(wc -l < "$4/compile-$t.sh") unités)"
    bash "$4/link-$t.sh" > "$4/link-$t.out" 2> "$4/link-$t.err" || { echo "LINK $t ÉCHEC"; tail -5 "$4/link-$t.err"; exit 5; }
    echo "LINK $t OK $(sha256sum "$4/$t" | cut -c1-16)"
  done
' ns "$SRC" "$CO" "$G" "$OUT"
