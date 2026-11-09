#!/usr/bin/env bash
# D4rling : build BSD i386 en deux OverlayFS prives.
# --check : lecture seule ; --build : dossier neuf sur WSL ext4.
set -Eeuo pipefail
umask 077
ulimit -c 0
export LC_ALL=C GIT_OPTIONAL_LOCKS=0 GIT_NO_LAZY_FETCH=1
export GIT_TERMINAL_PROMPT=0 PYTHONDONTWRITEBYTECODE=1
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR

S=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
B=$(dirname -- "$S")/build-core-i386
X=$S/src/external/xnu
P=$S/reproduction/patches/bsd-i386-return-lseek-fa29287.patch
WORK_ROOT=$(dirname -- "$(dirname -- "$S")")
BM4="${D4RLING_BSD_OUTPUT_ROOT:-$WORK_ROOT/C13-gQ93QvMc/BM4-tvUnbSa8}"

fail(){ echo "OVERLAY_BLOCKED=$1" >&2; exit 3; }

check(){
 [ "$(git -C "$S" rev-parse --show-toplevel)" = "$S" ] || fail REPO
 [ "$(git -C "$S" symbolic-ref -q --short HEAD)" = master ] || fail BRANCH
 git -C "$S" merge-base --is-ancestor ab20544d1bb8839ed2523342615142d7eabb4b6f HEAD || fail HISTORY
 git -C "$S" diff --quiet ab20544d1bb8839ed2523342615142d7eabb4b6f HEAD -- CMakeLists.txt src/CMakeLists.txt src/startup src/external/xnu src/external/dyld || fail CRITICAL_CHANGE
 [ -z "$(git -C "$S" status --porcelain=v1 --untracked-files=no --ignore-submodules=all)" ] || fail DIRTY
 [ "$(git -C "$X" rev-parse HEAD)" = fa29287aa2f0115271e091f1031f53c9e024005d ] || fail XNU
 [ "$(git -C "$S" ls-tree HEAD src/external/xnu | awk '{print $3}')" = fa29287aa2f0115271e091f1031f53c9e024005d ] || fail GITLINK
 [ -z "$(git -C "$X" status --porcelain=v1 --untracked-files=all)" ] || fail XNU_DIRTY
 [ "$(sha256sum "$P" | awk '{print $1}')" = d2642690c6c15601261429fe807dca674dd06ada08e85ca554cd120655ec3d61 ] || fail PATCH
 git -C "$X" apply --check -- "$P" || fail PATCH_APPLICABILITY
 [ -f "$B/build.ninja" ] && [ -f "$B/CMakeCache.txt" ] || fail BUILD
 grep -Fqx "CMAKE_HOME_DIRECTORY:INTERNAL=$S" "$B/CMakeCache.txt" || fail CMAKE_SOURCE
 ninja -C "$B" -t query system_kernel >/dev/null || fail KERNEL_TARGET
 ninja -C "$B" -t query system_loader >/dev/null || fail DYLD_TARGET
 echo 'OVERLAY_CHECK=PASS'
}

case "${1:-}" in
__worker)
 shift
set -Eeuo pipefail
umask 077
ulimit -c 0

SRC=$1
XNU=$2
BUILD=$3
PATCH=$4
OUT=$5
HOST_MNT=$6

blocked() {
    echo "BSD_OVERLAY_WORKER_BLOCKED=$1"
    exit 3
}

[ "$(readlink /proc/self/ns/mnt)" != "$HOST_MNT" ] ||
    blocked HOST_MOUNT_NAMESPACE

mount --make-rprivate /

# Le reste du canon est en lecture seule.
mount --bind "$SRC" "$SRC"
mount -o remount,bind,ro "$SRC"

# XNU : bind inferieur RO puis overlay prive.
mount --bind "$XNU" "$OUT/lower/xnu"
mount -o remount,bind,ro "$OUT/lower/xnu"

mount -t overlay overlay \
    -o "lowerdir=$OUT/lower/xnu,upperdir=$OUT/upper/xnu,workdir=$OUT/work/xnu" \
    "$XNU"

# Build : meme chemin absolu, mais toutes les ecritures
# sont redirigees dans upper/build.
mount --bind "$BUILD" "$OUT/lower/build"
mount -o remount,bind,ro "$OUT/lower/build"

mount -t overlay overlay \
    -o "lowerdir=$OUT/lower/build,upperdir=$OUT/upper/build,workdir=$OUT/work/build" \
    "$BUILD"

[ "$(stat -f -c %T "$XNU")" = overlayfs ] ||
    blocked XNU_OVERLAY_NOT_ACTIVE
[ "$(stat -f -c %T "$BUILD")" = overlayfs ] ||
    blocked BUILD_OVERLAY_NOT_ACTIVE

mount --bind "$OUT/tmp" /tmp

export HOME="$OUT/home"
export TMPDIR="$OUT/tmp"
export XDG_CACHE_HOME="$OUT/cache"

echo 'SOURCE_NAMESPACE=PRIVATE'
echo 'XNU_OVERLAY=ACTIVE'
echo 'BUILD_OVERLAY=ACTIVE'

echo
echo '=== APPLICATION DU PATCH COMBINE ==='

git -C "$XNU" apply --check -- "$PATCH"
git -C "$XNU" apply -- "$PATCH"
git -C "$XNU" apply --reverse --check -- "$PATCH"

EXPECTED=$(printf '%s\n' \
    'darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/bsd_syscall_table.h' \
    'darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/bsd_syscall.S' \
    'darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/bsd_syscall_table.c' \
    'darling/src/libsystem_kernel/emulation/src/xnu_syscall/bsd/impl/unistd/lseek.c' |
    sort)

