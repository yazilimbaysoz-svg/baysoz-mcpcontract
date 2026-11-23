# SPDX-License-Identifier: MIT
# Baysöz Labs <baysozlabs@proton.me>

"""JSON Schema audit tests."""

from __future__ import annotations

from baysoz_mcpcontract.loader import load_manifests
from baysoz_mcpcontract.profiles import get_profile
from baysoz_mcpcontract.schema_audit import audit_schema


def test_clean_schema_has_no_issues(clean_manifest: str) -> None:
    tools = load_manifests([clean_manifest])[0].tools
    for tool in tools:
        audit = audit_schema(tool.input_schema, get_profile("enterprise-strict"))
        assert audit.issues == ()
        assert audit.description_coverage == 1.0


def test_unsafe_schema_detects_deep_defects(unsafe_manifest: str) -> None:
    tool = load_manifests([unsafe_manifest])[0].tools[0]
    audit = audit_schema(tool.input_schema, get_profile("mcp-2025-06-18"))
    codes = {issue.code for issue in audit.issues}
    assert {"MCP002", "MCP006", "MCP007", "MCP013"}.issubset(codes)
    messages = " ".join(issue.message for issue in audit.issues)
    assert "recursive" in messages
    assert "unresolved" not in messages
    assert "default" in messages or "required" in messages


def test_output_secret_is_error(unsafe_manifest: str) -> None:
    tool = load_manifests([unsafe_manifest])[0].tools[0]
    assert tool.output_schema is not None
    audit = audit_schema(tool.output_schema, get_profile("mcp-2025-06-18"), is_output=True)
    assert any(issue.code == "MCP006" and issue.severity == "error" for issue in audit.issues)


def test_profile_feature_gating(unsafe_manifest: str) -> None:
    tool = load_manifests([unsafe_manifest])[0].tools[0]
    audit = audit_schema(tool.input_schema, get_profile("claude-code-2026"))
    unsupported = [issue for issue in audit.issues if issue.code == "MCP003"]
    assert {issue.message.split("'")[1] for issue in unsupported} >= {"$ref", "$defs", "oneOf"}


def test_bloat_and_depth_are_bounded() -> None:
    properties = {
        f"field_{index}": {"type": "string", "description": "A documented property."}
        for index in range(40)
    }
    schema = {"type": "object", "properties": properties, "additionalProperties": False}
    audit = audit_schema(schema, get_profile("enterprise-strict"))
    assert any("property count" in issue.message for issue in audit.issues)
    assert audit.property_count == 40
    assert audit.token_estimate > 0


def test_unresolved_ref_is_reported() -> None:
    schema = {
        "type": "object",
        "properties": {
            "value": {"$ref": "#/$defs/missing", "description": "A referenced value."}
        },
    }
    audit = audit_schema(schema, get_profile("mcp-2025-06-18"))
    assert any(issue.code == "MCP013" and "unresolved" in issue.message for issue in audit.issues)
