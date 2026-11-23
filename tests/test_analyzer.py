# SPDX-License-Identifier: MIT
# Baysöz Labs <baysozlabs@proton.me>

"""Contract analysis and drift tests."""

from __future__ import annotations

from dataclasses import replace

from baysoz_mcpcontract.analyzer import analyze
from baysoz_mcpcontract.loader import load_manifests, merge_manifests
from baysoz_mcpcontract.profiles import get_profile


def _rules(findings) -> set[str]:
    return {finding.rule_id for finding in findings}


def test_clean_manifest_passes_strict_profile(clean_manifest: str) -> None:
    findings = analyze(load_manifests([clean_manifest]), get_profile("enterprise-strict"))
    assert findings == []


def test_unsafe_manifest_triggers_safety_rules(unsafe_manifest: str) -> None:
    findings = analyze(load_manifests([unsafe_manifest]), get_profile("mcp-2025-06-18"))
    rules = _rules(findings)
    assert {"MCP005", "MCP006", "MCP007", "MCP012", "MCP013"}.issubset(rules)
    assert any(finding.severity == "error" for finding in findings)
    assert all(finding.remediation for finding in findings)
    assert all(finding.fingerprint for finding in findings)


def test_cross_manifest_normalized_collision(unsafe_manifest: str, collision_manifest: str) -> None:
    findings = analyze(
        load_manifests([unsafe_manifest, collision_manifest]), get_profile("mcp-2025-06-18")
    )
    collisions = [finding for finding in findings if finding.rule_id == "MCP009"]
    assert len(collisions) == 2
    assert all("getstatuscopy" in finding.message for finding in collisions)


def test_baseline_drift_detects_narrowed_enum(
    clean_manifest: str, baseline_manifest: str
) -> None:
    baseline = merge_manifests(load_manifests([baseline_manifest]), source="published")
    findings = analyze(
        load_manifests([clean_manifest]), get_profile("mcp-2025-06-18"), baseline
    )
    drift = [finding for finding in findings if finding.rule_id == "MCP011"]
    assert any("enum was narrowed" in finding.message for finding in drift)


def test_baseline_drift_detects_removed_tool(
    clean_manifest: str, baseline_manifest: str
) -> None:
    manifests = load_manifests([clean_manifest])
    current = [
        replace(
            manifests[0],
            tools=tuple(tool for tool in manifests[0].tools if tool.name != "delete_cache"),
        )
    ]
    baseline = merge_manifests(load_manifests([baseline_manifest]), source="published")
    findings = analyze(current, get_profile("mcp-2025-06-18"), baseline)
    assert any("was removed" in finding.message for finding in findings)


def test_annotation_flip_is_error(clean_manifest: str, baseline_manifest: str) -> None:
    manifests = load_manifests([clean_manifest])
    tools = tuple(
        replace(tool, annotations={"readOnlyHint": True, "destructiveHint": False})
        if tool.name == "delete_cache"
        else tool
        for tool in manifests[0].tools
    )
    current = [replace(manifests[0], tools=tools)]
    baseline = merge_manifests(load_manifests([baseline_manifest]), source="published")
    findings = analyze(current, get_profile("mcp-2025-06-18"), baseline)
    assert any("annotation 'destructiveHint' changed" in finding.message for finding in findings)


def test_manifest_tool_count_is_checked(clean_manifest: str) -> None:
    manifests = load_manifests([clean_manifest])
    strict = get_profile("enterprise-strict")
    expanded = [
        replace(manifests[0], tools=manifests[0].tools + manifests[0].tools * strict.max_tools)
    ]
    findings = analyze(expanded, strict)
    assert any("above profile limit" in finding.message for finding in findings)
