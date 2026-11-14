#!/usr/bin/env bash
# QT-B11E: materialise the 151 submodules of the B11E worktree WITHOUT network.
# Source of objects: the X1 worktree module stores (src2, same gitlinks as
# master 0374b553, verified by `git diff a5536c89 HEAD --submodule`).
# Each submodule is cloned from the local module gitdir (file URL override,
# config only for this command); a missing commit fails instead of fetching.
# Writes only the B11E worktree and its .git/worktrees/src4/modules store.
set -Eeuo pipefail
CANON=/home/Deniel/d4wrling-work/L1-CANON-20261108T2019Z/source
WT=/home/Deniel/d4wrling-work/validation/quicktime-b11e-20261114/src
LOG=/home/Deniel/d4wrling-work/validation/quicktime-b11e-20261114/reports/submodules
SRCMOD=$CANON/.git/worktrees/src2/modules
mkdir -p "$LOG"
cd -- "$WT"
test "$(git rev-parse --show-toplevel)" = "$WT"
export GIT_TERMINAL_PROMPT=0 GIT_ALLOW_PROTOCOL=file
one() {
	local path="$1" name ref rc
	name=$(git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk -v p="$path" '$2==p{sub(/^submodule\./,"",$1); sub(/\.path$/,"",$1); print $1}')
	ref="$SRCMOD/$name"
	if [ ! -d "$ref/objects" ]; then echo "99 $path noref"; return; fi
	set +e
	git -c protocol.file.allow=always -c "submodule.$name.url=$ref" \
		submodule update --init --reference "$ref" -- "$path" >"$LOG/${path//\//_}.log" 2>&1
	rc=$?
	set -e
	echo "$rc $path"
}
export -f one
export LOG SRCMOD
git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk '{print $2}' \
	| xargs -P 6 -I{} bash -c 'one "$@"' _ {} | sort > "$LOG/summary.txt"
echo "total: $(wc -l < "$LOG/summary.txt")  failed: $(awk '$1!=0' "$LOG/summary.txt" | wc -l)"
awk '$1!=0' "$LOG/summary.txt"
git submodule status | awk '{c=substr($0,1,1); print (c==" "?"ok":c)}' | sort | uniq -c
# Nested submodules (11 in src2): same offline method, from the parent's module store.
X1=/home/Deniel/d4wrling-work/validation/xnu-e72d43f-integration-20261114/src
git -C "$X1" submodule status --recursive | awk '{print $2}' \
	| grep -v -x -F -f <(git submodule status | awk '{print $2}') | while read -r nested; do
	parent=$(git submodule status | awk '{print $2}' | while read -r p; do case "$nested" in "$p"/*) echo "$p";; esac; done | head -1)
	rel=${nested#"$parent"/}
	pname=$(git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk -v p="$parent" '$2==p{sub(/^submodule\./,"",$1); sub(/\.path$/,"",$1); print $1}')
	nname=$(git -C "$parent" config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk -v p="$rel" '$2==p{sub(/^submodule\./,"",$1); sub(/\.path$/,"",$1); print $1}')
	ref="$SRCMOD/$pname/modules/$nname"
	set +e
	git -C "$parent" -c protocol.file.allow=always -c "submodule.$nname.url=$ref" \
		submodule update --init --reference "$ref" -- "$rel" >"$LOG/nested_${nested//\//_}.log" 2>&1
	echo "nested rc=$? $nested"
	set -e
done
git submodule status --recursive | awk '{c=substr($0,1,1); print (c==" "?"ok":c)}' | sort | uniq -c
