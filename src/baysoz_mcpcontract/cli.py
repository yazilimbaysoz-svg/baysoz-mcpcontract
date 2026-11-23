# SPDX-License-Identifier: MIT
# Baysöz Labs <baysozlabs@proton.me>

"""Command-line interface for the Baysöz Labs MCP contract oracle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __attribution__, __version__
from .analyzer import analyze
from .loader import load_manifests, merge_manifests
from .profiles import DEFAULT_PROFILE, PROFILES, RULES, get_profile
from .reports import render, summarize

PROGRAM = "mcpcontract"
EPILOG = f"Deterministic MCP contract gates by {__attribution__}."


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--version",
        action="version",
        version=f"{PROGRAM} {__version__} | {__attribution__}",
        help="show program version and Baysöz Labs attribution",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description=(
            "Offline MCP tool-contract conformance, portability and drift oracle "
            f"by {__attribution__}."
        ),
        epilog=EPILOG,
    )
    _add_common(parser)
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    check = subparsers.add_parser(
        "check",
        help="analyze tools/list exports and emit a CI gate report",
        description=f"Analyze MCP manifests deterministically by {__attribution__}.",
        epilog=EPILOG,
    )
    _add_common(check)
    check.add_argument("paths", nargs="+", help="JSON/JSONL file or directory of MCP manifests")
    check.add_argument("--profile", default=DEFAULT_PROFILE, help="portability profile name")
    check.add_argument("--baseline", help="published tools/list snapshot for drift detection")
    check.add_argument(
        "--format", choices=("text", "json", "sarif"), default="text", help="report format"
    )
    check.add_argument("--output", help="write the report to this file instead of stdout")
    check.add_argument(
        "--fail-on",
        choices=("error", "warning", "never"),
        default="error",
        help="severity that produces a non-zero exit status (default: error)",
    )

    profiles = subparsers.add_parser(
        "profiles",
        help="list or inspect portability profiles",
        description=f"Portability profiles maintained by {__attribution__}.",
        epilog=EPILOG,
    )
    _add_common(profiles)
    profiles.add_argument("--name", help="show one profile by name")

    rules = subparsers.add_parser(
        "rules",
        help="list or inspect deterministic rule metadata",
        description=f"Stable rule catalogue by {__attribution__}.",
        epilog=EPILOG,
    )
    _add_common(rules)
    rules.add_argument("--rule", help="show one rule by ID")

    normalize = subparsers.add_parser(
        "normalize",
        help="emit a canonical, sorted tools/list document for golden diffs",
        description=f"Deterministic manifest canonicalization by {__attribution__}.",
        epilog=EPILOG,
    )
    _add_common(normalize)
    normalize.add_argument("paths", nargs="+", help="JSON/JSONL file or directory of manifests")
    normalize.add_argument("--output", help="write canonical JSON to this file instead of stdout")
    return parser


def _profiles_command(name: str | None) -> str:
    lines = [f"baysoz-mcpcontract profiles | {__attribution__}", ""]
    selected = sorted(PROFILES) if name is None else [name]
    for profile_name in selected:
        profile = get_profile(profile_name)
        lines.append(f"{profile.name}")
        lines.append(f"  {profile.description}")
        lines.append(
            "  limits: "
            f"tools<={profile.max_tools}, bytes<={profile.max_schema_bytes}, "
            f"props<={profile.max_properties}, depth<={profile.max_depth}, "
            f"tokens~{profile.max_token_estimate}, docs>={profile.min_description_coverage:.0%}"
        )
        lines.append(f"  features: {', '.join(sorted(profile.supported_features))}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _rules_command(rule_id: str | None) -> str:
    lines = [f"baysoz-mcpcontract rules | {__attribution__}", ""]
    selected = sorted(RULES) if rule_id is None else [rule_id]
    for identifier in selected:
        rule = RULES.get(identifier)
        if rule is None:
            raise ValueError(f"unknown rule {identifier!r}")
        lines.append(f"{rule.rule_id} {rule.name} ({rule.default_severity})")
        lines.append(f"  {rule.rationale}")
        lines.append(f"  fix: {rule.remediation}")
        for reference in rule.references:
            lines.append(f"  evidence: {reference}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_output(content: str, output: str | None) -> None:
    if output:
        Path(output).write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
    else:
        sys.stdout.write(content if content.endswith("\n") else content + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        if args.command == "profiles":
            _write_output(_profiles_command(args.name), None)
            return 0
        if args.command == "rules":
            _write_output(_rules_command(args.rule), None)
            return 0
        if args.command == "normalize":
            manifests = load_manifests(args.paths)
            payload = {
                "attribution": __attribution__,
                "schema_version": "1.0",
                "tools": [tool.raw for manifest in manifests for tool in manifest.tools],
            }
            _write_output(
                json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                args.output,
            )
            return 0

        profile = get_profile(args.profile)
        manifests = load_manifests(args.paths)
        baseline_manifest = None
        if args.baseline:
            baseline_manifest = merge_manifests(
                load_manifests([args.baseline]), source=args.baseline
            )
        findings = analyze(manifests, profile, baseline_manifest)
        sources = [manifest.source for manifest in manifests]
        if args.baseline:
            sources.append(f"baseline:{args.baseline}")
        report = render(findings, profile.name, sources, args.format)
        _write_output(report, args.output)
        summary = summarize(findings)
        if args.fail_on == "never":
            return 0
        if args.fail_on == "warning":
            return 1 if summary["error"] or summary["warning"] else 0
        return 1 if summary["error"] else 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"{PROGRAM}: error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
