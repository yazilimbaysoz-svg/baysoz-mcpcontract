# SPDX-License-Identifier: MIT
# Baysöz Labs <baysozlabs@proton.me>

"""Core data model for Baysöz Labs MCP contract analysis."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
import re
from typing import Any

Severity = str


class Level(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"


@dataclass(frozen=True, slots=True)
class Profile:
    name: str
    description: str
    max_tools: int
    max_schema_bytes: int
    max_properties: int
    max_depth: int
    max_token_estimate: int
    min_description_coverage: float
    supported_features: frozenset[str]
    allowed_formats: frozenset[str]
    require_annotations: bool
    require_output_schema_for_mutating: bool
    reject_untyped_items: bool


@dataclass(frozen=True, slots=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None
    annotations: dict[str, Any]
    source: str
    raw: dict[str, Any] = field(default_factory=dict, compare=False)

    @property
    def canonical_name(self) -> str:
        normalized = "".join(ch for ch in self.name.lower() if ch.isalnum())
        return normalized

    @property
    def is_mutating(self) -> bool:
        text = f"{self.name} {self.description[:240]}"
        return not READ_SAFETY.search(text) and bool(MUTATING_VERBS.search(text.lower()))

    @property
    def is_high_risk(self) -> bool:
        text = f"{self.name} {self.description[:240]}"
        return not READ_SAFETY.search(text) and bool(HIGH_RISK_VERBS.search(text.lower()))

    @property
    def is_read_named(self) -> bool:
        return bool(READ_VERBS.search(f"{self.name} {self.description[:240]}".lower()))


@dataclass(frozen=True, slots=True)
class Manifest:
    source: str
    tools: tuple[Tool, ...]
    server_name: str = ""

    def __len__(self) -> int:
        return len(self.tools)


@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str
    severity: Severity
    message: str
    source: str
    tool: str = ""
    path: str = ""
    remediation: str = ""
    fingerprint: str = ""

    def with_fingerprint(self) -> Finding:
        import hashlib
        import json

        material = json.dumps(
            [self.rule_id, self.severity, self.source, self.tool, self.path, self.message],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
        return replace(self, fingerprint=digest)


@dataclass(frozen=True, slots=True)
class SchemaIssue:
    code: str
    severity: Severity
    message: str
    path: str


MUTATING_VERBS = re.compile(
    r"\b(create|add|insert|write|update|modify|patch|set|delete|remove|drop|purge|"
    r"truncate|kill|terminate|exec|execute|run|shell|apply|deploy|push|commit|"
    r"restart|start|stop|reset|rollback|scale|rename|move|install|uninstall|"
    r"configure|provision|migrate)\b"
)
HIGH_RISK_VERBS = re.compile(
    r"\b(delete|remove|drop|purge|truncate|kill|terminate|exec|execute|run|shell|"
    r"apply|push|reset|rollback|write|update|patch|deploy|provision|migrate)\b"
)
READ_VERBS = re.compile(
    r"\b(get|list|read|describe|show|status|inspect|query|fetch|search|find|diff|"
    r"check|validate|verify|explain|measure|stats|audit)\b"
)
READ_SAFETY = re.compile(
    r"(read[- ]?only|non[- ]?mutating|select only|dry run|no side effects|idempotent read)",
    re.IGNORECASE,
)
SECRET_NAMES = re.compile(
    r"(password|passwd|secret|token|api[_.-]?key|credential|authorization|"
    r"private[_.-]?key|access[_.-]?key|session[_.-]?key)",
    re.IGNORECASE,
)
COMMAND_NAMES = re.compile(r"(command|cmd|script|shell|payload|argv|args|query)", re.IGNORECASE)
PATH_NAMES = re.compile(r"(path|file|dir|folder|url|uri|target|location)", re.IGNORECASE)
