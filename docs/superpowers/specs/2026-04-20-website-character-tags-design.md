# Website Character Tags — Design Spec
_2026-04-20_

## Overview

Surface character tags (from `.edited.tags.xml` files) on the Comedy Store website. Tags appear as colored pills on chapter headers in the episode view and search results. Clicking a tag opens a dedicated tag-filter view listing all chapters tagged with that character. Text search matches chapter titles and tag text in addition to subtitle lines.

---

## 1. Data Layer (`scripts/build_data.py`)

`parse_chapters_xml` is extended to also read a sibling `.edited.tags.xml` file (same stem, same directory). The tags XML is parsed using the same logic as `MatroskaTagsIO.read` in the player: `<Tag>/<Targets>/<ChapterUID>` → `<Simple>/<Name>=CHARACTER` → `<String>` values are collected and attached to the matching chapter by 1-based index.

**JSON chapter shape:**
```json
{ "start": 217.32, "end": 274.88, "name": "יהוקמץ בן-פסיק", "tags": ["יהוקמץ בן-פסיק"] }
```

- `tags` is **always present** as an array (empty `[]` when no tags — never omitted).
- Tags with no matching chapter UID are silently ignored.
- If no `.edited.tags.xml` exists, all chapters get `tags: []`.

---

## 2. TypeScript Types & Loader (`src/types.ts`, `src/loader.ts`)

**`Chapter`** gains `tags: string[]`.

**`EpisodeSearchResult`** gains:
```ts
chapterMatches?: { chapterIdx: number; chapter: Chapter }[];
```

**`loader.ts` additions:**
- `getCachedChapters(): Map<string, Chapter[]>` — exposes all cached chapter data (mirrors `getCachedSubtitles`).
- A `tagIndex: Map<string, {episodeId: string; chapterIdx: number}[]>` is built once during bundle load by iterating all episodes' chapters.
- `getTagIndex(): Map<string, {episodeId: string; chapterIdx: number}[]>` — exposes the tag index.

---

## 3. Tag Color System (`src/utils.ts`)

A pure function `tagColor(tag: string): string` hashes the tag text (simple charCode sum mod palette length) to an index into a fixed palette of ~12 distinct HSL colors chosen to work in both light and dark themes.

Tags render as `<span class="tag">` pills with `style="--tag-color: hsl(...)"`. CSS uses `background: var(--tag-color)` with a contrasting fixed text color per palette slot.

---

## 4. Episode View (`src/views/episode.ts`)

In `renderWithChapters`, after building the chapter header (name + timestamp), a `<div class="chapter-tags">` is appended inside the header containing one `<span class="tag">` per tag with computed color. The div is always created when `ch.tags.length > 0`.

Tag click navigation is handled by a single delegated listener on the chapter list: clicks on `.tag` elements navigate to `#tag/{encodeURIComponent(tagText)}`.

`applyQueryFilter` updated: a chapter block is visible if any of its lines match **or** its chapter name/tags contain the query. Named chapters that match on title/tag show their header even when all subtitle lines are hidden.

---

## 5. Tag Route & View (`src/router.ts`, `src/views/tag.ts`)

**New route kind:**
```ts
{ kind: "tag", tag: string }
```
Parsed from `#tag/{encodedTagName}`. Added to `parseHash` and `handleRoute`.

**`renderTagView(container, tag, tagIndex, episodeIndex, chapterMap)`** renders:
- A heading with the tag pill and a count (`N סצינות`).
- Episodes in episode-number order, each as a group heading linking to `#episode/{id}`.
- Under each episode: chapter cards (`<a>`) linking to `#episode/{id}/ch-{N}`, showing chapter name, timestamp, and tag pills (clickable, navigating to their own tag view).
- Episodes with no matching chapters are omitted.

**Breadcrumb:** `ראשי › תג: {tag}`

**Sidebar:** no special state for the tag view.

**Search box:** behaves normally (navigates to `#search/{q}`).

---

## 6. Enhanced Search (`src/search.ts`, `src/views/results.ts`)

**`searchEpisodes`** accepts a new `chapterMap: Map<string, Chapter[]>` parameter. For each episode, after collecting subtitle-line match indices it also checks each chapter's `name` and `tags` against the query, collecting `chapterMatches`. An episode is included in results if it has either subtitle-line matches or chapter matches.

**`episodeHasMatch`** (used by sidebar) similarly checks chapter name/tags via the chapter map.

**`results.ts`:** Chapter match cards are rendered **above** subtitle-line entries for each episode. Each card is an `<a>` linking to `#episode/{id}/ch-{N}`, showing name + timestamp + tag pills. The existing `entries` / "show more" logic is unchanged. `totalMatches` count includes chapter matches.

---

## Navigation Graph

| From | Action | To |
|---|---|---|
| Episode view | Click tag pill | `#tag/{tag}` |
| Search results | Click tag pill on chapter card | `#tag/{tag}` |
| Tag view | Click chapter card | `#episode/{id}/ch-{N}` |
| Tag view | Type in search box | `#search/{q}` |
| Any view | Browser back | Previous route |

Arriving at an episode/chapter from the tag view shows the standard breadcrumb (`ראשי › פרק N`); browser back returns to the tag view. No `prevTag` URL threading — keeps the URL scheme simple.

---

## Files Changed / Added

| File | Change |
|---|---|
| `scripts/build_data.py` | Read `.edited.tags.xml`; add `tags: []` to all chapters |
| `src/types.ts` | `Chapter.tags: string[]`; `EpisodeSearchResult.chapterMatches?` |
| `src/loader.ts` | `getCachedChapters()`, `getTagIndex()`, build `tagIndex` on load |
| `src/router.ts` | Parse `#tag/{name}` → `{kind:"tag", tag}` |
| `src/search.ts` | Accept `chapterMap`; match chapter name/tags; populate `chapterMatches` |
| `src/views/episode.ts` | Render tag pills; delegated tag-click navigation; chapter filter by name/tags |
| `src/views/results.ts` | Render chapter match cards above subtitle entries |
| `src/views/tag.ts` | New: tag filter view |
| `src/utils.ts` | `tagColor(tag)` function |
| `static/style.css` | `.tag` pill styles, `--tag-color` custom property |
