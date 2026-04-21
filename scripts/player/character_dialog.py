from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .dictionary_registry import DictionaryRegistry
from .chapter_model import Chapter


class CharacterDialog(QDialog):
    """Edit the character list for a single chapter."""

    def __init__(
        self,
        chapter_name: str,
        characters: list[str],
        registry: DictionaryRegistry,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Characters — {chapter_name}")
        self.setMinimumWidth(350)
        self._registry = registry
        self._characters: list[str] = list(characters)

        layout = QVBoxLayout(self)

        self._list = QListWidget()
        for c in self._characters:
            self._list.addItem(c)
        layout.addWidget(self._list)

        remove_btn = QPushButton("Remove selected (Del)")
        remove_btn.clicked.connect(self._remove_selected)
        layout.addWidget(remove_btn)

        add_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Add character…")
        completer = QCompleter(registry.all_characters)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self._input.setCompleter(completer)
        self._input.returnPressed.connect(self._add_character)
        completer.activated.connect(self._add_from_completer)
        add_row.addWidget(self._input)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_character)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._input.setFocus()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Delete:
            self._remove_selected()
        else:
            super().keyPressEvent(event)

    @property
    def characters(self) -> list[str]:
        return list(self._characters)

    def _add_character(self) -> None:
        self._commit_name(self._input.text().strip())

    def _add_from_completer(self, text: str) -> None:
        self._commit_name(text.strip())

    def _commit_name(self, name: str) -> None:
        if not name or name in self._characters:
            self._input.clear()
            return
        self._characters.append(name)
        self._list.addItem(name)
        self._registry.add_character(name)
        self._input.clear()

    def _remove_selected(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            return
        self._list.takeItem(row)
        self._characters.pop(row)


class CharactersOverviewDialog(QDialog):
    """Bulk-edit characters across all chapters."""

    def __init__(
        self,
        chapters: list[Chapter],
        registry: DictionaryRegistry,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("All Characters")
        self.setMinimumWidth(620)
        self.setMinimumHeight(400)
        self._registry = registry

        layout = QVBoxLayout(self)

        self._table = QTableWidget(len(chapters), 2)
        self._table.setHorizontalHeaderLabels(["Chapter", "Characters (comma-separated)"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)

        for i, ch in enumerate(chapters):
            name_item = QTableWidgetItem(ch.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 0, name_item)
            chars_item = QTableWidgetItem(", ".join(ch.characters))
            self._table.setItem(i, 1, chars_item)

        layout.addWidget(self._table)

        fr_row = QHBoxLayout()
        fr_row.addWidget(QLabel("Find:"))
        self._find_input = QLineEdit()
        fr_row.addWidget(self._find_input)
        fr_row.addWidget(QLabel("Replace:"))
        self._replace_input = QLineEdit()
        fr_row.addWidget(self._replace_input)
        replace_btn = QPushButton("Replace All")
        replace_btn.clicked.connect(self._replace_all)
        fr_row.addWidget(replace_btn)
        layout.addLayout(fr_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_changes(self, original_chapters: list[Chapter]) -> dict[int, list[str]]:
        """Return {index: new_characters} for every chapter whose list changed."""
        changes: dict[int, list[str]] = {}
        for i in range(self._table.rowCount()):
            item = self._table.item(i, 1)
            raw = item.text() if item else ""
            chars = [c.strip() for c in raw.split(",") if c.strip()]
            if chars != original_chapters[i].characters:
                changes[i] = chars
        return changes

    def _replace_all(self) -> None:
        find = self._find_input.text().strip()
        replace = self._replace_input.text().strip()
        if not find or find == replace:
            return
        for i in range(self._table.rowCount()):
            item = self._table.item(i, 1)
            if item is None:
                continue
            chars = [c.strip() for c in item.text().split(",") if c.strip()]
            new_chars = [replace if c == find else c for c in chars]
            item.setText(", ".join(new_chars))
        if replace:
            self._registry.add_character(replace)
