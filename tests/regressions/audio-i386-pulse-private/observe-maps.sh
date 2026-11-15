#!/usr/bin/env bash
# AUDIO-I386: host-side, read-only observer. For SECONDS, records the ELF files mapped
# by any of the caller's processes that map a libpulse; never signals a process.
# Usage: observe-maps.sh SECONDS OUT.txt
set -u
end=$(( $(date +%s) + ${1:?seconds} )); out=${2:?out}; : > "$out.raw"
while [ "$(date +%s)" -lt "$end" ]; do
  for m in /proc/[0-9]*/maps; do
    p=${m#/proc/}; p=${p%/maps}
    [ -O "/proc/$p" ] || continue
    grep -q 'libpulse\.so' "$m" 2>/dev/null || continue
    exe=$(readlink "/proc/$p/exe" 2>/dev/null)
    awk -v p="$p" -v e="$exe" '$6 ~ /\.so/ {print p, e, $6}' "$m" 2>/dev/null >> "$out.raw"
  done
  sleep 0.2
done
sort -u "$out.raw" | awk '{print $2, $3}' | sort -u | while read -r e f; do
  printf '%s %s %s\n' "$(basename "$e")" "$(sha256sum "$f" 2>/dev/null | cut -c1-64)" "$f"
done > "$out"
