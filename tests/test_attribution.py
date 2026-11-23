# SPDX-License-Identifier: MIT
# Baysöz Labs <baysozlabs@proton.me>

"""Repository-wide attribution and naming policy checks."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "build"}
TEXT_SUFFIXES = {".py", ".md", ".toml", ".yml", ".yaml", ".json", ".jsonl"}
SPECIAL_FILES = {"LICENSE", ".gitignore"}
FORBIDDEN_SUFFIXES = (
    "Hold" + "ing",
    "Cor" + "p.",
    "Cor" + "poration",
    "Incor" + "porated",
    "A." + "Ş.",
    "In" + "c.",
)


def _public_files() -> list[Path]:
    files = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or EXCLUDED_DIRS.intersection(path.parts):
            continue
        if path.suffix in TEXT_SUFFIXES or path.name in SPECIAL_FILES:
            files.append(path)
    return files


def test_public_files_exist() -> None:
    assert len(_public_files()) >= 20


def test_every_public_file_attributes_baysoz_labs() -> None:
    for path in _public_files():
        text = path.read_text(encoding="utf-8")
        assert "Baysöz Labs" in text, f"{path.name} lacks Baysöz Labs attribution"
        assert "baysozlabs@proton.me" in text, f"{path.name} lacks contact email"


def test_no_legal_entity_suffixes() -> None:
    for path in _public_files():
        text = path.read_text(encoding="utf-8")
        for suffix in FORBIDDEN_SUFFIXES:
            assert suffix not in text, f"{path.name} contains forbidden suffix {suffix}"
