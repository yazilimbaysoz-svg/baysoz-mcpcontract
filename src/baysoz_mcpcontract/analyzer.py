# SPDX-License-Identifier: MIT
# Baysöz Labs <baysozlabs@proton.me>

"""Contract analysis engine: structure, safety, portability and drift."""

from __future__ import annotations

import re
from typing import Any, Iterable

from .loader import canonical_json
from .model import COMMAND_NAMES, Finding, Manifest, Profile, Tool
from .profiles import RULES
from .schema_audit import audit_schema

TOOL_NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
ANNOTATION_FLAGS = ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint")


def _finding(
    rule_id: str,
    severity: str,
    message: str,
    *,
    source: str,
    tool: str = "",
    path: str = "",
) -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=severity,
        message=message,
        source=source,
        tool=tool,
        path=path,
        remediation=RULES[rule_id].remediation,
    ).with_fingerprint()


def _walk_properties(schema: dict[str, Any], prefix: str = "") -> Iterable[tuple[str, dict[str, Any], str]]:
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return
    for name, subschema in properties.items():
        path = f"{prefix}.{name}" if prefix else name
        if isinstance(subschema, dict):
            yield name, subschema, f"inputSchema.properties.{path}"
            yield from _walk_properties(subschema, path)


def _annotation_checks(tool: Tool, profile: Profile) -> list[Finding]:
    findings: list[Finding] = []
    annotations = tool.annotations
    for key in ANNOTATION_FLAGS:
        if key in annotations and not isinstance(annotations[key], bool):
            findings.append(
                _finding(
                    "MCP005",
                    "error",
                    f"annotation '{key}' must be a boolean",
                    source=tool.source,
                    tool=tool.name,
                    path=f"annotations.{key}",
                )
            )
    if profile.require_annotations:
        for key in ("readOnlyHint", "destructiveHint"):
            if key not in annotations:
                findings.append(
                    _finding(
                        "MCP005",
                        "error",
                        f"profile {profile.name} requires annotations.{key}",
                        source=tool.source,
                        tool=tool.name,
                        path=f"annotations.{key}",
                    )
                )
    read_only = annotations.get("readOnlyHint") is True
    destructive = annotations.get("destructiveHint") is True
    if tool.is_mutating and read_only:
        findings.append(
            _finding(
                "MCP005",
                "error",
                "tool performs a mutating operation but declares readOnlyHint=true",
                source=tool.source,
                tool=tool.name,
                path="annotations.readOnlyHint",
            )
        )
    if tool.is_high_risk and not destructive:
        findings.append(
            _finding(
                "MCP005",
                "error",
                "high-risk operation requires annotations.destructiveHint=true",
                source=tool.source,
                tool=tool.name,
                path="annotations.destructiveHint",
            )
        )
    if tool.is_read_named and not tool.is_mutating and destructive:
        findings.append(
            _finding(
                "MCP005",
                "warning",
                "read-oriented tool declares destructiveHint=true",
                source=tool.source,
                tool=tool.name,
                path="annotations.destructiveHint",
            )
        )
    return findings


def _command_checks(tool: Tool) -> list[Finding]:
    findings: list[Finding] = []
    for name, subschema, path in _walk_properties(tool.input_schema):
        if not COMMAND_NAMES.search(name) or subschema.get("type") != "string":
            continue
        constrained = any(key in subschema for key in ("enum", "const", "pattern", "maxLength"))
        if constrained:
            continue
        severity = "warning" if tool.annotations.get("destructiveHint") is True else "error"
        findings.append(
            _finding(
                "MCP012",
                severity,
                f"free-form command/query property '{name}' is an injection sink",
                source=tool.source,
                tool=tool.name,
                path=path,
            )
        )
    return findings


