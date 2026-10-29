#!/usr/bin/env bash
# ============================================================
# MLDR PR #6 - 5700X PINNED REGRESSION (NO NETWORK)
# Machine       : 5700X / Ryzen 7 5700X / 64 Go
# Host OS       : Windows 11 Pro N x64
# Guest OS      : Debian GNU/Linux 13 / WSL2
# Terminal      : Bash / Deniel@5700X:~$
# Users         : Deniel (WSL), Ordi (Windows)
# Repository    : /home/Deniel/d4rling-ui/d4rling-carbon-qualif
# Branch        : ANY (no checkout or branch modification)
# Workdir       : repository root via explicit cd
# Writes        : only a NEW private report directory under /home/Deniel
# Forbidden     : downloads, installs, fetch, pull, checkout, reset,
#                 Ninja, sudo, commit, push, runtime or prefix changes
# Protected     : Carbon/CoreAudio builds, servers, installations, guests
# ============================================================
(
set -Eeuo pipefail
umask 077
ulimit -c 0
export GIT_OPTIONAL_LOCKS=0
REPO=/home/Deniel/d4rling-ui/d4rling-carbon-qualif
SOURCE_SHA=2c05caaae9c13882cbc5d07fd3f3e4ebdee0687c
BASE_SHA=6617ef82b9d8cc68ecafa72d051b4731fffedf5a
PY_SHA=b3bf63fe23a1371e59e0eb9454807d772c1e0abc
RB_SHA=aaa8d9eb015bd082bf24e5440317a15a2ed24802
PROBE_SHA=db1397effea9c7d7b3f967e6949d1b320962151c
TESTDIR=tests/regressions/mldr-socket-bitmap
FALLBACK=/home/Deniel/d4rling-mldr-pr6c-xNfhXAtf/mldr.c

[[ $(id -un) == Deniel ]] || { echo STOP_USER; exit 3; }
. /etc/os-release
[[ "$ID" == debian && "$VERSION_ID" == 13 ]] || { echo STOP_OS; exit 3; }
uname -r | grep -qi microsoft || { echo STOP_NOT_WSL2; exit 3; }
cd "$REPO" || { echo STOP_REPO; exit 3; }
[[ $(git rev-parse --show-toplevel) == "$REPO" ]] || { echo STOP_GIT_ROOT; exit 3; }
for tool in git python3 sha256sum mktemp cmp grep; do
  command -v "$tool" >/dev/null || { echo "BLOCKED_TOOL=$tool"; exit 4; }
done
if command -v clang-19 >/dev/null; then
  export CLANG
  CLANG=$(command -v clang-19)
elif command -v clang >/dev/null; then
  export CLANG
  CLANG=$(command -v clang)
else
  echo BLOCKED_NO_CLANG
  exit 4
fi

REPORT=$(mktemp -d /home/Deniel/d4rling-pr6-qualif-XXXXXXXX)
mkdir -p "$REPORT/runner" "$REPORT/src/src/startup/mldr"
echo "REPORT=$REPORT"
git rev-parse HEAD > "$REPORT/git-head.before"
git status --porcelain=v1 -uall > "$REPORT/git-status.before"
if [[ -f src/startup/mldr/mldr.c ]]; then
  git hash-object --no-filters src/startup/mldr/mldr.c > "$REPORT/mldr.before"
else
  echo ABSENT > "$REPORT/mldr.before"
fi

installation_snapshot() {
  local root=/home/Deniel/d4rling-qt432-438-rRJ1fhT1/installation
  for f in bin/darling bin/darlingserver \
    libexec/darling/usr/libexec/darling/mldr \
    libexec/darling/usr/libexec/darling/mldr32; do
    [[ -f "$root/$f" ]] && sha256sum "$root/$f"
  done
  return 0
}
installation_snapshot > "$REPORT/installation.before"
postflight() {
  local previous=$?
  set +e
  git rev-parse HEAD > "$REPORT/git-head.after"
  git status --porcelain=v1 -uall > "$REPORT/git-status.after"
  if [[ -f src/startup/mldr/mldr.c ]]; then
    git hash-object --no-filters src/startup/mldr/mldr.c > "$REPORT/mldr.after"
  else
    echo ABSENT > "$REPORT/mldr.after"
  fi
  installation_snapshot > "$REPORT/installation.after"
  local changed=0
  for name in git-head git-status mldr installation; do
    cmp -s "$REPORT/$name.before" "$REPORT/$name.after" || {
      echo "POSTFLIGHT_CHANGED=$name"; changed=1;
    }
  done
  [[ "$changed" == 0 ]] && echo 'POSTFLIGHT=UNCHANGED'
  echo 'DARLING_GUEST_RUNTIME=NOT_EXECUTED'
  echo 'RPC_MINUS_111=NOT_TESTED'
  echo "REPORT=$REPORT"
  if [[ "$changed" != 0 ]]; then exit 9; else exit "$previous"; fi
}
trap postflight EXIT

materialize() {
  local sha="$1" dest="$2" fallback="$3"
  if git cat-file -e "$sha^{blob}" 2>/dev/null; then
    git cat-file blob "$sha" > "$dest"
  elif [[ -f "$fallback" && $(git hash-object --no-filters "$fallback") == "$sha" ]]; then
    cp "$fallback" "$dest"
  else
    echo "BLOCKED_MISSING_LOCAL_BLOB=$sha"
    return 4
  fi
  [[ $(git hash-object --no-filters "$dest") == "$sha" ]] || return 5
  echo "VERIFIED_BLOB=$sha"
}
materialize "$SOURCE_SHA" "$REPORT/src/src/startup/mldr/mldr.c" "$FALLBACK"
materialize "$PY_SHA" "$REPORT/runner/run.py" "$REPO/$TESTDIR/run.py"
materialize "$RB_SHA" "$REPORT/runner/run.rb" "$REPO/$TESTDIR/run.rb"
materialize "$PROBE_SHA" "$REPORT/runner/probe.c.in" "$REPO/$TESTDIR/probe.c.in"

python3 "$REPORT/runner/run.py" \
  --source "$REPORT/src/src/startup/mldr/mldr.c" \
  --expect-blob "$SOURCE_SHA" > "$REPORT/patched-python.log" 2>&1 || {
    cat "$REPORT/patched-python.log"
    echo PATCHED_PYTHON=FAIL; exit 6;
  }
grep -Fxq MLDR_PR6_DETERMINISTIC=PASS "$REPORT/patched-python.log" || exit 6
echo PATCHED_PYTHON=PASS

if command -v ruby >/dev/null; then
  ruby "$REPORT/runner/run.rb" "$REPORT/src" > "$REPORT/patched-ruby.log" 2>&1 || {
    cat "$REPORT/patched-ruby.log"
    echo PATCHED_RUBY=FAIL; exit 7;
  }
  grep -Fxq MLDR_PR6_DETERMINISTIC=PASS "$REPORT/patched-ruby.log" || exit 7
  echo PATCHED_RUBY=PASS
else
  echo PATCHED_RUBY=NOT_EXECUTED_NO_INSTALLED_RUBY
fi

if git cat-file -e "$BASE_SHA^{blob}" 2>/dev/null; then
  git cat-file blob "$BASE_SHA" > "$REPORT/baseline.c"
  if python3 "$REPORT/runner/run.py" \
      --source "$REPORT/baseline.c" --expect-blob "$BASE_SHA" \
      > "$REPORT/baseline.log" 2>&1; then
    echo BASELINE=FAIL_UNEXPECTED_SUCCESS; exit 8
  fi
  grep -Fq 'COMPILE=PASS' "$REPORT/baseline.log" &&
    grep -Fq 'socket_bitmap.bit_length == 16' "$REPORT/baseline.log" || {
    echo BASELINE=FAIL_UNEXPECTED_FAILURE_MODE; exit 8;
  }
  echo BASELINE=EXPECTED_FAILURE
else
  echo BASELINE=NOT_EXECUTED_NO_LOCAL_BLOB
fi

echo 'PR6_DETERMINISTIC_HOST_STATUS=PASS'
)
