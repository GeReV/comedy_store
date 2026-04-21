from __future__ import annotations

from pathlib import Path

from scripts.player.dictionary_registry import DictionaryRegistry


# Characters

def test_add_and_suggest_character_prefix(tmp_path: Path):
    reg = DictionaryRegistry(tmp_path / "dict.json")
    reg.add_character("Avi Kushnir")
    reg.add_character("Dana Modan")
    assert reg.suggest_character("Av") == ["Avi Kushnir"]
    assert reg.suggest_character("Da") == ["Dana Modan"]
    assert len(reg.suggest_character("")) == 2


def test_suggest_character_case_insensitive(tmp_path: Path):
    reg = DictionaryRegistry(tmp_path / "dict.json")
    reg.add_character("Avi Kushnir")
    assert reg.suggest_character("avi") == ["Avi Kushnir"]
    assert reg.suggest_character("AVI") == ["Avi Kushnir"]


def test_add_character_persists_to_disk(tmp_path: Path):
    path = tmp_path / "dict.json"
    reg = DictionaryRegistry(path)
    reg.add_character("Avi Kushnir")
    reg2 = DictionaryRegistry(path)
    assert "Avi Kushnir" in reg2.all_characters


def test_add_character_deduplicates(tmp_path: Path):
    reg = DictionaryRegistry(tmp_path / "dict.json")
    reg.add_character("Avi Kushnir")
    reg.add_character("Avi Kushnir")
    assert reg.all_characters.count("Avi Kushnir") == 1


def test_all_characters_returns_sorted(tmp_path: Path):
    reg = DictionaryRegistry(tmp_path / "dict.json")
    reg.add_character("Ziva")
    reg.add_character("Avi Kushnir")
    reg.add_character("Moni")
    assert reg.all_characters == sorted(["Ziva", "Avi Kushnir", "Moni"])


# Titles

def test_add_and_suggest_title_prefix(tmp_path: Path):
    reg = DictionaryRegistry(tmp_path / "dict.json")
    reg.add_title("First Title")
    reg.add_title("Second Title")
    assert reg.suggest_title("Fi") == ["First Title"]
    assert reg.suggest_title("Se") == ["Second Title"]
    assert len(reg.suggest_title("")) == 2


def test_suggest_title_case_insensitive(tmp_path: Path):
    reg = DictionaryRegistry(tmp_path / "dict.json")
    reg.add_title("Title")
    assert reg.suggest_title("tit") == ["Title"]
    assert reg.suggest_title("TIT") == ["Title"]


def test_add_title_persists_to_disk(tmp_path: Path):
    path = tmp_path / "dict.json"
    reg = DictionaryRegistry(path)
    reg.add_title("Title")
    reg2 = DictionaryRegistry(path)
    assert "Title" in reg2.all_titles


def test_add_title_deduplicates(tmp_path: Path):
    reg = DictionaryRegistry(tmp_path / "dict.json")
    reg.add_title("Title")
    reg.add_title("Title")
    assert reg.all_titles.count("Title") == 1


def test_all_titles_returns_sorted(tmp_path: Path):
    reg = DictionaryRegistry(tmp_path / "dict.json")
    reg.add_title("Ziva")
    reg.add_title("Title")
    reg.add_title("Moni")
    assert reg.all_titles == sorted(["Ziva", "Title", "Moni"])


# All

def test_empty_registry(tmp_path: Path):
    reg = DictionaryRegistry(tmp_path / "dict.json")
    assert reg.all_characters == []
    assert reg.all_titles == []
    assert reg.suggest_character("") == []
    assert reg.suggest_title("") == []


def test_load_missing_file(tmp_path: Path):
    reg = DictionaryRegistry(tmp_path / "nonexistent.json")
    assert reg.all_characters == []
    assert reg.all_titles == []


def test_load_corrupt_file(tmp_path: Path):
    path = tmp_path / "dict.json"
    path.write_text("NOT JSON", encoding="utf-8")
    reg = DictionaryRegistry(path)
    assert reg.all_characters == []
    assert reg.all_titles == []
