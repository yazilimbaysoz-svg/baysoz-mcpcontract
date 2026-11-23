# SPDX-License-Identifier: MIT
# Baysöz Labs <baysozlabs@proton.me>

"""Input loading for MCP tools/list exports and standalone tool manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import Manifest, Tool

TOOL_LIST_KEYS = ("tools",)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _as_tool(record: Any, source: str) -> Tool:
    if not isinstance(record, dict):
        raise ValueError(f"{source}: tool record must be a JSON object")
    raw_schema = record.get("inputSchema")
    raw_output = record.get("outputSchema")
    annotations = record.get("annotations")
    return Tool(
        name=str(record.get("name", "") or ""),
        description=str(record.get("description", "") or ""),
        input_schema=dict(raw_schema) if isinstance(raw_schema, dict) else {},
        output_schema=dict(raw_output) if isinstance(raw_output, dict) else None,
        annotations=dict(annotations) if isinstance(annotations, dict) else {},
        source=source,
        raw=record,
    )


def _records_from_document(document: Any, source: str) -> tuple[list[dict[str, Any]], str]:
    if isinstance(document, list):
        return [record for record in document if isinstance(record, dict)], ""
    if not isinstance(document, dict):
        raise ValueError(f"{source}: expected a JSON object, array or JSON Lines stream")
    if isinstance(document.get("result"), dict) and "tools" in document["result"]:
        document = document["result"]
    for key in TOOL_LIST_KEYS:
        if key in document:
            values = document[key]
            if not isinstance(values, list):
                raise ValueError(f"{source}: {key} must be an array")
            server_info = document.get("serverInfo")
            server_name = ""
            if isinstance(server_info, dict):
                server_name = str(server_info.get("name", "") or "")
            return [record for record in values if isinstance(record, dict)], server_name
    if "name" in document or "inputSchema" in document:
        return [document], ""
    raise ValueError(f"{source}: no tools array or standalone tool object found")


def _files_from_path(path: Path) -> list[Path]:
    if path.is_dir():
        candidates = sorted({*path.rglob("*.json"), *path.rglob("*.jsonl")})
        if not candidates:
            raise ValueError(f"{path}: directory contains no .json or .jsonl files")
        return candidates
    if path.is_file():
        return [path]
    raise ValueError(f"{path}: path does not exist")


def load_manifests(paths: list[str] | list[Path]) -> list[Manifest]:
    manifests: list[Manifest] = []
    seen: set[Path] = set()
    for raw_path in paths:
        for path in _files_from_path(Path(raw_path)):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if path.suffix == ".jsonl":
                tools: list[Tool] = []
                with path.open(encoding="utf-8") as handle:
                    for line_number, line in enumerate(handle, start=1):
                        if not line.strip():
                            continue
                        try:
                            document = json.loads(line)
                        except json.JSONDecodeError as exc:
                            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
                        records, _ = _records_from_document(document, f"{path}:{line_number}")
                        tools.extend(
                            _as_tool(record, f"{path}:{line_number}") for record in records
                        )
                manifests.append(Manifest(source=str(path), tools=tuple(tools)))
                continue
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}: invalid JSON: {exc.msg} at line {exc.lineno}") from exc
            records, server_name = _records_from_document(document, str(path))
            manifests.append(
                Manifest(
                    source=str(path),
                    tools=tuple(_as_tool(record, str(path)) for record in records),
                    server_name=server_name,
                )
            )
    if not manifests:
        raise ValueError("no input manifests provided")
    return manifests


def merge_manifests(manifests: list[Manifest], source: str = "baseline") -> Manifest:
    tools = [tool for manifest in manifests for tool in manifest.tools]
    return Manifest(source=source, tools=tuple(tools))
