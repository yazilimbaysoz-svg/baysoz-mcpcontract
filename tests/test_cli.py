# SPDX-License-Identifier: MIT
# Baysöz Labs <baysozlabs@proton.me>

"""End-to-end CLI tests."""

from __future__ import annotations

import json

import pytest

from baysoz_mcpcontract import __attribution__
from baysoz_mcpcontract.cli import main


def test_help_and_version_carry_attribution(capsys) -> None:
    with pytest.raises(SystemExit) as help_exit:
        main(["--help"])
    assert help_exit.value.code == 0
    assert __attribution__ in capsys.readouterr().out

    with pytest.raises(SystemExit) as version_exit:
        main(["--version"])
    assert version_exit.value.code == 0
    assert __attribution__ in capsys.readouterr().out


def test_check_clean_json_gate(clean_manifest: str, capsys) -> None:
    code = main(
        ["check", clean_manifest, "--profile", "enterprise-strict", "--format", "json"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["summary"]["total"] == 0
    assert payload["attribution"] == __attribution__


def test_check_unsafe_sarif_gate(unsafe_manifest: str, capsys) -> None:
    code = main(["check", unsafe_manifest, "--format", "sarif"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["version"] == "2.1.0"
    assert payload["runs"][0]["properties"]["summary"]["error"] > 0


def test_fail_on_never_returns_zero(unsafe_manifest: str, capsys) -> None:
    code = main(["check", unsafe_manifest, "--fail-on", "never", "--format", "text"])
    assert code == 0
    assert __attribution__ in capsys.readouterr().out


def test_rules_and_profiles_outputs(capsys) -> None:
    assert main(["rules", "--rule", "MCP005"]) == 0
    assert "destructiveHint" in capsys.readouterr().out
    assert main(["profiles", "--name", "enterprise-strict"]) == 0
    assert "enterprise-strict" in capsys.readouterr().out


def test_normalize_is_canonical(clean_manifest: str, tmp_path, capsys) -> None:
    output = tmp_path / "normalized.json"
    assert main(["normalize", clean_manifest, "--output", str(output)]) == 0
    first = output.read_text(encoding="utf-8")
    assert main(["normalize", clean_manifest]) == 0
    assert capsys.readouterr().out == first
    payload = json.loads(first)
    assert payload["attribution"] == __attribution__
    assert list(payload["tools"][0]["name"]) == list("get_status")


def test_invalid_profile_is_usage_error(clean_manifest: str, capsys) -> None:
    code = main(["check", clean_manifest, "--profile", "missing"])
    assert code == 2
    assert "unknown profile" in capsys.readouterr().err
