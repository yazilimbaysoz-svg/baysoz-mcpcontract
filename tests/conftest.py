# SPDX-License-Identifier: MIT
# Baysöz Labs <baysozlabs@proton.me>

"""Shared fixtures for Baysöz Labs MCP contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def clean_manifest() -> str:
    return str(FIXTURES / "tools_clean.json")


@pytest.fixture
def unsafe_manifest() -> str:
    return str(FIXTURES / "tools_unsafe.json")


@pytest.fixture
def collision_manifest() -> str:
    return str(FIXTURES / "tools_unsafe_collision.json")


@pytest.fixture
def baseline_manifest() -> str:
    return str(FIXTURES / "tools_baseline.json")
