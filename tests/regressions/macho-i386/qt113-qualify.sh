#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# QT-113: reproducible i386 qualification on the 5700X.
# No source checkout changes, installation, or real Ninja builds.
set -uo pipefail
umask 077

if [[ ${1:-} == --help ]]; then
    echo "Usage: bash qt113-qualify.sh (or QT113_GUEST=0 bash qt113-qualify.sh)"
    echo "Downloads nine pinned tools from fr4nck/d4rling, verifies Git blobs,"
    echo "runs 54 host checks, scans i386 providers and inspects Ninja dry runs."
    echo "Default optional guest smoke test uses the qualified QT-108R process guard."
    exit 0
fi

CORE="$HOME/d4rling-core"
BUILD="$CORE/d4rling-build-i386"
EXP="/opt/d4rling-qt-i386"
ROOT="$EXP/libexec/darling"
PFX="$HOME/d4rling-prefix-qt101-20261027-054510-78489"
ORIG="$HOME/d4rling-prefix-runtime-01"
GUARD="$HOME/d4rling-qt108r-Kge0MnWY/guard.py"
QT110="$HOME/d4rling-qt110-O3YBfvHf"
PIN="0d954680fe45dcb41dfe6f9cc62b15fb7cc54769"
GUEST_REQUESTED="${QT113_GUEST:-1}"

if [[ "$GUEST_REQUESTED" != 0 && "$GUEST_REQUESTED" != 1 ]]; then
    echo "STOP: QT113_GUEST must be 0 or 1" >&2; exit 2
fi
for cmd in python3 git ninja timeout; do
    command -v "$cmd" >/dev/null 2>&1 || {
        echo "STOP: missing $cmd" >&2; exit 2;
    }
done
[[ -d "$CORE" && -f "$BUILD/build.ninja" ]] || {
    echo "STOP: core checkout or Ninja tree unavailable" >&2; exit 2;
}

REPORT="$(mktemp -d "$HOME/d4rling-qt113-XXXXXXXX")" || exit 2
TOOLS="$REPORT/tools"
mkdir -m 700 "$TOOLS" || exit 2
HOST=SKIP; SOURCE=SKIP; SYMBOLS=SKIP; GUEST=SKIP
GUEST_EXIT=NA; CLEAN=NOT_NEEDED; ORIGINAL=UNKNOWN; GIT_STATE=UNKNOWN
ORIG_PID=''; ORIG_START=''; EXP_STARTED=0

cleanup_on_exit() {
    if [[ "$EXP_STARTED" == 1 && -f "$GUARD" ]]; then
        python3 -B "$GUARD" cleanup "$EXP" "$PFX" || true
    fi
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "=== D4RLING QT-113 : 5700X I386 QUALIFICATION ==="
echo "REPORT=$REPORT"
echo "PIN=$PIN"
echo "GUEST_REQUESTED=$GUEST_REQUESTED"

git -C "$CORE" status --porcelain=v1 -uno > "$REPORT/git-before.txt" 2>/dev/null || true
ORIG_PID="$(ps -eo pid=,comm=,args= -ww 2>/dev/null |
    awk -v p="$ORIG" '$2=="darlingserver" && $3=="darlingserver" && $4==p {print $1}' |
    head -n 1)"
if [[ -n "$ORIG_PID" ]]; then
    ORIG_START="$(ps -p "$ORIG_PID" -o lstart= 2>/dev/null)"
    echo "ORIGINAL_PID=$ORIG_PID"
else
    echo "ORIGINAL_PID=NOT_RUNNING; guest execution will be skipped"
fi

echo "=== 1 : PINNED TOOL DOWNLOAD (EXPLICIT; READ-ONLY CHECKOUT) ==="
if python3 -B - "$PIN" "$TOOLS" >"$REPORT/download.log" 2>&1 <<'PY'
import hashlib
from pathlib import Path
import sys
import urllib.request