def _analyze_tool(tool: Tool, profile: Profile) -> list[Finding]:
    findings: list[Finding] = []
    if not TOOL_NAME_PATTERN.fullmatch(tool.name):
        findings.append(
            _finding(
                "MCP001",
                "error",
                "tool name must match [A-Za-z0-9_-]{1,64}",
                source=tool.source,
                tool=tool.name,
                path="name",
            )
        )
    description = tool.description.strip()
    if not description:
        findings.append(
            _finding(
                "MCP004",
                "error",
                "tool has no description",
                source=tool.source,
                tool=tool.name,
                path="description",
            )
        )
    elif len(description) < 12:
        findings.append(
            _finding(
                "MCP004",
                "warning",
                "tool description is shorter than 12 characters",
                source=tool.source,
                tool=tool.name,
                path="description",
            )
        )

    if not isinstance(tool.raw.get("inputSchema"), dict):
        findings.append(
            _finding(
                "MCP001",
                "error",
                "inputSchema must be a JSON Schema object",
                source=tool.source,
                tool=tool.name,
                path="inputSchema",
            )
        )
    elif tool.input_schema.get("type") != "object":
        findings.append(
            _finding(
                "MCP001",
                "error",
                "inputSchema.type must be 'object' for MCP tools",
                source=tool.source,
                tool=tool.name,
                path="inputSchema.type",
            )
        )
    if "annotations" in tool.raw and not isinstance(tool.raw["annotations"], dict):
        findings.append(
            _finding(
                "MCP001",
                "error",
                "annotations must be a JSON object",
                source=tool.source,
                tool=tool.name,
                path="annotations",
            )
        )

    audit = audit_schema(tool.input_schema, profile, base_path="inputSchema")
    for issue in audit.issues:
        findings.append(
            _finding(
                issue.code,
                issue.severity,
                issue.message,
                source=tool.source,
                tool=tool.name,
                path=issue.path,
            )
        )

    if tool.output_schema is not None:
        output_audit = audit_schema(
            tool.output_schema, profile, base_path="outputSchema", is_output=True
        )
        for issue in output_audit.issues:
            if issue.code in {"MCP004", "MCP008"}:
                continue
            findings.append(
                _finding(
                    issue.code,
                    issue.severity,
                    issue.message,
                    source=tool.source,
                    tool=tool.name,
                    path=issue.path,
                )
            )
        if tool.output_schema.get("type") != "object":
            findings.append(
                _finding(
                    "MCP010",
                    "warning",
                    "structured outputSchema should declare type='object'",
                    source=tool.source,
                    tool=tool.name,
                    path="outputSchema.type",
                )
            )
    elif profile.require_output_schema_for_mutating and tool.is_mutating:
        findings.append(
            _finding(
                "MCP010",
                "warning",
                "profile requires a structured outputSchema for mutating tools",
                source=tool.source,
                tool=tool.name,
                path="outputSchema",
            )
        )

    findings.extend(_annotation_checks(tool, profile))
    findings.extend(_command_checks(tool))
    return findings


def _collision_checks(tools: list[Tool]) -> list[Finding]:
    grouped: dict[str, list[Tool]] = {}
    for tool in tools:
        if tool.name:
            grouped.setdefault(tool.canonical_name, []).append(tool)
    findings: list[Finding] = []
    for normalized, group in sorted(grouped.items()):
        if len(group) < 2 or len({tool.name for tool in group}) < 2:
            continue
        names = ", ".join(sorted({tool.name for tool in group}))
        for tool in group:
            findings.append(
                _finding(
                    "MCP009",
                    "error",
                    f"normalized tool name '{normalized}' is ambiguous across: {names}",
                    source=tool.source,
                    tool=tool.name,
                    path="name",
                )
            )
    return findings


def analyze(manifests: list[Manifest], profile: Profile, baseline: Manifest | None = None) -> list[Finding]:
    tools = [tool for manifest in manifests for tool in manifest.tools]
    findings: list[Finding] = []
    for manifest in manifests:
        if len(manifest) > profile.max_tools:
            findings.append(
                _finding(
                    "MCP008",
                    "error",
                    f"manifest exposes {len(manifest)} tools, above profile limit {profile.max_tools}",
                    source=manifest.source,
                    path="tools",
                )
            )
    for tool in tools:
        findings.extend(_analyze_tool(tool, profile))
    findings.extend(_collision_checks(tools))
    if baseline is not None:
        findings.extend(analyze_drift(baseline, tools))
    return sorted(
        findings,
        key=lambda item: (
            item.source,
            item.tool,
            item.path,
            item.rule_id,
            item.message,
        ),
    )


