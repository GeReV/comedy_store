from __future__ import annotations
import json
from pathlib import Path
import pytest
from scripts.player.character_registry import CharacterRegistry


def test_empty_registry(tmp_path: Path):
    reg = CharacterRegistry(tmp_path / "chars.json")
    assert reg.all == []
    assert reg.suggest("") == []


def test_add_and_suggest_prefix(tmp_path: Path):
    reg = CharacterRegistry(tmp_path / "chars.json")
    reg.add("Avi Kushnir")
    reg.add("Dana Modan")
    assert reg.suggest("Av") == ["Avi Kushnir"]
    assert reg.suggest("Da") == ["Dana Modan"]
    assert len(reg.suggest("")) == 2


def test_suggest_case_insensitive(tmp_path: Path):
    reg = CharacterRegistry(tmp_path / "chars.json")
    reg.add("Avi Kushnir")
    assert reg.suggest("avi") == ["Avi Kushnir"]
    assert reg.suggest("AVI") == ["Avi Kushnir"]


def test_add_persists_to_disk(tmp_path: Path):
    path = tmp_path / "chars.json"
    reg = CharacterRegistry(path)
    reg.add("Avi Kushnir")
    reg2 = CharacterRegistry(path)
    assert "Avi Kushnir" in reg2.all


def test_add_deduplicates(tmp_path: Path):
    reg = CharacterRegistry(tmp_path / "chars.json")
    reg.add("Avi Kushnir")
    reg.add("Avi Kushnir")
    assert reg.all.count("Avi Kushnir") == 1


def test_all_returns_sorted(tmp_path: Path):
    reg = CharacterRegistry(tmp_path / "chars.json")
    reg.add("Ziva")
    reg.add("Avi Kushnir")
    reg.add("Moni")
    assert reg.all == sorted(["Ziva", "Avi Kushnir", "Moni"])


def test_load_missing_file(tmp_path: Path):
    reg = CharacterRegistry(tmp_path / "nonexistent.json")
    assert reg.all == []


def test_load_corrupt_file(tmp_path: Path):
    path = tmp_path / "chars.json"
    path.write_text("NOT JSON", encoding="utf-8")
    reg = CharacterRegistry(path)
    assert reg.all == []
