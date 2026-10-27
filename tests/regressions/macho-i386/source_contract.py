#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only check of the Darling i386 libSystem source dependency contract.

This inspects CMake source and declarations, not compiled binaries. It cannot
establish that an i386 dynamic build or runtime API invocation will succeed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


class ContractError(ValueError):
    """Missing or altered source relationship."""


def cmake_calls(content: str, name: str) -> list[list[str]]:
    """Extract simple multiline CMake calls; comments and quotes respected.

    Deliberately supports only the form used by the relevant Darling sources.
    Does not evaluate CMake macros or generator expressions.
    """
    found = []
    match_re = re.compile(r"(?im)^\s*" + re.escape(name) + r"\s*\(")
    for match in match_re.finditer(content):
        depth = 1
        quote = False
        comment = False
        escape = False
        pos = match.end()
        buffer = []
        while pos < len(content) and depth:
            c = content[pos]
            pos += 1
            if comment:
                if c == "\n":
                    comment = False
                    buffer.append(" ")
                continue
            if escape:
                buffer.append(c)
                escape = False
                continue
            if c == "\\" and quote:
                buffer.append(c)
                escape = True
                continue
            if c == '"':
                quote = not quote
                buffer.append(c)
                continue
            if not quote and c == "#":
                comment = True
                continue
            if not quote and c == "(":
                depth += 1
            if not quote and c == ")":
                depth -= 1
                if depth == 0:
                    break
            buffer.append(c)
        if depth:
            raise ContractError(f"unclosed {name}( command")
        found.append(re.findall(r'"(?:[^"\\]|\\.)*"|\S+', "".join(buffer)))
    return found


def find_call(source: str, command: str, target: str) -> list[str]:
    matches = [args for args in cmake_calls(source, command)
               if args and args[0] == target]
    if len(matches) != 1:
        raise ContractError(f"expected one {command}({target} ...), found {len(matches)}")
    return matches[0]


def object_targets(args: list[str]) -> set[str]:
    return set(re.findall(r"\$<TARGET_OBJECTS:([A-Za-z0-9_]+)>", " ".join(args)))


def values_after(args: list[str], key: str, markers: set[str]) -> list[str]:
    if key not in args:
        raise ContractError(f"missing CMake section {key}")
    start = args.index(key) + 1
    result = []
    for value in args[start:]:
        if value in markers:
            break
        result.append(value)
    return result


def inspect_checkout(root: Path) -> dict:
    """Inspect initialized, pinned source submodules under an existing checkout."""
    files = {
        "kernel_cmake": "src/external/xnu/darling/src/libsystem_kernel/CMakeLists.txt",
        "syscall_cmake": "src/external/xnu/libsyscall/CMakeLists.txt",
        "kernel_init": "src/external/xnu/libsyscall/wrappers/_libkernel_init.c",
        "malloc_cmake": "src/external/libmalloc/CMakeLists.txt",
        "malloc_impl": "src/external/libmalloc/src/malloc.c",
        "system_cmake": "src/external/libsystem/CMakeLists.txt",
    }
    content = {}
    for key, relative in files.items():
        path = root / relative
        if not path.is_file():
            raise ContractError(f"required initialized source missing: {relative}")
        content[key] = path.read_text(encoding="utf-8", errors="replace")

    checks: dict[str, bool] = {}
    static_args = find_call(content["kernel_cmake"], "add_library", "system_kernel_static32")
    dynamic_args = find_call(content["kernel_cmake"], "add_circular", "system_kernel")
    static_objects = object_targets(static_args)
    dynamic_objects = object_targets(dynamic_args)
    checks["static32_has_expected_objects"] = {
        "libsyscall_32", "libsyscall", "emulation_dyld"
    } <= static_objects and "STATIC" in static_args
    checks["static32_omits_dynamic_init_objects"] = "libsyscall_dynamic" not in static_objects
    checks["dynamic_kernel_has_init_objects"] = "libsyscall_dynamic" in dynamic_objects
    checks["dynamic_kernel_uses_circular_dependencies"] = (
        "SIBLINGS" in dynamic_args
        and {"system_c", "compiler_rt", "system_dyld"} <= set(
            values_after(dynamic_args, "SIBLINGS", {"DEPENDENCIES", "STRONG_SIBLINGS", "LINK_FLAGS"})
        )
    )

    dynamic_source_args = find_call(content["syscall_cmake"], "set", "syscall_dynamic_sources")
    dynamic_target_args = find_call(content["syscall_cmake"], "add_darling_object_library", "libsyscall_dynamic")
    checks["kernel_init_compiled_only_in_dynamic_source_group"] = (
        "wrappers/_libkernel_init.c" in dynamic_source_args
        and "${syscall_dynamic_sources}" in dynamic_target_args
        and "wrappers/_libkernel_init.c" not in find_call(content["syscall_cmake"], "set", "syscall_sources")
    )
    checks["libkernel_functions_declared_in_kernel_init"] = bool(re.search(
        r"\b_libkernel_functions_t\s+_libkernel_functions\s*;", content["kernel_init"]
    ))

    malloc_sources = find_call(content["malloc_cmake"], "set", "libmalloc_sources")
    malloc_target = find_call(content["malloc_cmake"], "add_circular", "system_malloc")
    checks["malloc_source_in_dynamic_malloc_target"] = (
        "src/malloc.c" in malloc_sources
        and "${libmalloc_sources}" in malloc_target
        and "FAT" in malloc_target
    )
    checks["malloc_and_free_defined_in_source"] = (
        bool(re.search(r"(?m)^malloc\s*\(\s*size_t\s+size\s*\)", content["malloc_impl"]))
        and bool(re.search(r"(?m)^free\s*\(\s*void\s*\*\s*ptr\s*\)", content["malloc_impl"]))
    )

    system_target = find_call(content["system_cmake"], "add_circular", "system")
    reexport_calls = cmake_calls(content["system_cmake"], "libsystem_reexport")
    if len(reexport_calls) != 1:
        raise ContractError("expected one libsystem_reexport(...) declaration")
    system_reexports = reexport_calls[0]
    checks["libsystem_dynamically_reexports_malloc_and_kernel"] = (
        "FAT" in system_target
        and len(system_reexports) % 2 == 0
        and "system_kernel" in system_reexports[::2]
        and "system_malloc" in system_reexports[::2]
    )

    return {
        "schema_version": 1,
        "kind": "source_contract_only",
        "sources": files,
        "static32_object_targets": sorted(static_objects),
        "dynamic_kernel_object_targets": sorted(dynamic_objects),
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "conclusion": (
            "static system_kernel archive is not a substitute for the dynamic "
            "libSystem dependency graph; compile/link/runtime remain unverified"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--output", type=Path,
                        help="write new JSON report; existing targets are not overwritten")
    args = parser.parse_args()
    try:
        report = inspect_checkout(args.checkout)
        payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(payload)
            print(f"REPORT={args.output}")
        else:
            print(payload, end="")
        return 0 if report["all_checks_pass"] else 1
    except (OSError, ContractError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
