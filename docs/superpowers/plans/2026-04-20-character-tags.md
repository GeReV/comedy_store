# Character Tags Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-chapter CHARACTER tag editing to the chapter player, saved as Matroska Tags XML alongside the edited chapters file.

**Architecture:** Characters are stored directly on the `Chapter` dataclass so the existing snapshot/undo mechanism covers them for free. Tag I/O is a thin XML layer (`MatroskaTagsIO`) added to `chapter_io.py`. Two PyQt6 dialogs — single-chapter and bulk overview — handle editing; a global `CharacterRegistry` persists known names for autocomplete.

**Tech Stack:** Python 3.13, PyQt6, xml.etree.ElementTree / xml.dom.minidom (already used in project), pytest

---

## File Map

| File | Change |
|------|--------|
| `scripts/player/chapter_model.py` | Add `characters` to `Chapter`; fix `_snapshot` / `chapters`; add `set_characters`, `set_all_characters`; update `split`, `merge_with_previous` |
| `scripts/player/chapter_io.py` | Add `tags_output_path_for`, `MatroskaTagsIO`; update `MatroskaIO.write` to emit `ChapterUID` |
| `scripts/player/character_registry.py` | New — `CharacterRegistry` backed by `characters.json` |
| `scripts/player/character_dialog.py` | New — `CharacterDialog`, `CharactersOverviewDialog` |
| `scripts/player/player_window.py` | Wire dialogs, load/save tags, add keyboard shortcuts, update shortcuts bar |
| `scripts/player/timeline_widget.py` | Add right-click context menu signal |
| `tests/player/test_chapter_model.py` | Extend with character tests |
| `tests/player/test_chapter_io.py` | Extend with ChapterUID and tags I/O tests |
| `tests/player/test_character_registry.py` | New — registry tests |

Run all tests with: `uv run pytest tests/ -v`

---

### Task 1: Extend `Chapter` with `characters`; fix snapshot and `chapters` property

**Files:**
- Modify: `scripts/player/chapter_model.py`
- Modify: `tests/player/test_chapter_model.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/player/test_chapter_model.py`:

```python
def test_chapter_default_characters():
    ch = Chapter(0, 5_000_000_000, "Intro")
    assert ch.characters == []


def test_chapter_accepts_characters():
    ch = Chapter(0, 5_000_000_000, "Intro", characters=["Avi Kushnir"])
    assert ch.characters == ["Avi Kushnir"]


def test_snapshot_preserves_characters():
    cl = ChapterList([Chapter(0, 5_000_000_000, "A", characters=["Avi"])])
    cl.rename(0, "B")   # triggers before/after snapshot
    cl.undo()
    assert cl[0].characters == ["Avi"]


def test_chapters_property_copies_characters():
    cl = ChapterList([Chapter(0, 5_000_000_000, "A", characters=["Avi"])])
    result = cl.chapters
    result[0].characters.append("MUTATED")
    assert cl[0].characters == ["Avi"]  # internal state unchanged
```

- [ ] **Step 2: Run tests to verify they fail**

```
uv run pytest tests/player/test_chapter_model.py -k "characters" -v
```

Expected: FAIL — `Chapter.__init__()` does not accept `characters`.

- [ ] **Step 3: Implement**

In `scripts/player/chapter_model.py`, add `from dataclasses import dataclass, field` import (replace existing `from dataclasses import dataclass`) and update `Chapter`:

```python
from dataclasses import dataclass, field

@dataclass
class Chapter:
    start_ns: int
    end_ns: int
    name: str
    characters: list[str] = field(default_factory=list)
```

Update `_snapshot` (line ~126) to copy the characters list:

```python
def _snapshot(self) -> list[Chapter]:
    return [Chapter(c.start_ns, c.end_ns, c.name, list(c.characters)) for c in self._chapters]
```

Update the `chapters` property (line ~59) to copy the characters list:

