# Character Tags — Design Spec
Date: 2026-04-20

## Overview

Add support for Matroska Tags XML to the chapter editor/player. The only tag type needed is `CHARACTER`, associated to chapters via `ChapterUID`. Tags are stored in a separate `<base>.edited.tags.xml` file alongside the edited chapters file. Character editing is undoable/redoable, integrated with the existing undo stack.

---

## 1. Data Model

### `Chapter` dataclass
Add `characters: list[str] = field(default_factory=list)` to the existing `Chapter` dataclass in `chapter_model.py`. The existing snapshot/restore mechanism automatically includes this field, so undo/redo costs nothing extra.

### `ChapterList` mutations
Add two new methods:
- `set_characters(index: int, characters: list[str])` — replaces the character list for one chapter and pushes a single undo entry via the existing `_record()` mechanism.
- `set_all_characters(by_index: dict[int, list[str]])` — replaces characters for multiple chapters in one call, pushing a single composite undo entry. Used by the overview dialog so all bulk changes are undone together.

Update existing structural mutations:
- `split(index, split_ns)` — the new second half copies the original chapter's character list.
- `merge_with_previous(index)` — the surviving chapter's character list is the sorted, deduplicated union of both chapters' lists.

ChapterUIDs are always 1-based positional indices, recomputed implicitly from list position on every write.

### `CharacterRegistry`
New class in `scripts/player/character_registry.py`. Wraps a `list[str]` backed by `scripts/player/characters.json`.

- Loaded at application startup; created empty if the file does not exist.
- `suggest(prefix: str) -> list[str]` — case-insensitive prefix match, sorted alphabetically.
- `add(name: str)` — adds `name` if not already present, then persists immediately.
- The JSON file is a plain sorted array of strings.

---

## 2. Tag I/O

### File naming
Tags output path mirrors the chapters output path pattern:

| File | Pattern |
|------|---------|
| Source chapters | `<base>.chapters.xml` |
| Edited chapters | `<base>.edited.chapters.xml` |
| Edited tags | `<base>.edited.tags.xml` |

`chapter_io.py` gains a `tags_output_path_for(chapters_path: Path) -> Path` helper that derives the tags path from the chapters path.

### `MatroskaTagsIO` class (new, in `chapter_io.py`)
Reads and writes `<base>.edited.tags.xml` following the Matroska Tags DTD.

**Write format:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Tags SYSTEM "matroskatags.dtd">
<Tags>
  <Tag>
    <Targets>
      <ChapterUID>1</ChapterUID>
    </Targets>
    <Simple>
      <Name>CHARACTER</Name>
      <String>Avi Kushnir</String>
    </Simple>
  </Tag>
</Tags>
```

- One `<Tag>` block per chapter that has at least one character.
- Multiple characters produce multiple `<Simple>` elements under the same `<Tag>`.
- ChapterUID is the 1-based index of the chapter in the list at save time.
- Chapters with no characters are omitted entirely.

**Read behaviour:** Parse `<ChapterUID>` → map back to `chapters[uid - 1].characters`. UIDs that exceed the current chapter count are silently ignored (handles files edited externally).

### Load/save lifecycle
- When a `.chapters.xml` is dropped (or its `.edited.chapters.xml` is auto-loaded), the tags file is also loaded if it exists at the derived path.
- `Ctrl+S` saves both the chapters file and the tags file atomically (chapters first, then tags).

---

## 3. UI

### Single-chapter character dialog — `CharacterDialog`

`CharacterDialog(QDialog)` manages characters for one chapter.

**Layout (top to bottom):**
1. `QListWidget` — current characters, one per row. `Delete` key or a remove button removes the selected entry.
2. `QLineEdit` with `QCompleter` backed by `CharacterRegistry.suggest()` — focused immediately on open.
3. Pressing `Enter` in the input: adds the name to the list and to `CharacterRegistry`, clears the input, re-focuses the input. Ready for the next entry.
4. `OK` / `Cancel` buttons.

**Trigger points:**
- Keyboard shortcut `C` — opens for the chapter at the current playhead position.
- Right-click on the timeline → context menu → "Edit characters…".

**Undo integration:** On `OK`, `PlayerWindow` calls `set_characters(index, new_list)`, which pushes a single undo entry.

### Multi-chapter overview dialog — `CharactersOverviewDialog`

`CharactersOverviewDialog(QDialog)` shows all chapters in a two-column `QTableWidget`:

| Chapter | Characters |
|---------|-----------|
| Intro | Avi Kushnir, Dana Modan |
| Sketch 1 | Moni Moshonov |

- Characters column is editable inline (comma-separated).
- "Find / Replace" button opens an inline form: `From:` / `To:` fields + `Replace All` button. Replaces the character name across all chapters in the dialog's working copy.
- Dialog operates on a deep copy of `chapters`. On `OK`, `PlayerWindow` calls `set_all_characters` with a dict of all chapters whose character lists changed, producing a single composite undo entry.

**Trigger points:**
- Keyboard shortcut `Shift+C`.
- Can also be opened from the right-click context menu as "Manage all characters…".

### Timeline right-click context menu
`TimelineWidget` gains a `contextMenuRequested` signal (or overrides `contextMenuEvent`). `PlayerWindow` connects it and builds a `QMenu` with:
- "Edit characters…" → opens `CharacterDialog` for the clicked chapter
- "Manage all characters…" → opens `CharactersOverviewDialog`

### Shortcuts bar update
Add `C` (Edit characters) and `Shift+C` (All characters) to the existing shortcuts bar at the bottom of `PlayerWindow`.

---

## 4. Files changed / added

| File | Change |
|------|--------|
| `scripts/player/chapter_model.py` | Add `characters` field to `Chapter`; add `set_characters` to `ChapterList`; update `split` and `merge_with_previous` |
| `scripts/player/chapter_io.py` | Add `MatroskaTagsIO`, `tags_output_path_for`; update `MatroskaIO.write` to emit `ChapterUID` |
| `scripts/player/character_registry.py` | New: `CharacterRegistry` backed by `characters.json` |
| `scripts/player/character_dialog.py` | New: `CharacterDialog` and `CharactersOverviewDialog` |
| `scripts/player/player_window.py` | Wire up dialogs, load/save tags, add shortcuts, update shortcuts bar |
| `scripts/player/timeline_widget.py` | Add right-click context menu support |
| `scripts/player/characters.json` | New (auto-created on first use, gitignored or committed as `[]`) |
