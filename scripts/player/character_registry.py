from __future__ import annotations
import json
from pathlib import Path

_DEFAULT_PATH = Path(__file__).parent / "characters.json"


class CharacterRegistry:
    def __init__(self, path: Path = _DEFAULT_PATH) -> None:
        self._path = path
        self._characters: list[str] = []
        self._load()

    def suggest(self, prefix: str) -> list[str]:
        lower = prefix.lower()
        return [c for c in self._characters if c.lower().startswith(lower)]

    def add(self, name: str) -> None:
        if name and name not in self._characters:
            self._characters.append(name)
            self._characters.sort()
            self._save()

    @property
    def all(self) -> list[str]:
        return list(self._characters)

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._characters = sorted(data) if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            self._characters = []

    def _save(self) -> None:
        try:
            self._path.write_text(
                json.dumps(self._characters, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass  # best-effort persistence; in-memory state is still valid
