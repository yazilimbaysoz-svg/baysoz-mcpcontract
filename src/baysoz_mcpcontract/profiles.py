# SPDX-License-Identifier: MIT
# Baysöz Labs <baysozlabs@proton.me>

"""Portability profiles and deterministic rule catalogue."""

from __future__ import annotations

from dataclasses import dataclass

from .model import Profile

BASE_FEATURES = frozenset(
    {
        "type",
        "enum",
        "const",
        "pattern",
        "format",
        "minimum",
        "maximum",
        "minLength",
        "maxLength",
    }
)
RICH_FEATURES = frozenset({"$ref", "$defs", "anyOf", "oneOf", "allOf", "format"})
FULL_FEATURES = frozenset(
    {
        *RICH_FEATURES,
        "if/then/else",
        "patternProperties",
        "dependentSchemas",
        "contains",
        "prefixItems",
    }
)
COMMON_FORMATS = frozenset({"date-time", "date", "uri", "email", "uuid", "hostname", "ipv4", "ipv6"})

PROFILES: dict[str, Profile] = {
    "mcp-2025-06-18": Profile(
        name="mcp-2025-06-18",
        description="Baseline MCP tools/list contract with full JSON Schema composition support.",
        max_tools=64,
        max_schema_bytes=24000,
        max_properties=60,
        max_depth=10,
        max_token_estimate=12000,
        min_description_coverage=0.75,
        supported_features=FULL_FEATURES,
        allowed_formats=COMMON_FORMATS | frozenset({"password", "duration", "path"}),
        require_annotations=False,
        require_output_schema_for_mutating=False,
        reject_untyped_items=True,
    ),
    "claude-code-2026": Profile(
        name="claude-code-2026",
        description=(
            "Portability profile for clients that flatten tool schemas and drop $ref/$defs/"
            "anyOf/oneOf, motivated by anthropics/claude-code issue 111857."
        ),
        max_tools=48,
        max_schema_bytes=16000,
        max_properties=48,
        max_depth=8,
        max_token_estimate=8000,
        min_description_coverage=0.85,
        supported_features=BASE_FEATURES | frozenset({"allOf"}),
        allowed_formats=COMMON_FORMATS | frozenset({"password"}),
        require_annotations=True,
        require_output_schema_for_mutating=False,
        reject_untyped_items=True,
    ),
    "gemini-antigravity-2026": Profile(
        name="gemini-antigravity-2026",
        description=(
            "Portability profile with strict typing for array items and compact tool payloads, "
            "motivated by gnoviawan/troupe issue 1981 and Antigravity schema-limit reports."
        ),
        max_tools=40,
        max_schema_bytes=12000,
        max_properties=40,
        max_depth=7,
        max_token_estimate=6000,
        min_description_coverage=0.85,
        supported_features=BASE_FEATURES,
        allowed_formats=COMMON_FORMATS,
        require_annotations=True,
        require_output_schema_for_mutating=False,
        reject_untyped_items=True,
    ),
    "enterprise-strict": Profile(
        name="enterprise-strict",
        description=(
            "Highest-assurance production profile: flat schemas, complete descriptions, "
            "explicit annotations and structured outputs for mutating tools."
        ),
        max_tools=32,
        max_schema_bytes=8000,
        max_properties=32,
        max_depth=6,
        max_token_estimate=4000,
        min_description_coverage=1.0,
        supported_features=BASE_FEATURES,
        allowed_formats=COMMON_FORMATS | frozenset({"password"}),
        require_annotations=True,
        require_output_schema_for_mutating=True,
        reject_untyped_items=True,
    ),
}

DEFAULT_PROFILE = "mcp-2025-06-18"


@dataclass(frozen=True, slots=True)
class Rule:
    rule_id: str
    name: str
    default_severity: str
    remediation: str
    rationale: str
    references: tuple[str, ...] = ()


RULES: dict[str, Rule] = {
    rule.rule_id: rule
    for rule in (
        Rule(
            "MCP001",
            "ToolStructure",
            "error",
            "Provide a non-empty name, description and object-shaped inputSchema for every tool.",
            "A tool without a valid contract cannot be safely advertised to an agent runtime.",
        ),
        Rule(
            "MCP002",
            "SchemaInvalid",
            "error",
            "Correct schema keyword types, required members, enum/default values and regex patterns.",
            "Malformed JSON Schema is interpreted differently by every client and can cause silent "
            "argument coercion.",
        ),
        Rule(
            "MCP003",
            "UnsupportedFeature",
            "error",
            "Inline or flatten the construct, or select a profile that supports it.",
            "Several 2026 clients strip composition keywords from tool schemas before model exposure.",
            ("https://github.com/anthropics/claude-code/issues/111857",),
        ),
        Rule(
            "MCP004",
            "DocumentationGap",
            "warning",
            "Describe the tool and every property with short, behaviour-focused text.",
            "Undescribed tool properties cause incorrect agent arguments; the official MCP git server "
            "tracks this defect explicitly.",
            ("https://github.com/modelcontextprotocol/servers/issues/5647",),
        ),
        Rule(
            "MCP005",
            "AnnotationMismatch",
            "error",
            "Set annotations.destructiveHint/readOnlyHint to match the tool's actual effect.",
            "Incorrect hints let autonomous clients auto-approve dangerous operations.",
        ),
        Rule(
            "MCP006",
            "SecretSurface",
            "warning",
            "Mark secret inputs with writeOnly or format=password and never emit them in outputs.",
            "Validation errors and structured responses are common credential-leak channels.",
            ("https://github.com/modelcontextprotocol/servers/issues/5646",),
        ),
        Rule(
            "MCP007",
            "UnconstrainedPath",
            "warning",
            "Constrain path/URL properties with pattern, enum, const or a documented containment rule.",
            "Unbounded path-like inputs become file-read or SSRF primitives in agent workflows.",
        ),
        Rule(
            "MCP008",
            "SchemaBloat",
            "warning",
            "Shorten descriptions, deduplicate definitions and split oversized tool sets.",
            "Tool listings are a fixed per-session token cost for every agent call.",
            ("https://github.com/earthobservations/wetterdienst/issues/4318",),
        ),
        Rule(
            "MCP009",
            "NameCollision",
            "error",
            "Rename tools so normalized names remain unique across all registered servers.",
            "Clients that normalize separators can silently route calls to the wrong server.",
        ),
        Rule(
            "MCP010",
            "OutputContract",
            "warning",
            "Declare a structured outputSchema for mutating tools and keep secret fields out of it.",
            "Downstream tools need a stable result shape; leaked credentials violate least privilege.",
        ),
        Rule(
            "MCP011",
            "ContractDrift",
            "error",
            "Review the published baseline and gate breaking changes behind a major version bump.",
            "Silent tool removals and type changes break every agent that cached the old manifest.",
        ),
        Rule(
            "MCP012",
            "CommandSink",
            "error",
            "Replace free-form command/query inputs with enumerated operations or a validated grammar.",
            "Free-form command properties are injection sinks when combined with shell-backed tools.",
        ),
        Rule(
            "MCP013",
            "RefIntegrity",
            "error",
            "Resolve local $ref targets and remove reference cycles from tool schemas.",
            "Unresolved or recursive references produce client-specific hangs and validation bypasses.",
        ),
    )
}


def get_profile(name: str) -> Profile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        available = ", ".join(sorted(PROFILES))
        raise ValueError(f"unknown profile {name!r}; available: {available}") from exc


def rule_remediation(rule_id: str) -> str:
    rule = RULES.get(rule_id)
    return rule.remediation if rule else "Review the finding and correct the tool contract."
