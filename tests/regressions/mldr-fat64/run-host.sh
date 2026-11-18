#!/usr/bin/env bash
# Host tests of mldr's universal-binary slice selection (issue #18):
# the upstream test tests/mldr/fat_slice.c (Darling #2069) and the D4rling
# complement fat_slice_cap.c, built for 64-bit and 32-bit hosts and once under
# ASan/UBSan. No network, no install; outputs go to a temporary directory.
set -Eeuo pipefail
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../../.." && pwd)
src=$root/src/startup/mldr; out=$(mktemp -d); trap 'rm -rf "$out"' EXIT
CC=${CC:-cc}; fail=0
run() { local name=$1; shift
  if "$CC" -std=gnu11 -O2 -Wall -Wextra -Werror -I"$src" "$@" "$src/fat_slice.c" -o "$out/$name" 2>"$out/$name.log"; then
    if "$out/$name" >"$out/$name.out"; then echo "PASS $name ($(grep -c '^PASS' "$out/$name.out") checks)"
    else echo "FAIL $name"; grep '^FAIL' "$out/$name.out"; fail=1; fi
  else echo "SKIP $name (cannot build: $(head -1 "$out/$name.log"))"; fi
}
for m in 64 32; do
  run upstream-m$m -m$m "$root/tests/mldr/fat_slice.c"
  run cap-m$m -m$m "$here/fat_slice_cap.c"
done
if "$CC" -fsanitize=address,undefined -x c /dev/null -c -o /dev/null 2>/dev/null; then
  run upstream-asan -g -fsanitize=address,undefined -fno-sanitize-recover=all "$root/tests/mldr/fat_slice.c"
fi
exit $fail