```python
@property
def chapters(self) -> list[Chapter]:
    return [Chapter(c.start_ns, c.end_ns, c.name, list(c.characters)) for c in self._chapters]
```

- [ ] **Step 4: Run tests to verify they pass**

```
uv run pytest tests/player/test_chapter_model.py -v
```

Expected: ALL PASS (existing tests + new character tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/player/chapter_model.py tests/player/test_chapter_model.py
git commit -m "feat: add characters field to Chapter dataclass"
```

---

### Task 2: Add `set_characters` and `set_all_characters` to `ChapterList`

**Files:**
- Modify: `scripts/player/chapter_model.py`
- Modify: `tests/player/test_chapter_model.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/player/test_chapter_model.py`:

```python
def test_set_characters():
    cl = _make_list()
    cl.set_characters(1, ["Avi", "Dana"])
    assert cl[1].characters == ["Avi", "Dana"]
    assert cl[0].characters == []  # others unchanged


def test_set_characters_undo():
    cl = _make_list()
    cl.set_characters(0, ["Avi"])
    assert cl[0].characters == ["Avi"]
    cl.undo()
    assert cl[0].characters == []


def test_set_all_characters():
    cl = _make_list()
    cl.set_all_characters({0: ["Avi"], 2: ["Dana"]})
    assert cl[0].characters == ["Avi"]
    assert cl[1].characters == []
    assert cl[2].characters == ["Dana"]


def test_set_all_characters_single_undo_entry():
    cl = _make_list()
    cl.set_all_characters({0: ["Avi"], 1: ["Dana"]})
    # One undo should restore both changes at once
    cl.undo()
    assert cl[0].characters == []
    assert cl[1].characters == []
    assert not cl.can_undo  # only one entry was pushed
```

- [ ] **Step 2: Run tests to verify they fail**

```
uv run pytest tests/player/test_chapter_model.py -k "set_characters or set_all" -v
```

Expected: FAIL — `ChapterList` has no `set_characters`.

- [ ] **Step 3: Implement**

Add after the `rename` method in `ChapterList` (around line 122):

```python
def set_characters(self, index: int, characters: list[str]) -> None:
    before = self._snapshot()
    self._chapters[index].characters = list(characters)
    after = self._snapshot()
    self._record(before, after)

def set_all_characters(self, by_index: dict[int, list[str]]) -> None:
    before = self._snapshot()
    for index, characters in by_index.items():
        self._chapters[index].characters = list(characters)
    after = self._snapshot()
    self._record(before, after)
```

- [ ] **Step 4: Run tests to verify they pass**

```
uv run pytest tests/player/test_chapter_model.py -v
```

Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/player/chapter_model.py tests/player/test_chapter_model.py
git commit -m "feat: add set_characters and set_all_characters to ChapterList"
```

---

### Task 3: Propagate characters through `split` and `merge_with_previous`

**Files:**
- Modify: `scripts/player/chapter_model.py`
- Modify: `tests/player/test_chapter_model.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/player/test_chapter_model.py`:

```python
def test_split_copies_characters_to_both_halves():
    cl = ChapterList([Chapter(0, 10_000_000_000, "A", characters=["Avi", "Dana"])])
    cl.split(0, 5_000_000_000)
    assert cl[0].characters == ["Avi", "Dana"]
    assert cl[1].characters == ["Avi", "Dana"]


def test_merge_unions_characters():
    cl = ChapterList([
        Chapter(0, 5_000_000_000, "A", characters=["Avi", "Moni"]),
        Chapter(5_000_000_000, 10_000_000_000, "B", characters=["Dana", "Avi"]),
    ])
    cl.merge_with_previous(1)
    assert cl[0].characters == ["Avi", "Dana", "Moni"]  # sorted, deduplicated


def test_merge_characters_undo():
    cl = ChapterList([
        Chapter(0, 5_000_000_000, "A", characters=["Avi"]),
        Chapter(5_000_000_000, 10_000_000_000, "B", characters=["Dana"]),
    ])
    cl.merge_with_previous(1)
    cl.undo()
    assert cl[0].characters == ["Avi"]
    assert cl[1].characters == ["Dana"]
```

- [ ] **Step 2: Run tests to verify they fail**

```
uv run pytest tests/player/test_chapter_model.py -k "split_copies or merge_unions or merge_characters_undo" -v
```

Expected: FAIL — characters not propagated.

- [ ] **Step 3: Implement**

Replace the `split` method body in `chapter_model.py`:

```python
def split(self, index: int, split_ns: int) -> None:
    ch = self._chapters[index]
    if not (ch.start_ns < split_ns < ch.end_ns):
        return
    before = self._snapshot()
    chars = list(ch.characters)
    self._chapters[index] = Chapter(ch.start_ns, split_ns, ch.name, list(chars))
    self._chapters.insert(index + 1, Chapter(split_ns, ch.end_ns, ch.name, list(chars)))
    after = self._snapshot()
    self._record(before, after)
```

Replace the `merge_with_previous` method body:

```python
def merge_with_previous(self, index: int) -> None:
    if index == 0:
        return
    before = self._snapshot()
    prev = self._chapters[index - 1]
    curr = self._chapters[index]
    merged_chars = sorted(set(prev.characters) | set(curr.characters))
    self._chapters[index - 1].end_ns = curr.end_ns
    self._chapters[index - 1].characters = merged_chars
    self._chapters.pop(index)
    after = self._snapshot()
    self._record(before, after)
```

- [ ] **Step 4: Run tests to verify they pass**

```
uv run pytest tests/player/test_chapter_model.py -v
```

Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/player/chapter_model.py tests/player/test_chapter_model.py
git commit -m "feat: propagate characters through split and merge"
```

---

### Task 4: Add `CharacterRegistry`

**Files:**
- Create: `scripts/player/character_registry.py`
- Create: `tests/player/test_character_registry.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/player/test_character_registry.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```
uv run pytest tests/player/test_character_registry.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `scripts/player/character_registry.py`:

```python
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
        self._path.write_text(
            json.dumps(self._characters, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```
uv run pytest tests/player/test_character_registry.py -v
```

Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/player/character_registry.py tests/player/test_character_registry.py
git commit -m "feat: add CharacterRegistry backed by characters.json"
```

---

### Task 5: Update `MatroskaIO.write` to emit `ChapterUID`

**Files:**
- Modify: `scripts/player/chapter_io.py`
- Modify: `tests/player/test_chapter_io.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/player/test_chapter_io.py`:

```python
import xml.etree.ElementTree as ET


def test_write_includes_chapter_uid(tmp_path: Path):
    chapters = [
        Chapter(start_ns=0, end_ns=3_000_000_000, name="First"),
        Chapter(start_ns=3_000_000_000, end_ns=8_000_000_000, name="Second"),
    ]
    out = tmp_path / "out.chapters.xml"
    MatroskaIO().write(chapters, out)
    tree = ET.parse(out)
    uids = [el.text for el in tree.getroot().iter("ChapterUID")]
    assert uids == ["1", "2"]
```

- [ ] **Step 2: Run test to verify it fails**

```
uv run pytest tests/player/test_chapter_io.py::test_write_includes_chapter_uid -v
```

Expected: FAIL — no `ChapterUID` elements found.

- [ ] **Step 3: Implement**

In `scripts/player/chapter_io.py`, update the `write` method of `MatroskaIO`. Inside the `for ch in chapters:` loop, add the `ChapterUID` element as the first child of `ChapterAtom`. Replace:

```python
        for ch in chapters:
            atom = doc.createElement("ChapterAtom")

            start_el = doc.createElement("ChapterTimeStart")
```

With:

```python
        for i, ch in enumerate(chapters):
            atom = doc.createElement("ChapterAtom")

            uid_el = doc.createElement("ChapterUID")
            uid_el.appendChild(doc.createTextNode(str(i + 1)))
            atom.appendChild(uid_el)

            start_el = doc.createElement("ChapterTimeStart")
```

- [ ] **Step 4: Run all chapter_io tests to verify they pass**

```
uv run pytest tests/player/test_chapter_io.py -v
```

Expected: ALL PASS (existing roundtrip tests are unaffected — `MatroskaIO.read` ignores `ChapterUID`).

- [ ] **Step 5: Commit**

```bash
git add scripts/player/chapter_io.py tests/player/test_chapter_io.py
git commit -m "feat: emit ChapterUID in MatroskaIO.write"
```

---

### Task 6: Add `tags_output_path_for` and `MatroskaTagsIO`

**Files:**
- Modify: `scripts/player/chapter_io.py`
- Modify: `tests/player/test_chapter_io.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/player/test_chapter_io.py`:

```python
import textwrap
from scripts.player.chapter_io import MatroskaTagsIO, tags_output_path_for


def test_tags_output_path_for_edited_chapters():
    p = Path("/some/episode.edited.chapters.xml")
    assert tags_output_path_for(p) == Path("/some/episode.edited.tags.xml")


def test_tags_output_path_for_chapters_xml():
    p = Path("/some/episode.chapters.xml")
    assert tags_output_path_for(p) == Path("/some/episode.edited.tags.xml")


def _make_tagged_chapters() -> list[Chapter]:
    return [
        Chapter(0, 5_000_000_000, "Intro"),
        Chapter(5_000_000_000, 10_000_000_000, "Sketch", characters=["Avi Kushnir", "Dana Modan"]),
        Chapter(10_000_000_000, 20_000_000_000, "End"),
    ]


def test_tags_write_and_read_roundtrip(tmp_path: Path):
    chapters = _make_tagged_chapters()
    path = tmp_path / "ep.edited.tags.xml"
    io = MatroskaTagsIO()
    io.write(chapters, path)

    recovered = [Chapter(c.start_ns, c.end_ns, c.name) for c in chapters]
    io.read(path, recovered)

    assert recovered[0].characters == []
    assert recovered[1].characters == ["Avi Kushnir", "Dana Modan"]
    assert recovered[2].characters == []


def test_tags_write_skips_chapters_with_no_characters(tmp_path: Path):
    chapters = [Chapter(0, 5_000_000_000, "Empty")]
    path = tmp_path / "ep.edited.tags.xml"
    MatroskaTagsIO().write(chapters, path)
    root = ET.parse(path).getroot()
    assert list(root) == []  # no <Tag> elements written


def test_tags_read_ignores_out_of_range_uid(tmp_path: Path):
    xml = textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE Tags SYSTEM "matroskatags.dtd">
        <Tags>
          <Tag>
            <Targets><ChapterUID>99</ChapterUID></Targets>
            <Simple><Name>CHARACTER</Name><String>Ghost</String></Simple>
          </Tag>
        </Tags>
    """)
    path = tmp_path / "ep.edited.tags.xml"
    path.write_text(xml, encoding="utf-8")
    chapters = [Chapter(0, 5_000_000_000, "Only")]
    MatroskaTagsIO().read(path, chapters)
    assert chapters[0].characters == []
```

- [ ] **Step 2: Run tests to verify they fail**

```
uv run pytest tests/player/test_chapter_io.py -k "tags" -v
```

Expected: FAIL — `MatroskaTagsIO` and `tags_output_path_for` not defined.

- [ ] **Step 3: Implement**

Add to `scripts/player/chapter_io.py`, after the `output_path_for` function:

```python
def tags_output_path_for(chapters_path: Path) -> Path:
    name = chapters_path.name
    if name.endswith(".edited.chapters.xml"):
        base = name[: -len(".edited.chapters.xml")]
    elif name.endswith(".chapters.xml"):
        base = name[: -len(".chapters.xml")]
    else:
        base = chapters_path.stem
    return chapters_path.parent / (base + ".edited.tags.xml")


class MatroskaTagsIO:
    def read(self, path: Path, chapters: list[Chapter]) -> None:
        """Populate chapters[].characters in-place from a Matroska Tags XML file."""
        tree = ET.parse(path)
        root = tree.getroot()
        for tag in root.iter("Tag"):
            targets = tag.find("Targets")
            if targets is None:
                continue
            uid_el = targets.find("ChapterUID")
            if uid_el is None or uid_el.text is None:
                continue
            idx = int(uid_el.text) - 1
            if idx < 0 or idx >= len(chapters):
                continue
            characters = []
            for simple in tag.findall("Simple"):
                name_el = simple.find("Name")
                string_el = simple.find("String")
                if (
                    name_el is not None
                    and name_el.text == "CHARACTER"
                    and string_el is not None
                    and string_el.text
                ):
                    characters.append(string_el.text)
            chapters[idx].characters = characters

    def write(self, chapters: list[Chapter], path: Path) -> None:
        impl = getDOMImplementation()
        doc = impl.createDocument(
            None, "Tags",
            impl.createDocumentType("Tags", None, "matroskatags.dtd"),
        )
        root = doc.documentElement

        for i, ch in enumerate(chapters):
            if not ch.characters:
                continue
            tag = doc.createElement("Tag")

            targets = doc.createElement("Targets")
            uid_el = doc.createElement("ChapterUID")
            uid_el.appendChild(doc.createTextNode(str(i + 1)))
            targets.appendChild(uid_el)
            tag.appendChild(targets)

            for character in ch.characters:
                simple = doc.createElement("Simple")
                name_el = doc.createElement("Name")
                name_el.appendChild(doc.createTextNode("CHARACTER"))
                simple.appendChild(name_el)
                string_el = doc.createElement("String")
                string_el.appendChild(doc.createTextNode(character))
                simple.appendChild(string_el)
                tag.appendChild(simple)

            root.appendChild(tag)

        with open(path, "w", encoding="utf-8") as f:
            doc.writexml(f, addindent="  ", newl="\n", encoding="UTF-8")
```

- [ ] **Step 4: Run all chapter_io tests to verify they pass**

```
uv run pytest tests/player/test_chapter_io.py -v
```

Expected: ALL PASS.

- [ ] **Step 5: Run the full test suite**

```
uv run pytest tests/ -v
```

Expected: ALL PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/player/chapter_io.py tests/player/test_chapter_io.py
git commit -m "feat: add MatroskaTagsIO and tags_output_path_for"
```

---

### Task 7: Add `CharacterDialog` and `CharactersOverviewDialog`

**Files:**
- Create: `scripts/player/character_dialog.py`

No automated tests — PyQt6 dialogs require a running QApplication.

- [ ] **Step 1: Create `scripts/player/character_dialog.py`**

```python
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

from .character_registry import CharacterRegistry
from .chapter_model import Chapter


class CharacterDialog(QDialog):
    """Edit the character list for a single chapter."""

    def __init__(
        self,
        chapter_name: str,
        characters: list[str],
        registry: CharacterRegistry,
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
        completer = QCompleter(registry.all)
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
        self._registry.add(name)
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
        registry: CharacterRegistry,
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
            self._registry.add(replace)
```

- [ ] **Step 2: Verify the module imports without error**

```
uv run python -c "from scripts.player.character_dialog import CharacterDialog, CharactersOverviewDialog; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/player/character_dialog.py
git commit -m "feat: add CharacterDialog and CharactersOverviewDialog"
```

---

### Task 8: Add right-click context menu signal to `TimelineWidget`

**Files:**
- Modify: `scripts/player/timeline_widget.py`

- [ ] **Step 1: Implement**

Add the import and signal to `timeline_widget.py`.

Add `QPoint` to the existing `from PyQt6.QtCore import ...` import:

```python
from PyQt6.QtCore import QPoint, Qt, pyqtSignal
```

Add the new signal below the existing `seek_requested` signal:

```python
    seek_requested = pyqtSignal(int)  # milliseconds
    chapter_context_menu_requested = pyqtSignal(int, QPoint)  # chapter_idx, global pos
```

Add two new methods before `mousePressEvent`:

```python
    def _chapter_index_at(self, x: float) -> int:
        if self._chapters is None or len(self._chapters) == 0:
            return -1
        first_ns = self._chapters[0].start_ns
        last_ns = self._chapters[len(self._chapters) - 1].end_ns
        total_ns = last_ns - first_ns
        if total_ns == 0:
            return -1
        frac = max(0.0, min(1.0, x / self.width()))
        ns = first_ns + int(frac * total_ns)
        return self._chapters.current_index(ns)

    def contextMenuEvent(self, event) -> None:  # type: ignore[override]
        idx = self._chapter_index_at(event.position().x())
        if idx >= 0:
            self.chapter_context_menu_requested.emit(idx, event.globalPosition().toPoint())
```

- [ ] **Step 2: Verify the module imports without error**

```
uv run python -c "from scripts.player.timeline_widget import TimelineWidget; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/player/timeline_widget.py
git commit -m "feat: add chapter context menu signal to TimelineWidget"
```

---

### Task 9: Wire `PlayerWindow` — load/save tags, shortcuts, dialogs, shortcuts bar

**Files:**
- Modify: `scripts/player/player_window.py`

- [ ] **Step 1: Update imports**

Replace the existing import block at the top of `player_window.py` with:

```python
from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QEvent, QPoint, QTimer, QUrl, Qt
from PyQt6.QtMultimedia import QAudioOutput, QMediaMetaData, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QDialog,
    QInputDialog,
    QLabel,
    QLayout,
    QMainWindow,
    QMenu,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .chapter_io import MatroskaIO, MatroskaTagsIO, get_io, output_path_for, tags_output_path_for
from .chapter_model import Chapter, ChapterList
from .character_dialog import CharacterDialog, CharactersOverviewDialog
from .character_registry import CharacterRegistry
from .timeline_widget import TimelineWidget
```

- [ ] **Step 2: Add `_registry` and `_tags_output_path` to `__init__`**

In `PlayerWindow.__init__`, add after `self._dirty = False`:

```python
        self._tags_output_path: Path | None = None
        self._registry = CharacterRegistry()
```

After creating `self._timeline`, connect the new signal:

```python
        self._timeline.chapter_context_menu_requested.connect(self._on_chapter_context_menu)
```

- [ ] **Step 3: Reset `_tags_output_path` in `load_media`**

In `load_media`, add `self._tags_output_path = None` after `self._output_path = None`:

```python
    def load_media(self, path: Path) -> None:
        self._frame_ns = 0
        self._duration_ns = 0
        self._loaded_chapters = []
        self._chapters = ChapterList([])
        self._output_path = None
        self._tags_output_path = None
        self._base_title = path.name
        self._dirty = False
        self._refresh_title()
        self._timeline.set_chapters(self._chapters)
        self._timeline.set_duration(0)
        self._player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        self.statusBar().showMessage("Drop .chapters.xml to add chapters")
```

- [ ] **Step 4: Load tags in `load_chapters`**

Replace `load_chapters` with:

```python
    def load_chapters(self, path: Path, output_path: Path) -> None:
        self._output_path = output_path
        self._tags_output_path = tags_output_path_for(output_path)
        self._dirty = False
        self._refresh_title()
        raw = get_io(path).read(path)
        if raw and raw[0].start_ns > 0:
            raw = [Chapter(start_ns=0, end_ns=raw[0].start_ns, name="N/A")] + raw
        if self._tags_output_path.exists():
            MatroskaTagsIO().read(self._tags_output_path, raw)
        self._loaded_chapters = raw
        self._chapters = ChapterList(self._with_trailing(raw))
        self._timeline.set_chapters(self._chapters)
        self._update_status()
```

- [ ] **Step 5: Save tags in `_save`**

Replace `_save` with:

```python
    def _save(self) -> None:
        if self._output_path is None:
            return
        try:
            chapters = self._chapters.chapters
            MatroskaIO().write(chapters, self._output_path)
            if self._tags_output_path is not None:
                MatroskaTagsIO().write(chapters, self._tags_output_path)
            self._dirty = False
            self._refresh_title()
            self.statusBar().showMessage(f"Saved to {self._output_path.name}", 3000)
        except OSError as e:
            self.statusBar().showMessage(f"Save failed: {e}", 5000)
```

- [ ] **Step 6: Add keyboard shortcuts for `C` and `Shift+C`**

In `keyPressEvent`, add after the `elif key == Key.Key_R:` branch:

```python
        elif key == Key.Key_C and mods == Mod.NoModifier:
            self._edit_current_chapter_characters()
        elif key == Key.Key_C and mods == Mod.ShiftModifier:
            self._manage_all_characters()
```

- [ ] **Step 7: Add the three new private methods**

Add after `_rename_chapter`:

```python
    def _edit_current_chapter_characters(self) -> None:
        idx = self._chapters.current_index(self._pos_ns())
        if idx < 0:
            return
        self._edit_characters(idx)

    def _edit_characters(self, idx: int) -> None:
        ch = self._chapters[idx]
        dlg = CharacterDialog(ch.name, ch.characters, self._registry, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_chars = dlg.characters
            if new_chars != ch.characters:
                self._chapters.set_characters(idx, new_chars)
                self._mark_dirty()
                self._timeline.set_chapters(self._chapters)
                self._update_status()

    def _manage_all_characters(self) -> None:
        original = self._chapters.chapters
        dlg = CharactersOverviewDialog(original, self._registry, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            changes = dlg.get_changes(original)
            if changes:
                self._chapters.set_all_characters(changes)
                self._mark_dirty()
                self._timeline.set_chapters(self._chapters)
                self._update_status()

    def _on_chapter_context_menu(self, idx: int, pos: QPoint) -> None:
        menu = QMenu(self)
        edit_action = menu.addAction("Edit characters…")
        all_action = menu.addAction("Manage all characters…")
        action = menu.exec(pos)
        if action == edit_action:
            self._edit_characters(idx)
        elif action == all_action:
            self._manage_all_characters()
```

- [ ] **Step 8: Update the shortcuts bar**

In `_build_shortcuts_bar`, update the first `row(...)` call to include the character shortcuts. Replace:

```python
        rows = [
            row([
                (key("Space"), "Play/Pause"),
                (f'{key("[")} {key("]")}', "Prev/Next chapter"),
                (key("S"), "Split"),
                (key("Del"), "Merge with prev"),
                (key("R"), "Rename"),
                (key("Ctrl+S"), "Save"),
                (key("Ctrl+Z"), "Undo"),
                (key("Ctrl+Shift+Z"), "Redo"),
            ]),
```

With:

```python
        rows = [
            row([
                (key("Space"), "Play/Pause"),
                (f'{key("[")} {key("]")}', "Prev/Next chapter"),
                (key("S"), "Split"),
                (key("Del"), "Merge with prev"),
                (key("R"), "Rename"),
                (key("C"), "Edit chars"),
                (key("Shift+C"), "All chars"),
                (key("Ctrl+S"), "Save"),
                (key("Ctrl+Z"), "Undo"),
                (key("Ctrl+Shift+Z"), "Redo"),
            ]),
```

- [ ] **Step 9: Run the full test suite**

```
uv run pytest tests/ -v
```

Expected: ALL PASS.

- [ ] **Step 10: Verify the player launches without errors**

```
uv run python -m scripts.player
```

Expected: player window opens, no import errors in terminal.

- [ ] **Step 11: Commit**

```bash
git add scripts/player/player_window.py
git commit -m "feat: wire character tag editing into PlayerWindow"
```