def _schema_facts(schema: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], set[str]]:
    properties: dict[str, dict[str, Any]] = {}
    required: set[str] = set()

    def walk(node: Any, prefix: str) -> None:
        if not isinstance(node, dict):
            return
        members = node.get("properties")
        if isinstance(members, dict):
            for name, subschema in members.items():
                path = f"{prefix}.{name}" if prefix else name
                if isinstance(subschema, dict):
                    enum = None
                    if isinstance(subschema.get("enum"), list):
                        enum = frozenset(canonical_json(item) for item in subschema["enum"])
                    properties[path] = {
                        "type": canonical_json(subschema.get("type")),
                        "enum": enum,
                        "default": (
                            canonical_json(subschema["default"]) if "default" in subschema else None
                        ),
                        "description": str(subschema.get("description", "") or ""),
                    }
                    walk(subschema, path)
        declared_required = node.get("required")
        if isinstance(declared_required, list):
            for name in declared_required:
                if isinstance(name, str):
                    required.add(f"{prefix}.{name}" if prefix else name)

    walk(schema, "")
    return properties, required


def analyze_drift(baseline: Manifest, current_tools: list[Tool]) -> list[Finding]:
    old_tools = {tool.name: tool for tool in baseline.tools}
    new_tools: dict[str, list[Tool]] = {}
    for tool in current_tools:
        new_tools.setdefault(tool.name, []).append(tool)
    findings: list[Finding] = []

    def drift(
        severity: str,
        message: str,
        tool: Tool,
        path: str,
    ) -> None:
        findings.append(
            _finding(
                "MCP011",
                severity,
                message,
                source=tool.source,
                tool=tool.name,
                path=path,
            )
        )

    for name, old_tool in sorted(old_tools.items()):
        if name not in new_tools:
            findings.append(
                _finding(
                    "MCP011",
                    "error",
                    f"tool '{name}' from the published baseline was removed",
                    source=baseline.source,
                    tool=name,
                    path="tools",
                )
            )
            continue
        for tool in new_tools[name]:
            old_props, old_required = _schema_facts(old_tool.input_schema)
            new_props, new_required = _schema_facts(tool.input_schema)

            for path in sorted(old_required - new_required):
                drift("error", f"parameter '{path}' is no longer required", tool, f"inputSchema.{path}")
            for path in sorted(new_required - old_required):
                drift("error", f"parameter '{path}' became required", tool, f"inputSchema.{path}")
            for path in sorted(set(old_props) - set(new_props)):
                drift("error", f"parameter '{path}' was removed", tool, f"inputSchema.{path}")
            for path in sorted(set(new_props) - set(old_props)):
                drift("note", f"parameter '{path}' was added", tool, f"inputSchema.{path}")
            for path in sorted(set(old_props) & set(new_props)):
                old_fact = old_props[path]
                new_fact = new_props[path]
                base_path = f"inputSchema.properties.{path}"
                if old_fact["type"] != new_fact["type"]:
                    drift(
                        "error",
                        f"parameter '{path}' type changed from {old_fact['type']} to {new_fact['type']}",
                        tool,
                        base_path,
                    )
                old_enum = old_fact["enum"]
                new_enum = new_fact["enum"]
                if old_enum and new_enum and old_enum != new_enum:
                    if new_enum < old_enum:
                        drift("error", f"parameter '{path}' enum was narrowed", tool, base_path)
                    else:
                        drift("warning", f"parameter '{path}' enum was widened", tool, base_path)
                if old_fact["default"] != new_fact["default"]:
                    drift("warning", f"parameter '{path}' default value changed", tool, base_path)
                if old_fact["description"] and not new_fact["description"]:
                    drift("warning", f"parameter '{path}' lost its description", tool, base_path)

            old_annotations = old_tool.annotations
            new_annotations = tool.annotations
            for key in ("readOnlyHint", "destructiveHint"):
                if key in old_annotations and key in new_annotations:
                    if old_annotations[key] != new_annotations[key]:
                        severity = "error" if new_annotations[key] is True else "warning"
                        drift(
                            severity,
                            f"annotation '{key}' changed from {old_annotations[key]} to {new_annotations[key]}",
                            tool,
                            f"annotations.{key}",
                        )
            if old_tool.output_schema is not None and tool.output_schema is None:
                drift("warning", "structured outputSchema was removed", tool, "outputSchema")
            if len(old_tool.description) >= 12 and len(tool.description.strip()) < 12:
                drift("warning", "tool description was materially shortened", tool, "description")

    for name, tools in sorted(new_tools.items()):
        if name in old_tools:
            continue
        for tool in tools:
            drift("note", f"tool '{name}' was added to the contract", tool, "name")
    return findings
