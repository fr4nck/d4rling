#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-only regression for Carbon/HIToolbox duplicate-symbol contracts.

This does not link or execute Darling. Full package build and ABI verification
must remain separate from these static, read-only checks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


FILES = {
    "carbon_impl": "src/frameworks/Carbon/src/Carbon.c",
    "carbon_cmake": "src/frameworks/Carbon/CMakeLists.txt",
    "event_header": "src/frameworks/Carbon/HIToolbox/include/HIToolbox/CarbonEventsCore.h",
    "event_impl": "src/frameworks/Carbon/HIToolbox/src/CarbonEventsCore.c",
    "hitoolbox_cmake": "src/frameworks/Carbon/HIToolbox/CMakeLists.txt",
}


def signature(text: str, return_type: str, name: str, terminator: str) -> tuple[str, ...] | None:
    """Read simple flat C declarations/definitions, dropping parameter names.

    Intentionally not a general C parser. Only the two interfaces used by this
    contract are allowed; unsupported signatures fail rather than pass.
    """
    pattern = re.compile(
        r"(?m)^[ \t]*" + re.escape(return_type) + r"\s+" + re.escape(name)
        + r"\s*\(([^()]*)\)\s*" + re.escape(terminator)
    )
    matches = pattern.findall(text)
    if len(matches) != 1:
        return None
    body = matches[0].strip()
    if not body or body == "void":
        return ()
    types = []
    for argument in body.split(","):
        argument = argument.strip()
        match = re.search(r"([A-Za-z_]\w*)$", argument)
        if not match:
            return None
        types.append(re.sub(r"\s+", "", argument[:match.start()].strip()))
    return tuple(types)


def definition_count(text: str, return_type: str, name: str) -> int:
    pattern = re.compile(
        r"(?m)^[ \t]*" + re.escape(return_type) + r"\s+" + re.escape(name)
        + r"\s*\([^()]*\)\s*\{"
    )
    return len(pattern.findall(text))


def function_body(text: str, return_type: str, name: str) -> str | None:
    match = re.search(
        r"(?ms)^[ \t]*" + re.escape(return_type) + r"\s+" + re.escape(name)
        + r"\s*\([^()]*\)\s*\{(.*?)\}",
        text,
    )
    return match.group(1) if match else None


def inspect(root: Path) -> dict:
    contents = {}
    for key, relative in FILES.items():
        path = root / relative
        if not path.is_file():
            raise ValueError(f"missing required source: {relative}")
        contents[key] = path.read_text(encoding="utf-8", errors="replace")

    legacy = contents["carbon_impl"]
    implementation = contents["event_impl"]
    header = contents["event_header"]
    expected = ("EventRef", "EventParamName", "EventParamType", "ByteCount", "constvoid*")
    header_sig = signature(header, "OSStatus", "SetEventParameter", ";")
    impl_sig = signature(implementation, "OSStatus", "SetEventParameter", "{")
    target_body = function_body(implementation, "EventTargetRef", "GetApplicationEventTarget")
    setter_body = function_body(implementation, "OSStatus", "SetEventParameter")

    checks = {
        "carbon_omits_duplicate_setter": definition_count(legacy, "OSStatus", "SetEventParameter") == 0,
        "carbon_omits_duplicate_application_target": (
            definition_count(legacy, "EventTargetRef", "GetApplicationEventTarget") == 0
        ),
        "header_setter_uses_bytecount": header_sig == expected,
        "hitoolbox_implements_matching_setter": impl_sig == expected,
        "hitoolbox_setter_stores_parameters": bool(
            setter_body is not None and "AllocateParameter" in setter_body
        ),
        "hitoolbox_has_application_target_declaration": (
            signature(header, "EventTargetRef", "GetApplicationEventTarget", ";") == ()
        ),
        "hitoolbox_application_target_is_nonnull": bool(
            target_body is not None
            and re.search(r"\breturn\s+&applicationTarget\s*;", target_body)
        ),
        "umbrella_carbon_includes_public_header": "#include <Carbon/Carbon.h>" in legacy,
        "carbon_reexports_hitoolbox": bool(
            re.search(r"\breexport\s*\(\s*Carbon\s+HIToolbox\b", contents["carbon_cmake"])
        ),
        "hitoolbox_builds_event_core": "src/CarbonEventsCore.c" in contents["hitoolbox_cmake"],
    }
    return {
        "schema_version": 1,
        "kind": "source_only_contract",
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "source_paths": FILES,
        "note": "source-level checks only; full Mach-O linking and guest ABI not tested",
    }


def main() -> int:
    repo = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, default=repo)
    parser.add_argument("--output", type=Path,
                        help="write JSON report to a new path; refuse to overwrite")
    args = parser.parse_args()
    try:
        report = inspect(args.checkout)
        if args.output is not None:
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, sort_keys=True)
                stream.write("\n")
        for name, passed in sorted(report["checks"].items()):
            print(f"{name}={'PASS' if passed else 'FAIL'}")
        print(f"SOURCE_ABI_CONTRACT={'PASS' if report['all_checks_pass'] else 'FAIL'}")
        return 0 if report["all_checks_pass"] else 1
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
