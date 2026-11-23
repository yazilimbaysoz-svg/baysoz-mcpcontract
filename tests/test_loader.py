# SPDX-License-Identifier: MIT
# Baysöz Labs <baysozlabs@proton.me>

"""Loader behaviour tests."""

from __future__ import annotations

import json

import pytest

from baysoz_mcpcontract.loader import canonical_json, load_manifests, merge_manifests


def test_loads_tools_list_wrapper(clean_manifest: str) -> None:
    manifests = load_manifests([clean_manifest])
    assert len(manifests) == 1
    assert manifests[0].server_name == "clean-reference-server"
    assert [tool.name for tool in manifests[0].tools] == ["get_status", "delete_cache"]
    assert manifests[0].tools[0].annotations["readOnlyHint"] is True


def test_loads_jsonl_and_directory(tmp_path, clean_manifest: str) -> None:
    source = json.loads(open(clean_manifest, encoding="utf-8").read())
    jsonl = tmp_path / "stream.jsonl"
    jsonl.write_text(
        "\n".join(canonical_json({"tools": [tool]}) for tool in source["tools"]) + "\n",
        encoding="utf-8",
    )
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "copy.json").write_text(json.dumps(source), encoding="utf-8")
    manifests = load_manifests([tmp_path])
    assert len(manifests) == 2
    assert sum(len(manifest) for manifest in manifests) == 4


def test_merge_manifests_uses_explicit_source(clean_manifest: str) -> None:
    merged = merge_manifests(load_manifests([clean_manifest]), source="published-baseline")
    assert merged.source == "published-baseline"
    assert len(merged) == 2


def test_rejects_unknown_document(tmp_path) -> None:
    path = tmp_path / "unknown.json"
    path.write_text('{"unexpected": true}', encoding="utf-8")
    with pytest.raises(ValueError, match="no tools array"):
        load_manifests([str(path)])


def test_rejects_malformed_json(tmp_path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_manifests([str(path)])
