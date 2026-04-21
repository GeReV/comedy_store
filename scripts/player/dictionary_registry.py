from __future__ import annotations
import json
from pathlib import Path

_DEFAULT_PATH = Path(__file__).parent / "dictionary.json"


class DictionaryRegistry:
    def __init__(self, path: Path = _DEFAULT_PATH) -> None:
        self._path = path
        self._characters: list[str] = []
        self._titles: list[str] = []
        self._load()

    def suggest_character(self, prefix: str) -> list[str]:
        lower = prefix.lower()
        return [c for c in self._characters if c.lower().startswith(lower)]

    def add_character(self, name: str) -> None:
        if name and name not in self._characters:
            self._characters.append(name)
            self._characters.sort()
            self._save()

    def suggest_title(self, prefix: str) -> list[str]:
        lower = prefix.lower()
        return [c for c in self._titles if c.lower().startswith(lower)]

    def add_title(self, title: str) -> None:
        if title and title not in self._titles:
            self._titles.append(title)
            self._titles.sort()
            self._save()

    @property
    def all_characters(self) -> list[str]:
        return list(self._characters)

    @property
    def all_titles(self) -> list[str]:
        return list(self._titles)

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._characters = sorted(data["characters"]) if "characters" in data and isinstance(data["characters"], list) else []
            self._titles = sorted(data["titles"]) if "titles" in data and isinstance(data["titles"], list) else []
        except (json.JSONDecodeError, OSError):
            self._characters = []
            self._titles = []


    def _save(self) -> None:
        try:
            output = {
                "characters": self._characters,
                "titles": self._titles,
            }
            self._path.write_text(
                json.dumps(output, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass  # best-effort persistence; in-memory state is still valid
