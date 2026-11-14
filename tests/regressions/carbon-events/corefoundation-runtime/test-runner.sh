#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Infrastructure-only negative/positive control-flow tests. The fake commands
# do not inspect or execute Mach-O, and cannot qualify CoreFoundation runtime.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
mkdir "$tmp/mock-bin"
: > "$tmp/dummy-exe"
: > "$tmp/dummy-cf"
cat > "$tmp/mock-bin/file" <<'MOCK_FILE'
#!/bin/sh
case "$*" in
    *dummy-exe*) printf '%s\n' 'Mach-O 64-bit x86_64 executable' ;;
    *dummy-cf*) printf '%s\n' 'Mach-O 64-bit x86_64 dynamically linked shared library' ;;
    *) printf '%s\n' 'ELF 64-bit x86-64 executable' ;;
esac
MOCK_FILE
cat > "$tmp/mock-bin/llvm-objdump" <<'MOCK_OBJDUMP'
#!/bin/sh
if [ "${MOCK_CF_DEP:-0}" = 1 ]; then
    printf '%s\n' '/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation'
fi
if [ "${MOCK_HIT_DEP:-0}" = 1 ]; then
    printf '%s\n' '/System/Library/Frameworks/Carbon.framework/Frameworks/HIToolbox.framework/HIToolbox'
fi
MOCK_OBJDUMP
cat > "$tmp/runner" <<'MOCK_RUNNER'
#!/bin/sh
case "${MOCK_SUITE:-corefoundation}" in
    corefoundation) printf '%s\n' 'CoreFoundation Mach-O runtime checks: 18 | Failures: 0' ;;
    carbon) printf '%s\n' 'Carbon HIToolbox/CoreFoundation integration checks: 18 | Failures: 0' ;;
    wrong) printf '%s\n' 'not a test result' ;;
esac
exit "${MOCK_RUNNER_STATUS:-0}"
MOCK_RUNNER
chmod +x "$tmp/mock-bin/file" "$tmp/mock-bin/llvm-objdump" "$tmp/runner"
checks=0
failures=0
check_exit() {
    expected=$1
    shift
    set +e
    "$@" > "$tmp/stdout" 2> "$tmp/stderr"
    actual=$?
    set -e
    checks=$((checks + 1))
    if [ "$actual" -eq "$expected" ]; then
        printf 'PASS: guard %u, exit %s\n' "$checks" "$actual"
    else
        failures=$((failures + 1))
        printf 'FAIL: guard %u, expected %s got %s\n' "$checks" "$expected" "$actual" >&2
        cat "$tmp/stdout" "$tmp/stderr" >&2
    fi
}
check_exit 2 sh "$script_dir/run.sh"
check_exit 2 sh "$script_dir/run.sh" corefoundation /bin/true /bin/true /bin/true
check_exit 2 env PATH="$tmp/mock-bin:$PATH" MOCK_CF_DEP=0 sh "$script_dir/run.sh" corefoundation "$tmp/dummy-exe" "$tmp/dummy-cf" "$tmp/runner"
check_exit 2 env PATH="$tmp/mock-bin:$PATH" MOCK_CF_DEP=1 MOCK_HIT_DEP=0 sh "$script_dir/run.sh" carbon "$tmp/dummy-exe" "$tmp/dummy-cf" "$tmp/runner"
check_exit 2 env PATH="$tmp/mock-bin:$PATH" MOCK_CF_DEP=1 sh "$script_dir/run.sh" corefoundation "$tmp/dummy-exe" "$tmp/dummy-cf" "$tmp/no-runner"
check_exit 1 env PATH="$tmp/mock-bin:$PATH" MOCK_CF_DEP=1 MOCK_RUNNER_STATUS=1 sh "$script_dir/run.sh" corefoundation "$tmp/dummy-exe" "$tmp/dummy-cf" "$tmp/runner"
check_exit 1 env PATH="$tmp/mock-bin:$PATH" MOCK_CF_DEP=1 MOCK_SUITE=wrong sh "$script_dir/run.sh" corefoundation "$tmp/dummy-exe" "$tmp/dummy-cf" "$tmp/runner"
check_exit 0 env PATH="$tmp/mock-bin:$PATH" MOCK_CF_DEP=1 MOCK_SUITE=corefoundation sh "$script_dir/run.sh" corefoundation "$tmp/dummy-exe" "$tmp/dummy-cf" "$tmp/runner"
check_exit 0 env PATH="$tmp/mock-bin:$PATH" MOCK_CF_DEP=1 MOCK_HIT_DEP=1 MOCK_SUITE=carbon sh "$script_dir/run.sh" carbon "$tmp/dummy-exe" "$tmp/dummy-cf" "$tmp/runner"
printf 'Runner control-flow checks: %u | Failures: %u (MOCKS ONLY, no Mach-O executed)\n' "$checks" "$failures"
[ "$failures" -eq 0 ]
