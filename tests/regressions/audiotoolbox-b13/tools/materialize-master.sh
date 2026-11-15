#!/usr/bin/env bash
# B13-INT: materialise the 151 top-level submodules of the B13 worktree (master 397e94d4) WITHOUT network.
# Objects: the B11E worktree module store (src4, same gitlinks as master except libcxx), and for
# libcxx 061279eb the LIBCXX-LEGACY-01 private clone. A missing commit fails instead of fetching.
# Nested submodules stay uninitialised, as in the B11E build.
set -Eeuo pipefail
CANON=$HOME/d4wrling-work/L1-CANON-20261108T2019Z/source
T=$HOME/d4wrling-work/validation/audiotoolbox-b13-20261115
WT=$T/src
LOG=$T/reports/submodules-master
SRCMOD=$CANON/.git/worktrees/src4/modules
LIBCXX=$HOME/d4wrling-work/validation/libcxx-legacy-01/libcxx.git
mkdir -p "$LOG"
cd -- "$WT"
test "$(git rev-parse HEAD)" = 397e94d470a837a23f80765748cc6d0af26f31c8
export GIT_TERMINAL_PROMPT=0 GIT_ALLOW_PROTOCOL=file
one() {
	local path="$1" name ref rc
	name=$(git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk -v p="$path" '$2==p{sub(/^submodule\./,"",$1); sub(/\.path$/,"",$1); print $1}')
	ref="$SRCMOD/$name"
	[ "$path" = src/external/libcxx ] && ref="$LIBCXX"
	if [ ! -d "$ref/objects" ]; then echo "99 $path noref"; return; fi
	set +e
	git -c protocol.file.allow=always -c "submodule.$name.url=$ref" \
		submodule update --init --reference "$ref" -- "$path" >"$LOG/${path//\//_}.log" 2>&1
	rc=$?
	set -e
	echo "$rc $path"
}
export -f one
export LOG SRCMOD LIBCXX
git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk '{print $2}' \
	| xargs -P 6 -I{} bash -c 'one "$@"' _ {} | sort > "$LOG/summary.txt"
echo "total: $(wc -l < "$LOG/summary.txt")  failed: $(awk '$1!=0' "$LOG/summary.txt" | wc -l)"
awk '$1!=0' "$LOG/summary.txt"
git submodule status | awk '{c=substr($0,1,1); print (c==" "?"ok":c)}' | sort | uniq -c
git submodule status src/external/libcxx
