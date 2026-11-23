# SPDX-License-Identifier: MIT
# Baysöz Labs <baysozlabs@proton.me>

"""Recursive JSON Schema auditing used by the MCP contract oracle."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any

from .model import PATH_NAMES, SECRET_NAMES, Profile, SchemaIssue

PRIMITIVES = frozenset({"object", "array", "string", "number", "integer", "boolean", "null"})
MISSING = object()


@dataclass(frozen=True, slots=True)
class SchemaAudit:
    issues: tuple[SchemaIssue, ...]
    byte_size: int
    token_estimate: int
    property_count: int
    description_coverage: float
    max_depth: int


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _matches_type(value: Any, declared: str) -> bool:
    if declared == "object":
        return isinstance(value, dict)
    if declared == "array":
        return isinstance(value, list)
    if declared == "string":
        return isinstance(value, str)
    if declared == "boolean":
        return isinstance(value, bool)
    if declared == "null":
        return value is None
    if declared == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if declared == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return True


def _resolve_pointer(root: Any, ref: str) -> tuple[bool, Any, str]:
    if not ref.startswith("#/"):
        return False, MISSING, ref
    tokens = [token.replace("~1", "/").replace("~0", "~") for token in ref[2:].split("/")]
    node: Any = root
    for token in tokens:
        if isinstance(node, dict) and token in node:
            node = node[token]
            continue
        if isinstance(node, list) and token.isdigit() and int(token) < len(node):
            node = node[int(token)]
            continue
        return False, MISSING, ref
    return True, node, ref


def audit_schema(
    schema: dict[str, Any],
    profile: Profile,
    base_path: str = "inputSchema",
    *,
    is_output: bool = False,
) -> SchemaAudit:
    issues: list[SchemaIssue] = []
    total_properties = 0
    described_properties = 0
    max_depth_seen = 0

    def add(code: str, severity: str, message: str, path: str) -> None:
        issues.append(SchemaIssue(code=code, severity=severity, message=message, path=path))

    def check_feature(feature: str, path: str) -> None:
        if feature not in profile.supported_features:
            add(
                "MCP003",
                "error",
                f"schema construct '{feature}' is not portable to profile {profile.name}",
                path,
            )

    def walk(
        node: Any,
        pointer: str,
        depth: int,
        active_refs: frozenset[str],
        property_name: str = "",
    ) -> None:
        nonlocal total_properties, described_properties, max_depth_seen
        max_depth_seen = max(max_depth_seen, depth)
        if depth > profile.max_depth:
            add(
                "MCP008",
                "error",
                f"schema nesting depth {depth} exceeds profile limit {profile.max_depth}",
                pointer,
            )
            return
        if not isinstance(node, dict):
            add("MCP002", "error", "subschema must be a JSON object", pointer)
            return

        if property_name:
            total_properties += 1
            description = node.get("description")
            if isinstance(description, str) and description.strip():
                described_properties += 1
            if SECRET_NAMES.search(property_name):
                if is_output:
                    add(
                        "MCP006",
                        "error",
                        f"secret-like property '{property_name}' is exposed in the output schema",
                        pointer,
                    )
                elif node.get("writeOnly") is not True and node.get("format") != "password":
                    add(
                        "MCP006",
                        "warning",
                        f"secret-like property '{property_name}' lacks writeOnly or format=password",
                        pointer,
                    )
            if PATH_NAMES.search(property_name) and node.get("type") == "string":
                constrained = any(key in node for key in ("pattern", "enum", "const", "maxLength"))
                if not constrained:
                    add(
                        "MCP007",
                        "warning",
                        f"path-like property '{property_name}' has no containment constraint",
                        pointer,
                    )

        declared_type = node.get("type")
        if declared_type is not None:
            types = declared_type if isinstance(declared_type, list) else [declared_type]
            if not all(isinstance(item, str) and item in PRIMITIVES for item in types):
                add("MCP002", "error", "type must use JSON Schema primitive names", f"{pointer}.type")
            elif len(types) > 1:
                add(
                    "MCP002",
                    "error",
                    "type unions are ambiguous across MCP clients; use anyOf in a compatible profile",
                    f"{pointer}.type",
                )
            if "array" in types and "items" not in node:
                add("MCP002", "error", "array schema is missing an items declaration", pointer)

        if "$ref" in node:
            check_feature("$ref", f"{pointer}.$ref")
            ref = node["$ref"]
            if not isinstance(ref, str) or not ref.startswith("#/"):
                add("MCP013", "error", "$ref must be a local JSON pointer starting with #/", pointer)
            else:
                found, target, target_pointer = _resolve_pointer(schema, ref)
                if not found:
                    add("MCP013", "error", f"unresolved $ref target '{ref}'", pointer)
                elif target_pointer in active_refs:
                    add("MCP013", "error", f"recursive $ref cycle through '{ref}'", pointer)
                elif target_pointer not in expanded_refs:
                    expanded_refs.add(target_pointer)
                    walk(
                        target,
                        f"{pointer}->{ref}",
                        depth + 1,
                        active_refs | {target_pointer},
                        property_name,
                    )

        for key in ("$defs", "definitions"):
            if key in node:
                check_feature("$defs", f"{pointer}.{key}")
                definitions = node[key]
                if not isinstance(definitions, dict):
                    add("MCP002", "error", f"{key} must be an object", f"{pointer}.{key}")
                else:
                    for name, subschema in definitions.items():
                        local_pointer = f"#/{key}/{name}"
                        walk(
                            subschema,
                            f"{pointer}.{key}.{name}",
                            depth + 1,
                            active_refs | {local_pointer},
                        )

        for key in ("anyOf", "oneOf", "allOf"):
            if key in node:
                check_feature(key, f"{pointer}.{key}")
                branches = node[key]
                if not isinstance(branches, list) or not branches:
                    add("MCP002", "error", f"{key} must be a non-empty array", f"{pointer}.{key}")
                else:
                    signatures: list[str] = []
                    for index, subschema in enumerate(branches):
                        walk(subschema, f"{pointer}.{key}[{index}]", depth + 1, active_refs)
                        if isinstance(subschema, dict) and "const" in subschema:
                            signatures.append(canonical_json(subschema["const"]))
                    if key == "oneOf" and signatures and len(set(signatures)) != len(signatures):
                        add(
                            "MCP002",
                            "error",
                            "oneOf branches contain duplicate const values and can never be exclusive",
                            f"{pointer}.{key}",
                        )

        if any(key in node for key in ("if", "then", "else")):
            check_feature("if/then/else", pointer)
            for key in ("if", "then", "else"):
                if key in node:
                    walk(node[key], f"{pointer}.{key}", depth + 1, active_refs)
        if "patternProperties" in node:
            check_feature("patternProperties", f"{pointer}.patternProperties")
            value = node["patternProperties"]
            if isinstance(value, dict):
                for name, subschema in value.items():
                    walk(subschema, f"{pointer}.patternProperties[{name}]", depth + 1, active_refs)
        if "dependentSchemas" in node:
            check_feature("dependentSchemas", f"{pointer}.dependentSchemas")
            value = node["dependentSchemas"]
            if isinstance(value, dict):
                for name, subschema in value.items():
                    walk(subschema, f"{pointer}.dependentSchemas[{name}]", depth + 1, active_refs)
        for key in ("contains", "propertyNames", "not", "if", "then", "else"):
            if key in node and key not in ("if", "then", "else"):
                if key == "contains":
                    check_feature("contains", f"{pointer}.{key}")
                walk(node[key], f"{pointer}.{key}", depth + 1, active_refs)
        if "prefixItems" in node:
            check_feature("prefixItems", f"{pointer}.prefixItems")
            value = node["prefixItems"]
            if isinstance(value, list):
                for index, subschema in enumerate(value):
                    walk(subschema, f"{pointer}.prefixItems[{index}]", depth + 1, active_refs)

        properties = node.get("properties")
        if properties is not None:
            if not isinstance(properties, dict):
                add("MCP002", "error", "properties must be an object", f"{pointer}.properties")
            else:
                for name, subschema in properties.items():
                    walk(subschema, f"{pointer}.properties[{name}]", depth + 1, active_refs, str(name))

        if "required" in node:
            required = node["required"]
            if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
                add("MCP002", "error", "required must be an array of strings", f"{pointer}.required")
            else:
                duplicates = {item for item in required if required.count(item) > 1}
                if duplicates:
                    add(
                        "MCP002",
                        "error",
                        f"duplicate required entries: {', '.join(sorted(duplicates))}",
                        f"{pointer}.required",
                    )
                if isinstance(properties, dict):
                    missing = [item for item in required if item not in properties]
                    if missing:
                        add(
                            "MCP002",
                            "error",
                            f"required properties not declared: {', '.join(missing)}",
                            f"{pointer}.required",
                        )

        if "items" in node:
            items = node["items"]
            if isinstance(items, dict):
                walk(items, f"{pointer}.items", depth + 1, active_refs)
                structural = any(
                    key in items
                    for key in ("type", "$ref", "enum", "const", "anyOf", "oneOf", "allOf")
                )
                if profile.reject_untyped_items and not structural:
                    add(
                        "MCP002",
                        "error",
                        "array items have no type or composition keyword",
                        f"{pointer}.items",
                    )
            elif not isinstance(items, bool):
                add("MCP002", "error", "items must be an object or boolean", f"{pointer}.items")

        if "additionalProperties" in node and not isinstance(
            node["additionalProperties"], (bool, dict)
        ):
            add(
                "MCP002",
                "error",
                "additionalProperties must be a boolean or schema object",
                f"{pointer}.additionalProperties",
            )

        if "enum" in node:
            values = node["enum"]
            if not isinstance(values, list) or not values:
                add("MCP002", "error", "enum must be a non-empty array", f"{pointer}.enum")
            else:
                serialized = [canonical_json(value) for value in values]
                if len(serialized) != len(set(serialized)):
                    add("MCP002", "error", "enum contains duplicate values", f"{pointer}.enum")
                if "default" in node and canonical_json(node["default"]) not in serialized:
                    add(
                        "MCP002",
                        "error",
                        "default value is not a member of enum",
                        f"{pointer}.default",
                    )

        if "default" in node and isinstance(declared_type, str):
            if not _matches_type(node["default"], declared_type):
                add(
                    "MCP002",
                    "error",
                    "default value does not match the declared type",
                    f"{pointer}.default",
                )

        if "pattern" in node:
            pattern = node["pattern"]
            if not isinstance(pattern, str):
                add("MCP002", "error", "pattern must be a string", f"{pointer}.pattern")
            else:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    add(
                        "MCP002",
                        "error",
                        f"invalid regular expression: {exc.msg}",
                        f"{pointer}.pattern",
                    )

        if "format" in node:
            fmt = node["format"]
            if not isinstance(fmt, str):
                add("MCP002", "error", "format must be a string", f"{pointer}.format")
            elif fmt not in profile.allowed_formats:
                add(
                    "MCP002",
                    "warning",
                    f"format '{fmt}' has no portable meaning in profile {profile.name}",
                    f"{pointer}.format",
                )

        for lower, upper in (("minLength", "maxLength"), ("minimum", "maximum")):
            low = node.get(lower)
            high = node.get(upper)
            for key, value in ((lower, low), (upper, high)):
                if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
                    add("MCP002", "error", f"{key} must be numeric", f"{pointer}.{key}")
            if (
                isinstance(low, (int, float))
                and isinstance(high, (int, float))
                and not isinstance(low, bool)
                and not isinstance(high, bool)
                and low > high
            ):
                add(
                    "MCP002",
                    "error",
                    f"{lower} must not exceed {upper}",
                    pointer,
                )

    expanded_refs: set[str] = set()
    walk(schema, base_path, 0, frozenset())
    byte_size = len(canonical_json(schema).encode("utf-8"))
    token_estimate = math.ceil(byte_size / 4)
    coverage = 1.0 if total_properties == 0 else described_properties / total_properties

    if total_properties > profile.max_properties:
        add_issue = SchemaIssue(
            code="MCP008",
            severity="error",
            message=(
                f"property count {total_properties} exceeds profile limit {profile.max_properties}"
            ),
            path=base_path,
        )
        issues.append(add_issue)
    if coverage + 1e-12 < profile.min_description_coverage:
        issues.append(
            SchemaIssue(
                code="MCP004",
                severity="warning",
                message=(
                    f"property description coverage {coverage:.0%} is below required "
                    f"{profile.min_description_coverage:.0%} ({described_properties}/{total_properties})"
                ),
                path=base_path,
            )
        )
    if byte_size > profile.max_schema_bytes or token_estimate > profile.max_token_estimate:
        issues.append(
            SchemaIssue(
                code="MCP008",
                severity="warning",
                message=(
                    f"schema cost {byte_size} bytes / ~{token_estimate} tokens exceeds profile "
                    f"budget {profile.max_schema_bytes} bytes / ~{profile.max_token_estimate} tokens"
                ),
                path=base_path,
            )
        )

    return SchemaAudit(
        issues=tuple(issues),
        byte_size=byte_size,
        token_estimate=token_estimate,
        property_count=total_properties,
        description_coverage=coverage,
        max_depth=max_depth_seen,
    )
