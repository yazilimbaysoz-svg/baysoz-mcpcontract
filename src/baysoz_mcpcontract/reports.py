# SPDX-License-Identifier: MIT
# Baysöz Labs <baysozlabs@proton.me>

"""Deterministic text, JSON and SARIF 2.1.0 report renderers."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from . import __attribution__, __version__
from .model import Finding
from .profiles import RULES

SCHEMA_URL = "https://json.schemastore.org/sarif-2.1.0.json"
REPOSITORY_URL = "https://github.com/yazilimbaysoz-svg/baysoz-mcpcontract"
LEVELS = {"error": "error", "warning": "warning", "note": "note"}


def summarize(findings: list[Finding]) -> dict[str, int]:
    counts = Counter(finding.severity for finding in findings)
    return {
        "total": len(findings),
        "error": counts.get("error", 0),
        "warning": counts.get("warning", 0),
        "note": counts.get("note", 0),
    }


def _header(profile_name: str) -> str:
    return f"baysoz-mcpcontract {__version__} | profile {profile_name}\n{__attribution__}"


def render_text(findings: list[Finding], profile_name: str, sources: list[str]) -> str:
    summary = summarize(findings)
    lines = [
        _header(profile_name),
        "",
        (
            f"Sources: {len(sources)} | findings: {summary['total']} "
            f"(error={summary['error']}, warning={summary['warning']}, note={summary['note']})"
        ),
        "",
    ]
    if not findings:
        lines.append("PASS: no contract violations detected.")
    for finding in findings:
        location = f"{finding.rule_id} {finding.tool or '<manifest>'} {finding.path or '-'}"
        lines.append(f"[{finding.severity.upper():7}] {location} @ {finding.source}")
        lines.append(f"          {finding.message}")
        lines.append(f"          fix: {finding.remediation}")
    lines.extend(["", f"Reported by {__attribution__}"])
    return "\n".join(lines)


def render_json(findings: list[Finding], profile_name: str, sources: list[str]) -> str:
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "tool": "baysoz-mcpcontract",
        "version": __version__,
        "attribution": __attribution__,
        "profile": profile_name,
        "sources": sources,
        "summary": summarize(findings),
        "findings": [
            {
                "rule_id": finding.rule_id,
                "severity": finding.severity,
                "message": finding.message,
                "source": finding.source,
                "tool": finding.tool,
                "path": finding.path,
                "remediation": finding.remediation,
                "fingerprint": finding.fingerprint,
            }
            for finding in findings
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_sarif(findings: list[Finding], profile_name: str, sources: list[str]) -> str:
    rules = []
    for rule_id, rule in sorted(RULES.items()):
        entry: dict[str, Any] = {
            "id": rule_id,
            "name": rule.name,
            "shortDescription": {"text": rule.name},
            "fullDescription": {"text": rule.rationale},
            "defaultConfiguration": {"level": LEVELS.get(rule.default_severity, "warning")},
            "help": {"text": rule.remediation},
        }
        if rule.references:
            entry["helpUri"] = rule.references[0]
        rules.append(entry)

    results = []
    for finding in findings:
        logical_name = f"{finding.source}:{finding.tool or '<manifest>'}:{finding.path or '-'}"
        results.append(
            {
                "ruleId": finding.rule_id,
                "level": LEVELS.get(finding.severity, "warning"),
                "message": {"text": finding.message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": finding.source},
                            "region": {"startLine": 1, "startColumn": 1},
                        },
                        "logicalLocations": [
                            {
                                "name": finding.tool or "<manifest>",
                                "fullyQualifiedName": logical_name,
                                "kind": "tool" if finding.tool else "manifest",
                            }
                        ],
                    }
                ],
                "fingerprints": {"mcpcontract/v1": finding.fingerprint},
            }
        )

    payload: dict[str, Any] = {
        "$schema": SCHEMA_URL,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "baysoz-mcpcontract",
                        "version": __version__,
                        "semanticVersion": __version__,
                        "informationUri": REPOSITORY_URL,
                        "fullName": f"MCP contract oracle by {__attribution__}",
                        "rules": rules,
                    }
                },
                "invocations": [
                    {
                        "executionSuccessful": True,
                        "commandLine": "mcpcontract check",
                        "properties": {
                            "profile": profile_name,
                            "sources": sources,
                            "attribution": __attribution__,
                        },
                    }
                ],
                "results": results,
                "properties": {
                    "attribution": __attribution__,
                    "summary": summarize(findings),
                },
            }
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render(findings: list[Finding], profile_name: str, sources: list[str], fmt: str) -> str:
    if fmt == "text":
        return render_text(findings, profile_name, sources)
    if fmt == "json":
        return render_json(findings, profile_name, sources)
    if fmt == "sarif":
        return render_sarif(findings, profile_name, sources)
    raise ValueError(f"unsupported report format: {fmt}")
