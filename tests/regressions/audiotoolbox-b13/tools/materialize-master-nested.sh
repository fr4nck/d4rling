#!/usr/bin/env bash
# B13-INT: the 11 nested submodules, offline, from the B11E module store (same method as
# quicktime-b11e-20261114/tools/materialize-submodules.sh). Writes only the B13 worktree modules.
set -Eeuo pipefail
CANON=$HOME/d4wrling-work/L1-CANON-20261108T2019Z/source
T=$HOME/d4wrling-work/validation/audiotoolbox-b13-20261115
WT=$T/src; LOG=$T/reports/submodules-master
SRCMOD=$CANON/.git/worktrees/src4/modules
Q=$HOME/d4wrling-work/validation/quicktime-b11e-20261114/src
export GIT_TERMINAL_PROMPT=0 GIT_ALLOW_PROTOCOL=file
cd -- "$WT"
git -C "$Q" submodule status --recursive | awk '{print $2}' \
	| grep -v -x -F -f <(git -C "$Q" submodule status | awk '{print $2}') | while read -r nested; do
	parent=$(git submodule status | awk '{print $2}' | while read -r p; do case "$nested" in "$p"/*) echo "$p";; esac; done | head -1)
	rel=${nested#"$parent"/}
	pname=$(git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk -v p="$parent" '$2==p{sub(/^submodule\./,"",$1); sub(/\.path$/,"",$1); print $1}')
	nname=$(git -C "$parent" config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk -v p="$rel" '$2==p{sub(/^submodule\./,"",$1); sub(/\.path$/,"",$1); print $1}')
	ref="$SRCMOD/$pname/modules/$nname"
	set +e
	git -C "$parent" -c protocol.file.allow=always -c "submodule.$nname.url=$ref" \
		submodule update --init --reference "$ref" -- "$rel" >"$LOG/nested_${nested//\//_}.log" 2>&1
	echo "nested rc=$? $nested $(git -C "$nested" rev-parse HEAD 2>/dev/null)"
	set -e
done
