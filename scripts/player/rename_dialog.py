from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QVBoxLayout,
)

from .dictionary_registry import DictionaryRegistry


class RenameDialog(QDialog):
    """Edit the title for a single chapter."""

    def __init__(
        self,
        chapter_name: str,
        registry: DictionaryRegistry,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Rename chapter")
        self.setMinimumWidth(350)
        self._registry = registry
        self._chapter_name = chapter_name

        layout = QVBoxLayout(self)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Set name…")
        self._input.setText(chapter_name)
        completer = QCompleter(registry.all_titles)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self._input.setCompleter(completer)
        self._input.returnPressed.connect(self._add_title)
        completer.activated.connect(self._add_from_completer)
        layout.addWidget(self._input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._input.setFocus()

    @property
    def chapter_name(self) -> str:
        return self._chapter_name

    def _add_title(self) -> None:
        self._commit_name(self._input.text().strip())

    def _add_from_completer(self, text: str) -> None:
        self._commit_name(text.strip())

    def _commit_name(self, name: str) -> None:
        self._chapter_name = name
        self._registry.add_title(name)
        self._input.clear()
