# SPDX-License-Identifier: MIT
# Baysöz Labs <baysozlabs@proton.me>

"""Report renderer tests."""

from __future__ import annotations

import json

from baysoz_mcpcontract import __attribution__
from baysoz_mcpcontract.analyzer import analyze
from baysoz_mcpcontract.loader import load_manifests
from baysoz_mcpcontract.profiles import get_profile
from baysoz_mcpcontract.reports import render, summarize


def _findings(path: str):
    return analyze(load_manifests([path]), get_profile("mcp-2025-06-18"))


def test_json_report_is_stable(clean_manifest: str) -> None:
    findings = _findings(clean_manifest)
    first = render(findings, "mcp-2025-06-18", [clean_manifest], "json")
    second = render(_findings(clean_manifest), "mcp-2025-06-18", [clean_manifest], "json")
    assert first == second
    payload = json.loads(first)
    assert payload["attribution"] == __attribution__
    assert payload["summary"] == {"total": 0, "error": 0, "warning": 0, "note": 0}


def test_sarif_report_is_valid_shape(unsafe_manifest: str) -> None:
    findings = _findings(unsafe_manifest)
    payload = json.loads(render(findings, "mcp-2025-06-18", [unsafe_manifest], "sarif"))
    assert payload["version"] == "2.1.0"
    run = payload["runs"][0]
    assert __attribution__ in run["tool"]["driver"]["fullName"]
    assert len(run["tool"]["driver"]["rules"]) == 13
    assert len(run["results"]) == len(findings)
    assert all("fingerprints" in result for result in run["results"])
    assert all(result["level"] in {"error", "warning", "note"} for result in run["results"])


def test_text_report_contains_remediation(unsafe_manifest: str) -> None:
    text = render(_findings(unsafe_manifest), "mcp-2025-06-18", [unsafe_manifest], "text")
    assert __attribution__ in text
    assert "fix:" in text
    assert "ERROR" in text


def test_summary_counts(unsafe_manifest: str) -> None:
    summary = summarize(_findings(unsafe_manifest))
    assert summary["total"] == summary["error"] + summary["warning"] + summary["note"]
    assert summary["error"] > 0