ACTUAL=$(git -C "$XNU" diff --name-only | sort)
[ "$ACTUAL" = "$EXPECTED" ] ||
    blocked PATCH_FILE_SET_MISMATCH

echo 'PATCH_APPLIED_ONLY_IN_OVERLAY=PASS'

echo
echo '=== GRAPHE DE RECONSTRUCTION ==='

ninja -C "$BUILD" -n system_kernel system_loader \
    > "$OUT/dry-run.log" 2>&1 ||
    blocked NINJA_DRY_RUN_FAILED

DRY_COUNT=$(
    grep -Ec '^\[[0-9]+/[0-9]+\]' \
        "$OUT/dry-run.log" || true
)

echo "NINJA_PLANNED_ACTIONS=$DRY_COUNT"

[ "$DRY_COUNT" -gt 0 ] ||
    blocked NO_REBUILD_DETECTED
[ "$DRY_COUNT" -le 700 ] ||
    blocked REBUILD_TOO_BROAD

grep -Fq 'bsd_syscall.S' "$OUT/dry-run.log" ||
    blocked DISPATCHER_NOT_REBUILT
grep -Fq 'lseek.c' "$OUT/dry-run.log" ||
    blocked LSEEK_NOT_REBUILT

echo
echo '=== COMPILATION ==='

ninja -C "$BUILD" -j 2 \
    system_kernel system_loader \
    > "$OUT/ninja.log" 2>&1 ||
    blocked NINJA_BUILD_FAILED

K="$BUILD/src/external/xnu/darling/src/libsystem_kernel/libsystem_kernel.dylib"
D="$BUILD/src/external/dyld/dyld"

[ -s "$K" ] && [ -s "$D" ] ||
    blocked CANDIDATE_BINARIES_MISSING

cp -- "$K" "$OUT/exports/libsystem_kernel.dylib"
cp -- "$D" "$OUT/exports/dyld"

sha256sum "$OUT/exports/libsystem_kernel.dylib"
sha256sum "$OUT/exports/dyld"

echo 'BSD_OVERLAY_REBUILD=PASS'
echo 'BSD_OVERLAY_EXPORT=PASS'
 ;;
--check)
 [ "$#" -eq 1 ] || fail ARGS
 check
 ;;
--build)
 [ "$#" -eq 2 ] || fail ARGS
 check
 case "$2" in /*) ;; *) fail ABSOLUTE_OUTPUT_REQUIRED ;; esac
 O=$(realpath -m -- "$2")
 [ "$O" = "$2" ] || fail NOT_CANONICAL
 case "$BM4/" in "$WORK_ROOT/"*) ;; *) fail OUTPUT_ROOT_OUTSIDE_WORKTREE ;; esac
 [ "$(realpath -m -- "$BM4")" = "$BM4" ] || fail OUTPUT_ROOT_NOT_CANONICAL
 case "$O/" in "$BM4/"*) ;; *) fail OUTSIDE_BM4 ;; esac
 case "$O/" in
  "$BM4/r11/"*|"$BM4/r10/"*|"$BM4/r6/"*|"$BM4/r5-lseek/"*)
   fail PROTECTED_OUTPUT ;;
 esac
 [ ! -e "$O" ] && [ ! -L "$O" ] || fail OUTPUT_EXISTS
 PAR=$(dirname -- "$O")
 [ -d "$PAR" ] || fail PARENT_MISSING
 case "$(stat -f -c %T "$PAR")" in ext4|ext2/ext3) ;; *) fail NOT_EXT4 ;; esac

 BEFORE=$(df -Pk "$PAR" | awk 'END {print $4}')
 [ "$BEFORE" -gt 3145728 ] || fail LOW_DISK_SPACE
 HOST_MNT=$(readlink /proc/self/ns/mnt)

 mkdir -m 700 -- "$O"
 for p in lower upper work; do
  mkdir -m 700 -- "$O/$p" "$O/$p/xnu" "$O/$p/build"
 done
 mkdir -m 700 -- "$O/exports" "$O/home" "$O/cache" "$O/tmp"

 timeout --signal=TERM --kill-after=10s 1200s \
  unshare --user --map-root-user --mount --mount-proc \
  --pid --fork --kill-child --ipc --uts --net \
  /bin/bash "$0" __worker \
  "$S" "$X" "$B" "$P" "$O" "$HOST_MNT" \
  > "$O/build.log" 2>&1 &

 PID=$!
 LIMIT_HIT=0
 while kill -0 "$PID" 2>/dev/null; do
  NOW=$(df -Pk "$PAR" | awk 'END {print $4}')
  if [ "$((BEFORE-NOW))" -gt 2097152 ]; then
   LIMIT_HIT=1
   kill -TERM "$PID" 2>/dev/null || true
   break
  fi
  sleep 3
 done

 if wait "$PID"; then RC=0; else RC=$?; fi
 echo "BUILD_EXIT=$RC"

 [ "$RC" -eq 0 ] && [ "$LIMIT_HIT" -eq 0 ] || {
  tail -n 35 "$O/build.log"
  fail BUILD_FAILED
 }
 grep -Fq 'BSD_OVERLAY_REBUILD=PASS' "$O/build.log" || fail BUILD_NOT_PROVED
 (cd -- "$O/exports" && sha256sum libsystem_kernel.dylib dyld > SHA256SUMS && sha256sum -c SHA256SUMS) || fail EXPORT_SHA
 [ "$(df -Pk "$PAR" | awk 'END {print $4}')" -ge "$((BEFORE-2097152))" ] || fail BUDGET
 [ -z "$(git -C "$X" status --porcelain=v1 --untracked-files=all)" ] || fail ORIGINAL_XNU_MODIFIED
 echo 'OVERLAY_BUILD=PASS_BOUNDED'
 ;;
*) fail USAGE_CHECK_OR_BUILD ;;
esac