pin, output = sys.argv[1:]
expected = {
    'generate.py': '3075e468a7bfeb8f05a3f189b821afeec5c06149',
    'test_generate.py': 'd9a26811074f0374ec4c53dd84dd411137b60c52',
    'symbol_providers.py': 'c758b9be34c6e41bfa37025145dc7d4b594770f8',
    'test_symbol_providers.py': '3e53e2a975a9af2199db512d0d4d0ad7c26de395',
    'source_contract.py': '1a2211e5bfb07471b6e1586604921af3c325958f',
    'test_source_contract.py': '403a8543a058ad2be416f973e33b9406e971dc17',
    'fetch_pinned_sources.py': '5a06e38c1046f9f8c4b6f618ebcb19160b48ed81',
    'test_fetch_pinned_sources.py': '2ea989c6f7de0ac3caf7e420cfed11a41b1be147',
    'run.sh': 'e05c019f9088396564e57ec00a0c686c1fce6d04',
}
base = f"https://raw.githubusercontent.com/fr4nck/d4rling/{pin}/tests/regressions/macho-i386"
for name, desired in expected.items():
    print("DOWNLOAD=" + name, flush=True)
    request = urllib.request.Request(
        base + "/" + name,
        headers={"User-Agent": "d4rling-qt113-pinned-test/1"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        data = response.read(256 * 1024 + 1)
    if len(data) > 256 * 1024:
        raise SystemExit("STOP: oversize " + name)
    actual = hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()
    if actual != desired:
        raise SystemExit("STOP: Git blob mismatch " + name + " " + actual)
    with (Path(output) / name).open("xb") as stream:
        stream.write(data)
    print("VERIFIED=" + name + " " + actual, flush=True)
print("PINNED_FILES=9 PASS", flush=True)
PY
then
    tail -n 10 "$REPORT/download.log"
else
    tail -n 15 "$REPORT/download.log"
    echo "STOP: tools not verified"
    echo "REPORT=$REPORT"
    exit 2
fi

echo "=== 2 : OFFLINE HOST TESTS ==="
if PYTHONDONTWRITEBYTECODE=1 sh "$TOOLS/run.sh" >"$REPORT/host.log" 2>&1 &&
   grep -Fxq 'HOST_TESTS=PASS' "$REPORT/host.log"; then
    HOST=PASS
else
    HOST=FAIL
fi
echo "HOST_TESTS=$HOST"
grep -E '^Ran [0-9]+ tests|^OK$|^FAILED|^FILE_FORMAT=|^HOST_TESTS=' \
    "$REPORT/host.log" | tail -n 14 || true

echo "=== 3 : LOCAL SOURCE CONTRACT (NO BUILD) ==="
if timeout 25s python3 -B "$TOOLS/source_contract.py" \
    --checkout "$CORE" --output "$REPORT/source-contract.json" \
    >"$REPORT/source-contract.log" 2>&1; then
    SOURCE=PASS
    python3 -B - "$REPORT/source-contract.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
print("SOURCE_CONTRACT_CHECKS=" + str(len(data["checks"])))
for name, passed in sorted(data["checks"].items()):
    print("CHECK_" + name + "=" + ("PASS" if passed else "FAIL"))
PY
else
    SOURCE=FAIL_OR_MISSING_SUBMODULE
    tail -n 12 "$REPORT/source-contract.log"
fi
echo "LOCAL_SOURCE_CONTRACT=$SOURCE"

echo "=== 4 : I386 SYMBOL PROVIDERS (NO LINKING) ==="
if [[ -f "$QT110/link-1.log" && -d "$BUILD/src" ]]; then
    scan=(--link-log "$QT110/link-1.log" --build-dir "$BUILD"
          --max-candidates 120 --timeout 5 --output "$REPORT/providers.json")
    [[ -f "$QT110/link-2.log" ]] && scan+=(--link-log "$QT110/link-2.log")
    if timeout --signal=TERM --kill-after=3s 125s \
        python3 -B "$TOOLS/symbol_providers.py" "${scan[@]}" \
        >"$REPORT/symbol-scan.log" 2>&1; then
        SYMBOLS=PASS
        python3 -B - "$REPORT/providers.json" <<'PY'
import json, sys
report = json.load(open(sys.argv[1], encoding="utf-8"))
missing = report["missing_symbols"]
providers = report["providers"]
found = sum(bool(providers[symbol]) for symbol in missing)
print(f"MISSING_SYMBOLS={len(missing)}")
print(f"WITH_CANDIDATE={found}")
print(f"WITHOUT_CANDIDATE={len(missing)-found}")
print(f"CANDIDATES_SCANNED={report['scan_counts']}")
print(f"TRUNCATED={report['truncated']}")
for symbol in ("__libkernel_functions", "_malloc", "_free"):
    print("PROVIDER_" + symbol + "=" +
          (",".join(providers.get(symbol, [])) or "NOT_FOUND_IN_SCAN"))
PY
    else
        SYMBOLS=FAIL_OR_TIMEOUT
        tail -n 15 "$REPORT/symbol-scan.log"
    fi
else
    SYMBOLS=SKIP_NO_QT110_LOG
fi
echo "SYMBOL_SCAN=$SYMBOLS"

echo "=== 5 : INSTALLED ARCHITECTURES + NINJA DRY RUNS ==="
for lib in "$ROOT/usr/lib/dyld" "$ROOT/usr/lib/libSystem.B.dylib" \
           "$ROOT/usr/lib/system/libsystem_kernel.dylib" \
           "$ROOT/usr/lib/system/libsystem_c.dylib" \
           "$ROOT/usr/lib/system/libsystem_malloc.dylib"; do
    if [[ -f "$lib" ]]; then
        echo "INSTALLED=$lib"
        if command -v llvm-lipo-19 >/dev/null 2>&1; then
            llvm-lipo-19 -archs "$lib" 2>/dev/null || file "$lib"
        else
            file "$lib"
        fi
    else
        echo "NOT_INSTALLED=$lib"
    fi
done
grep -E '^(COMPONENTS|TARGET_i386|TARGET_x86_64):' \
    "$BUILD/CMakeCache.txt" || true
for target in system_kernel_static32 system_kernel system_malloc \
              libsystem_c.dylib libSystem.B.dylib; do
    log="$REPORT/ninja-$(printf '%s' "$target" | tr '/.' '--').log"
    if timeout 35s ninja -C "$BUILD" -n "$target" >"$log" 2>&1; then
        count="$(awk '/^\[[0-9]+\/[0-9]+\]/{n=$0}
            END{if(n ~ /^\[[0-9]+\/[0-9]+\]/){
              sub(/^\[/,"",n);sub(/\].*/,"",n);split(n,a,"/");print a[2]
            }else print 0}' "$log")"
        echo "NINJA_PLAN_$target=AVAILABLE ACTIONS=$count"
    else
        echo "NINJA_PLAN_$target=UNAVAILABLE_OR_TIMEOUT"
        tail -n 3 "$log"
    fi
done

echo "=== 6 : OPTIONAL NEW I386 MACH-O EXECUTION ==="
if [[ "$GUEST_REQUESTED" != 1 ]]; then
    GUEST=SKIP_REQUESTED
elif [[ -z "$ORIG_PID" || -z "$ORIG_START" ]]; then
    GUEST=SKIP_ORIGINAL_NOT_RUNNING
elif [[ ! -f "$GUARD" || ! -O "$GUARD" || ! -x "$EXP/bin/darling" ]]; then
    GUEST=SKIP_GUARD_OR_LAUNCHER_ABSENT
elif ! python3 -B "$GUARD" check "$EXP" "$PFX" \
       >"$REPORT/guest-preflight.log" 2>&1; then
    GUEST=SKIP_UNRESOLVED_PROCESS
else
    DIR="$PFX/usr/local/bin"
    SAFE=1
    for p in "$PFX" "$PFX/usr" "$PFX/usr/local" "$DIR"; do
        if [[ -L "$p" || ( -e "$p" && ! -d "$p" ) ||
              ( -d "$p" && ! -O "$p" ) ]]; then
            echo "UNSAFE_PATH=$p"
            SAFE=0
        fi
    done
    if [[ "$SAFE" != 1 ]]; then
        GUEST=SKIP_UNSAFE_STAGING
    else
        mkdir -p "$DIR"
        TARGET="$DIR/qt113-$(basename "$REPORT")-i386"
        if [[ -e "$TARGET" || -L "$TARGET" ]]; then
            GUEST=SKIP_EXISTING_TARGET
        elif ! python3 -B "$TOOLS/generate.py" --output "$TARGET" \
                 >"$REPORT/generate.log" 2>&1; then
            GUEST=FAIL_GENERATION
        else
            echo "STAGED=$TARGET"
            EXP_STARTED=1
            (
                export DPREFIX="$PFX"
                umask 022
                timeout --signal=TERM --kill-after=3s 12s \
                    "$EXP/bin/darling" exec "$TARGET" </dev/null
            ) >"$REPORT/guest-runtime.log" 2>&1
            GUEST_EXIT=$?
            tail -n 25 "$REPORT/guest-runtime.log"
            if [[ "$GUEST_EXIT" == 43 ]] &&
               grep -Fxq 'D4RLING_I386_MACHO_OK' "$REPORT/guest-runtime.log"; then
                GUEST=PASS
            else
                GUEST=FAIL
            fi
            if python3 -B "$GUARD" cleanup "$EXP" "$PFX" \
               >"$REPORT/guest-cleanup.log" 2>&1; then
                CLEAN=PASS
                EXP_STARTED=0
            else
                CLEAN=UNRESOLVED
                echo "STOP: inspect guest-cleanup.log before any additional run"
            fi
        fi
    fi
fi
echo "GUEST_EXEC=$GUEST"
echo "GUEST_EXIT=$GUEST_EXIT"
echo "CLEAN=$CLEAN"

echo "=== 7 : INTEGRITY ==="
if [[ -n "$ORIG_PID" ]] &&
   [[ "$(ps -p "$ORIG_PID" -o lstart= 2>/dev/null)" == "$ORIG_START" ]] &&
   ps -p "$ORIG_PID" -o args= -ww 2>/dev/null |
      grep -Fq "darlingserver $ORIG "; then
    ORIGINAL=PASS
elif [[ -z "$ORIG_PID" ]]; then
    ORIGINAL=NOT_RUNNING_AT_START
else
    ORIGINAL=FAIL
fi
if git -C "$CORE" status --porcelain=v1 -uno >"$REPORT/git-after.txt" 2>/dev/null &&
   cmp -s "$REPORT/git-before.txt" "$REPORT/git-after.txt"; then
    GIT_STATE=UNCHANGED
else
    GIT_STATE=CHANGED_OR_UNVERIFIED
fi
cat > "$REPORT/REPRISE.txt" <<EOF
D4RLING QT-113
PIN=$PIN
HOST_TESTS=$HOST
LOCAL_SOURCE_CONTRACT=$SOURCE
SYMBOL_SCAN=$SYMBOLS
GUEST_EXEC=$GUEST
GUEST_EXIT=$GUEST_EXIT
CLEAN=$CLEAN
ORIGINAL=$ORIGINAL
SOURCE_STATUS=$GIT_STATE
REPORT=$REPORT
Notes: candidate symbol matches do not prove linkable i386 libSystem.
Only Ninja -n was used; no production build or installation.
EOF
echo "=== BILAN QT-113 ==="
cat "$REPORT/REPRISE.txt"
[[ ! -f "$REPORT/providers.json" ]] || sha256sum "$REPORT/providers.json"
echo "=== FIN D4RLING QT-113 ==="
