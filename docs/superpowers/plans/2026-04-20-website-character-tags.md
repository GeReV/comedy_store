# Website Character Tags Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface character tags from `.edited.tags.xml` files in the website — as colored pills on chapters, a tag-filter view, and enhanced search that matches chapter titles and tags.

**Architecture:** The Python build script gains tag XML parsing and merges tags into each chapter in the JSON bundle. The TypeScript frontend adds a new `#tag/{name}` route, enhanced search that checks chapter name/tags, a tag-filter view, and colored tag pill rendering in the episode and results views. A single delegated listener on the main pane handles tag navigation across all views.

**Tech Stack:** Python 3.13 + xml.etree.ElementTree (data build), TypeScript + esbuild (frontend), Vitest (unit tests)

---

## File Map

| File | Change |
|---|---|
| `scripts/build_data.py` | Add `parse_tags_xml`; add `tags: []` to `parse_chapters_xml`; merge tags in `find_chapters` |
| `src/types.ts` | `Chapter.tags: string[]`; new `ChapterMatch`; `EpisodeSearchResult.chapterMatches?` |
| `src/router.ts` | Add `{kind:"tag";tag:string}` to `Route`; add `buildTagHash`; update `parseHash` |
| `src/__tests__/router.test.ts` | Add tag route tests |
| `src/utils.ts` | Add `TAG_PALETTE` and `tagColor(tag)` |
| `src/__tests__/utils.test.ts` | New: tag color determinism tests |
| `static/style.css` | Add `.tag`, `.chapter-tags`, `.tag-view-heading`, `.tag-episode-section`, `.tag-chapter-card` |
| `src/loader.ts` | Add `buildTagIndex`, `getCachedChapters`, `getTagIndex`; build index on load |
| `src/search.ts` | `episodeHasMatch` checks chapters; `searchEpisodes` accepts `chapterMap`, populates `chapterMatches` |
| `src/__tests__/search.test.ts` | New: chapter/tag search tests |
| `src/sidebar.ts` | `updateSidebarState` accepts optional `chapterMap`; passes to `episodeHasMatch` |
| `src/views/episode.ts` | Render tag pills in chapter headers; update `applyQueryFilter` to check name/tags |
| `src/views/results.ts` | Import `ChapterMatch`, `tagColor`; render chapter match cards above subtitle entries; delegated tag listener on container |
| `src/views/tag.ts` | New: `renderTagView` |
| `src/main.ts` | Handle tag route; pass `getCachedChapters()` to search; update `syncSidebar`; tag breadcrumb; delegated tag click on mainPaneEl |

---

## Task 1: Python — Add `tags` field to chapter data

**Files:**
- Modify: `scripts/build_data.py`

- [ ] **Step 1: Add `parse_tags_xml` function**

Open `scripts/build_data.py`. After the `parse_chapters_xml` function (line 86), add:

```python
def parse_tags_xml(path: Path) -> dict[int, list[str]]:
    """Parse a .edited.tags.xml, return {0-based-chapter-idx: [character, ...]}."""
    try:
        tree = ET.parse(path)
    except Exception:
        return {}
    tags: dict[int, list[str]] = {}
    for tag in tree.getroot().iter("Tag"):
        targets = tag.find("Targets")
        if targets is None:
            continue
        uid_el = targets.find("ChapterUID")
        if uid_el is None or uid_el.text is None:
            continue
        idx = int(uid_el.text) - 1  # ChapterUID is 1-based
        characters: list[str] = []
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
        if characters:
            tags[idx] = characters
    return tags
```

- [ ] **Step 2: Add `tags: []` to every chapter in `parse_chapters_xml`**

In `parse_chapters_xml`, find the `chapters.append({...})` call (around line 101) and add `"tags": []`:

```python
        chapters.append({
            "start": round(int(start_el.text) / 1_000_000_000, 3),
            "end": round(int(end_el.text) / 1_000_000_000, 3),
            "name": name,
            "tags": [],
        })
```

- [ ] **Step 3: Merge tags into chapters in `find_chapters`**

Replace the body of `find_chapters` (currently ~3 lines) with:

```python
def find_chapters(srt_path: Path) -> list[dict]:
    """Return chapters for an episode from its .edited.chapters.xml, if it exists."""
    edited = srt_path.parent / f"{srt_path.stem}.edited.chapters.xml"
    if not edited.exists():
        return []
    chapters = parse_chapters_xml(edited)
    tags_path = srt_path.parent / f"{srt_path.stem}.edited.tags.xml"
    if tags_path.exists():
        tags_by_idx = parse_tags_xml(tags_path)
        for idx, chars in tags_by_idx.items():
            if 0 <= idx < len(chapters):
                chapters[idx]["tags"] = chars
    return chapters
```

- [ ] **Step 4: Rebuild data and verify**

```bash
cd /mnt/c/workspace/comedy_store_transcribe
npm run build:data
```

Expected: prints episode list, no errors.

Then spot-check episode 1 (which has tags):
```bash
python -c "
import json
data = json.load(open('static/data/subtitles.json'))
ep1 = next(e for e in data if e['id'] == 'פרק_001-21_12_08')
tagged = [c for c in ep1.get('chapters', []) if c['tags']]
print(f'Tagged chapters: {len(tagged)}')
for c in tagged:
    print(c['name'], c['tags'])
"
```

Expected output:
```
Tagged chapters: 6
יהוקמץ בן-פסיק ['יהוקמץ בן-פסיק']
N/A ['יש-לי יש-לי']
...
```

Also verify an episode without a tags file has `tags: []` on all chapters:
```bash
python -c "
import json
data = json.load(open('static/data/subtitles.json'))
# Find any episode with chapters
ep = next((e for e in data if e.get('chapters')), None)
print('All chapters have tags key:', all('tags' in c for c in ep['chapters']))
"
```

Expected: `All chapters have tags key: True`

- [ ] **Step 5: Commit**

```bash
git add scripts/build_data.py static/data/subtitles.json static/data/subtitles.json.gz
git commit -m "feat(data): add character tags to chapter JSON output"
```

---

## Task 2: TypeScript types

**Files:**
- Modify: `src/types.ts`

- [ ] **Step 1: Update `Chapter`, add `ChapterMatch`, update `EpisodeSearchResult`**

Replace the entire `src/types.ts` with:

```typescript
export interface EpisodeMetadata {
  id: string;
  title: string;
  /** Numeric sort key. Regular episodes: episode number. 2020 specials: 10000+. */
  num: number;
}

export interface Line {
  start: number; // seconds
  end: number;   // seconds
  text: string;
}

export interface Chapter {
  start: number; // seconds
  end: number;   // seconds
  name: string;
  tags: string[];
}

export type EpisodeIndex = EpisodeMetadata[];
export type EpisodeLines = Line[];

/**
 * A range of lines to display for one logical match group.
 * startIdx..endIdx (inclusive) is the display range including context.
 * matchIndices contains the line indices that are actual search hits.
 */
export interface DisplayEntry {
  startIdx: number;
  endIdx: number;
  matchIndices: Set<number>;
}

export interface ChapterMatch {
  /** 1-based chapter index (matches URL ch-{N} convention). */
  chapterIdx: number;
  chapter: Chapter;
}

export interface EpisodeSearchResult {
  episode: EpisodeMetadata;
  /** Merged, context-expanded display entries. */
  entries: DisplayEntry[];
  /** Total individual matching lines (before context/merging) plus chapter matches. */
  totalMatches: number;
  /** Chapters whose name or tags matched the query. */
  chapterMatches?: ChapterMatch[];
}
```

- [ ] **Step 2: Type-check compiles**

```bash
cd /mnt/c/workspace/comedy_store_transcribe
npm run build:ts 2>&1 | head -20
```

Expected: build succeeds (esbuild doesn't do type-checking, but verifies the file is parseable). Type errors will surface in later tasks as we update callers.

- [ ] **Step 3: Commit**

```bash
git add src/types.ts
git commit -m "feat(types): add Chapter.tags, ChapterMatch, EpisodeSearchResult.chapterMatches"
```

---

## Task 3: Router — add tag route

**Files:**
- Modify: `src/router.ts`
- Modify: `src/__tests__/router.test.ts`

- [ ] **Step 1: Write failing tests**

Add to `src/__tests__/router.test.ts`, inside the `describe("parseHash", ...)` block:

```typescript
    it("tag hash → tag route", () => {
        const encoded = encodeURIComponent("יש-לי יש-לי");
        expect(parseHash(`#tag/${encoded}`)).toEqual({
            kind: "tag",
            tag: "יש-לי יש-לי",
        });
    });

    it("tag hash with ASCII name → tag route", () => {
        expect(parseHash("#tag/comedy")).toEqual({ kind: "tag", tag: "comedy" });
    });
```

And add a new `describe("buildTagHash", ...)` block at the end of the file:

```typescript
describe("buildTagHash", () => {
    it("encodes tag name", () => {
        expect(buildTagHash("יש-לי יש-לי")).toBe(
            `tag/${encodeURIComponent("יש-לי יש-לי")}`,
        );
    });

    it("plain ASCII tag", () => {
        expect(buildTagHash("comedy")).toBe("tag/comedy");
    });
});
```

Also update the import at the top of the test file:

```typescript
import { parseHash, buildEpisodeHash, buildTagHash } from "../router.js";
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /mnt/c/workspace/comedy_store_transcribe
npm run test:unit 2>&1 | tail -20
```

Expected: failures for `tag hash → tag route`, `tag hash with ASCII name → tag route`, `buildTagHash` tests.

- [ ] **Step 3: Update `router.ts`**

Replace the entire `src/router.ts` with:

```typescript
export type Route =
    | { kind: "welcome" }
    | { kind: "results"; query: string }
    | { kind: "episode"; id: string; lineIndex?: number; query?: string }
    | { kind: "chapter"; episodeId: string; chapterIdx: number }
    | { kind: "tag"; tag: string };

export function parseHash(hash: string): Route {
    const raw = hash.startsWith("#") ? hash.slice(1) : hash;
    if (!raw) return { kind: "welcome" };

    if (raw.startsWith("search/")) {
        const query = decodeURIComponent(raw.slice("search/".length));
        return { kind: "results", query };
    }

    if (raw.startsWith("tag/")) {
        const tag = decodeURIComponent(raw.slice("tag/".length));
        return { kind: "tag", tag };
    }

    if (raw.startsWith("episode/")) {
        const qIdx = raw.indexOf("?");
        const path = qIdx !== -1 ? raw.slice(0, qIdx) : raw;
        const qs = qIdx !== -1 ? raw.slice(qIdx + 1) : "";
        const query = qs.startsWith("q=") ? decodeURIComponent(qs.slice(2)) : undefined;

        const rest = path.slice("episode/".length);
        const slashIdx = rest.lastIndexOf("/");
        if (slashIdx !== -1) {
            const id = decodeURIComponent(rest.slice(0, slashIdx));
            const seg = rest.slice(slashIdx + 1);
            if (seg.startsWith("ch-")) {
                const chapterIdx = parseInt(seg.slice(3), 10);
                if (!isNaN(chapterIdx)) {
                    return { kind: "chapter", episodeId: id, chapterIdx };
                }
            }
            const lineIndex = parseInt(seg, 10);
            return { kind: "episode", id, lineIndex: isNaN(lineIndex) ? undefined : lineIndex, query };
        }
        return { kind: "episode", id: decodeURIComponent(rest), query };
    }

    return { kind: "welcome" };
}

export function buildEpisodeHash(id: string, lineIndex?: number, query?: string): string {
    let h = `episode/${encodeURIComponent(id)}`;
    if (lineIndex !== undefined) { h += `/${lineIndex}`; }
    if (query) { h += `?q=${encodeURIComponent(query)}`; }
    return h;
}

export function buildTagHash(tag: string): string {
    return `tag/${encodeURIComponent(tag)}`;
}
```

- [ ] **Step 4: Run tests and verify they pass**

```bash
npm run test:unit 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/router.ts src/__tests__/router.test.ts
git commit -m "feat(router): add tag route and buildTagHash"
```

---

## Task 4: Tag color utility

**Files:**
- Modify: `src/utils.ts`
- Create: `src/__tests__/utils.test.ts`

- [ ] **Step 1: Write failing tests**

Create `src/__tests__/utils.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { tagColor } from "../utils.js";

describe("tagColor", () => {
    it("returns a CSS hsl string", () => {
        const color = tagColor("יש-לי יש-לי");
        expect(color).toMatch(/^hsl\(\d+,\s*\d+%,\s*\d+%\)$/);
    });

    it("is deterministic — same input, same output", () => {
        expect(tagColor("אבגד")).toBe(tagColor("אבגד"));
        expect(tagColor("יהוקמץ בן-פסיק")).toBe(tagColor("יהוקמץ בן-פסיק"));
    });

    it("different inputs produce colors from within a fixed palette", () => {
        const colors = new Set([
            tagColor("א"),
            tagColor("ב"),
            tagColor("ג"),
            tagColor("ד"),
            tagColor("ה"),
            tagColor("ו"),
            tagColor("ז"),
            tagColor("ח"),
            tagColor("ט"),
            tagColor("י"),
            tagColor("כ"),
            tagColor("ל"),
            tagColor("מ"),
        ]);
        // At most 12 distinct colors (palette size)
        expect(colors.size).toBeLessThanOrEqual(12);
        // At least 2 distinct colors among 13 inputs
        expect(colors.size).toBeGreaterThanOrEqual(2);
    });
});
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
npm run test:unit 2>&1 | grep -A 5 "tagColor"
```

Expected: test file errors (tagColor not exported).

- [ ] **Step 3: Add `TAG_PALETTE` and `tagColor` to `utils.ts`**

Append to the end of `src/utils.ts`:

```typescript
const TAG_PALETTE = [0, 25, 50, 100, 145, 175, 200, 220, 255, 280, 315, 345];

export function tagColor(tag: string): string {
  let hash = 0;
  for (let i = 0; i < tag.length; i++) {
    hash += tag.charCodeAt(i);
  }
  const hue = TAG_PALETTE[hash % TAG_PALETTE.length];
  return `hsl(${hue}, 60%, 42%)`;
}
```

- [ ] **Step 4: Run tests and verify they pass**

```bash
npm run test:unit 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/utils.ts src/__tests__/utils.test.ts
git commit -m "feat(utils): add tagColor deterministic palette function"
```

---

## Task 5: CSS — tag pill styles

**Files:**
- Modify: `static/style.css`

- [ ] **Step 1: Add tag and tag-view styles**

Append to the end of `static/style.css` (before the closing of the file):

```css
/* ── Tag pills ───────────────────────────────────────────────────────── */
.tag {
  display: inline-block;
  padding: .15em .5em;
  border-radius: 999px;
  font-size: .75rem;
  font-weight: 600;
  background: var(--tag-color);
  color: #fff;
  cursor: pointer;
  transition: opacity .15s;
  white-space: nowrap;
  user-select: none;
}

.tag:hover {
  opacity: .8;
}

.chapter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: .3rem;
  margin-top: .3rem;
}

/* ── Tag view ─────────────────────────────────────────────────────────── */
.tag-view-heading {
  display: flex;
  align-items: center;
  gap: .75rem;
  margin-bottom: 1.5rem;
}

.tag-view-count {
  font-size: .9rem;
  color: var(--text-muted);
}

.tag-episode-section {
  margin-bottom: 1.5rem;
}

.tag-episode-title {
  display: block;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
  margin-bottom: .5rem;
  padding-bottom: .3rem;
  border-bottom: 1px solid var(--border);
  text-decoration: none;
}

.tag-episode-title:hover {
  color: var(--accent);
}

.tag-chapter-card {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: .5rem;
  padding: .4rem .75rem;
  margin-bottom: .35rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  text-decoration: none;
  transition: background .1s;
}

.tag-chapter-card:hover {
  background: var(--surface-alt);
}

.tag-chapter-card strong {
  font-weight: 600;
}

.tag-chapter-card small {
  font-size: .8rem;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

/* ── Chapter match card (in search results) ──────────────────────────── */
.chapter-match-card {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: .5rem;
  padding: .4rem .75rem;
  margin-bottom: .35rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  text-decoration: none;
  transition: background .1s;
}

.chapter-match-card:hover {
  background: var(--surface-alt);
}

.chapter-match-card strong {
  font-weight: 600;
}

.chapter-match-card small {
  font-size: .8rem;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
```

- [ ] **Step 2: Commit**

```bash
git add static/style.css
git commit -m "feat(css): add tag pill and tag view styles"
```

---

## Task 6: Loader — chapter cache and tag index

**Files:**
- Modify: `src/loader.ts`

- [ ] **Step 1: Add `buildTagIndex`, `getCachedChapters`, `getTagIndex`; build index on load**

Replace the entire `src/loader.ts` with:

```typescript
import type { Chapter, EpisodeIndex, EpisodeLines, EpisodeMetadata } from "./types.js";
import { ensure } from "./utils.js";

function dataUrl(path: string): string {
  return `data/${path}`;
}

let indexCache: EpisodeIndex | null = null;
const subtitleCache = new Map<string, EpisodeLines>();
const chapterCache = new Map<string, Chapter[]>();
let tagIndexCache: Map<string, { episodeId: string; chapterIdx: number }[]> | null = null;

export function getEpisodeChapters(id: string): Chapter[] | undefined {
  return chapterCache.get(id);
}

export function getCachedChapters(): Map<string, Chapter[]> {
  return chapterCache;
}

export function getTagIndex(): Map<string, { episodeId: string; chapterIdx: number }[]> {
  return tagIndexCache ?? new Map();
}

function buildTagIndex(
  chapterMap: Map<string, Chapter[]>,
): Map<string, { episodeId: string; chapterIdx: number }[]> {
  const index = new Map<string, { episodeId: string; chapterIdx: number }[]>();
  for (const [episodeId, chapters] of chapterMap) {
    for (let i = 0; i < chapters.length; i++) {
      const ch = chapters[i];
      if (!ch) continue;
      for (const tag of ch.tags) {
        const entries = index.get(tag) ?? [];
        entries.push({ episodeId, chapterIdx: i + 1 }); // 1-based
        index.set(tag, entries);
      }
    }
  }
  return index;
}

export type ProgressCallback = (bytesLoaded: number, totalBytes: number) => void;

async function readChunks(
  body: ReadableStream<Uint8Array>,
  total: number,
  onProgress?: ProgressCallback,
): Promise<Uint8Array[]> {
  const reader = body.getReader();
  const chunks: Uint8Array[] = [];
  let received = 0;

  while (true) {
    const { done, value } = await reader.read();

    if (done) {
      break;
    }

    chunks.push(value);
    received += value.byteLength;
    onProgress?.(received, total);
  }

  return chunks;
}

type BundleEntry = EpisodeMetadata & { lines: EpisodeLines; chapters?: Chapter[] };

async function fetchAndDecompress(
  url: string,
  onProgress?: ProgressCallback,
): Promise<BundleEntry[]> {
  const res = await fetch(url);

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const total = parseInt(res.headers.get("content-length") ?? "0", 10);
  const chunks = await readChunks(ensure(res.body, "response.body"), total, onProgress);
  const blob = new Blob(chunks);
  const stream = blob.stream().pipeThrough(new DecompressionStream("gzip"));
  const text = await new Response(stream).text();
  return JSON.parse(text);
}

async function fetchPlain(
  url: string,
  onProgress?: ProgressCallback,
): Promise<BundleEntry[]> {
  const res = await fetch(url);

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const total = parseInt(res.headers.get("content-length") ?? "0", 10);
  const chunks = await readChunks(ensure(res.body, "response.body"), total, onProgress);
  const text = new TextDecoder().decode(await new Blob(chunks).arrayBuffer());
  return JSON.parse(text);
}

async function fetchWithProgress(
  onProgress?: ProgressCallback,
): Promise<BundleEntry[]> {
  if (typeof DecompressionStream !== "undefined") {
    try {
      return await fetchAndDecompress(dataUrl("subtitles.json.gz"), onProgress);
    } catch {
      // fall through to uncompressed
    }
  }

  return await fetchPlain(dataUrl("subtitles.json"), onProgress);
}

let bundlePromise: Promise<void> | null = null;

function ensureBundle(onProgress?: ProgressCallback): Promise<void> {
  if (!bundlePromise) {
    bundlePromise = fetchWithProgress(onProgress).then((combined) => {
      indexCache = combined.map(({ id, title, num }) => ({ id, title, num }));

      for (const { id, lines, chapters } of combined) {
        subtitleCache.set(id, lines);

        if (chapters) {
          chapterCache.set(id, chapters);
        }
      }

      tagIndexCache = buildTagIndex(chapterCache);
    });
  }

  return bundlePromise;
}

export async function loadBundle(onProgress?: ProgressCallback): Promise<EpisodeIndex> {
  await ensureBundle(onProgress);
  return ensure(indexCache, "bundle not loaded");
}

export async function loadEpisode(episode: EpisodeMetadata): Promise<EpisodeLines> {
  const cached = subtitleCache.get(episode.id);

  if (cached) {
    return cached;
  }

  await ensureBundle();
  return ensure(subtitleCache.get(episode.id), `subtitles for ${episode.id} not found in bundle`);
}

export function getCachedSubtitles(): Map<string, EpisodeLines> {
  return subtitleCache;
}
```

- [ ] **Step 2: Build to verify no parse errors**

```bash
npm run build:ts 2>&1 | head -20
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add src/loader.ts
git commit -m "feat(loader): add getCachedChapters, getTagIndex, buildTagIndex"
```

---

## Task 7: Search — chapter/tag matching

**Files:**
- Modify: `src/search.ts`
- Create: `src/__tests__/search.test.ts`

- [ ] **Step 1: Write failing tests**

Create `src/__tests__/search.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { searchEpisodes, episodeHasMatch } from "../search.js";
import type { Chapter, EpisodeIndex, EpisodeLines } from "../types.js";

const INDEX: EpisodeIndex = [
    { id: "ep1", title: "פרק 1", num: 1 },
    { id: "ep2", title: "פרק 2", num: 2 },
];

const LINES: Map<string, EpisodeLines> = new Map([
    ["ep1", [{ start: 0, end: 2, text: "שלום עולם" }]],
    ["ep2", [{ start: 0, end: 2, text: "להתראות" }]],
]);

const CHAPTERS: Map<string, Chapter[]> = new Map([
    [
        "ep1",
        [
            { start: 0, end: 60, name: "פתיח", tags: [] },
            { start: 60, end: 120, name: "סצינה ראשית", tags: ["אריה לייב"] },
        ],
    ],
    [
        "ep2",
        [
            { start: 0, end: 30, name: "N/A", tags: ["אריה לייב"] },
        ],
    ],
]);

describe("episodeHasMatch — subtitle lines", () => {
    it("returns true when a line matches", () => {
        expect(episodeHasMatch(LINES.get("ep1")!, "שלום")).toBe(true);
    });

    it("returns false when no line matches", () => {
        expect(episodeHasMatch(LINES.get("ep1")!, "ביי")).toBe(false);
    });
});

describe("episodeHasMatch — with chapters", () => {
    it("returns true when chapter name matches", () => {
        expect(episodeHasMatch([], "פתיח", CHAPTERS.get("ep1"))).toBe(true);
    });

    it("returns true when chapter tag matches", () => {
        expect(episodeHasMatch([], "אריה", CHAPTERS.get("ep2"))).toBe(true);
    });

    it("returns false when neither lines nor chapters match", () => {
        expect(episodeHasMatch([], "xyz", CHAPTERS.get("ep1"))).toBe(false);
    });
});

describe("searchEpisodes — chapter matches", () => {
    it("includes chapterMatches when chapter name matches query", () => {
        const results = searchEpisodes(INDEX, LINES, "פתיח", CHAPTERS);
        const ep1 = results.find((r) => r.episode.id === "ep1");
        expect(ep1).toBeDefined();
        expect(ep1!.chapterMatches).toHaveLength(1);
        expect(ep1!.chapterMatches![0].chapter.name).toBe("פתיח");
        expect(ep1!.chapterMatches![0].chapterIdx).toBe(1);
    });

    it("includes chapterMatches when chapter tag matches query", () => {
        const results = searchEpisodes(INDEX, LINES, "אריה", CHAPTERS);
        const ep1 = results.find((r) => r.episode.id === "ep1");
        expect(ep1).toBeDefined();
        expect(ep1!.chapterMatches).toHaveLength(1);
        expect(ep1!.chapterMatches![0].chapterIdx).toBe(2);
    });

    it("includes episode in results even when only chapters match (no subtitle lines match)", () => {
        const results = searchEpisodes(INDEX, LINES, "פתיח", CHAPTERS);
        expect(results.some((r) => r.episode.id === "ep1")).toBe(true);
    });

    it("totalMatches counts chapter matches", () => {
        const results = searchEpisodes(INDEX, LINES, "אריה", CHAPTERS);
        const ep1 = results.find((r) => r.episode.id === "ep1");
        expect(ep1!.totalMatches).toBe(1); // 1 chapter match, 0 subtitle matches
    });

    it("works without chapterMap (backwards compatible)", () => {
        const results = searchEpisodes(INDEX, LINES, "שלום");
        expect(results).toHaveLength(1);
        expect(results[0].episode.id).toBe("ep1");
    });
});
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
npm run test:unit 2>&1 | grep -E "(FAIL|PASS|search)" | head -20
```

Expected: failures for search tests.

- [ ] **Step 3: Update `search.ts`**

Replace the entire `src/search.ts` with:

```typescript
import type { Chapter, ChapterMatch, DisplayEntry, EpisodeIndex, EpisodeLines, EpisodeSearchResult } from "./types.js";

export const MIN_QUERY_LENGTH = 2;

/** Lines of context shown above and below each match. */
export const CONTEXT_LINES = 1;

/** Maximum display entries shown per episode group before "show more". */
export const MAX_ENTRIES_PER_GROUP = 3;

/**
 * Maximum total lines in a single merged display entry.
 * Prevents a dense cluster of matches from producing an enormous block.
 */
export const MAX_MERGED_LINES = 10;

/**
 * When true, adjacent/overlapping context windows are merged into a single
 * display entry. When false, each match produces its own independent entry.
 */
export const MERGE_CONTEXT_ENTRIES = true;

/** Quick check: does any line or chapter in this episode match the query? */
export function episodeHasMatch(
  lines: EpisodeLines,
  query: string,
  chapters?: Chapter[],
): boolean {
  const q = query.trim().toLowerCase();

  if (q.length < MIN_QUERY_LENGTH) {
    return false;
  }

  if (lines.some((l) => l.text.toLowerCase().includes(q))) {
    return true;
  }

  if (chapters) {
    return chapters.some(
      (ch) =>
        ch.name.toLowerCase().includes(q) ||
        ch.tags.some((t) => t.toLowerCase().includes(q)),
    );
  }

  return false;
}

/**
 * Given a sorted list of matching line indices, build merged display entries.
 *
 * Each match expands to a window [idx - C, idx + C]. Adjacent or overlapping
 * windows are merged. The total line count of a merged entry is capped at
 * MAX_MERGED_LINES to prevent enormous blocks from dense match clusters.
 */
function buildDisplayEntries(
  matchIndices: number[],
  totalLines: number,
): DisplayEntry[] {
  if (matchIndices.length === 0) {
    return [];
  }

  const C = CONTEXT_LINES;
  const entries: DisplayEntry[] = [];

  for (const idx of matchIndices) {
    const start = Math.max(0, idx - C);
    const end = Math.min(totalLines - 1, idx + C);

    const prev = entries.at(-1);
    if (MERGE_CONTEXT_ENTRIES && prev && start <= prev.endIdx + 1) {
      const newEnd = Math.min(
        Math.max(prev.endIdx, end),
        prev.startIdx + MAX_MERGED_LINES - 1,
      );
      prev.endIdx = newEnd;
      if (idx <= prev.endIdx) {
        prev.matchIndices.add(idx);
      }
    } else {
      entries.push({ startIdx: start, endIdx: end, matchIndices: new Set([idx]) });
    }
  }

  return entries;
}

export function searchEpisodes(
  index: EpisodeIndex,
  subtitles: Map<string, EpisodeLines>,
  query: string,
  chapterMap?: Map<string, Chapter[]>,
): EpisodeSearchResult[] {
  const q = query.trim().toLowerCase();

  if (q.length < MIN_QUERY_LENGTH) {
    return [];
  }

  const results: EpisodeSearchResult[] = [];

  for (const episode of index) {
    const lines = subtitles.get(episode.id);

    if (!lines) {
      continue;
    }

    const matchIndices: number[] = [];
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (!line) continue;
      if (line.text.toLowerCase().includes(q)) {
        matchIndices.push(i);
      }
    }

    const chapterMatches: ChapterMatch[] = [];
    const chapters = chapterMap?.get(episode.id) ?? [];
    for (let i = 0; i < chapters.length; i++) {
      const ch = chapters[i];
      if (!ch) continue;
      const nameMatch = ch.name.toLowerCase().includes(q);
      const tagMatch = ch.tags.some((t) => t.toLowerCase().includes(q));
      if (nameMatch || tagMatch) {
        chapterMatches.push({ chapterIdx: i + 1, chapter: ch });
      }
    }

    if (matchIndices.length > 0 || chapterMatches.length > 0) {
      results.push({
        episode,
        entries: buildDisplayEntries(matchIndices, lines.length),
        totalMatches: matchIndices.length + chapterMatches.length,
        chapterMatches: chapterMatches.length > 0 ? chapterMatches : undefined,
      });
    }
  }

  return results;
}
```

- [ ] **Step 4: Run tests and verify they pass**

```bash
npm run test:unit 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/search.ts src/__tests__/search.test.ts
git commit -m "feat(search): match chapter names and tags; add chapterMatches to results"
```

---

## Task 8: Sidebar — pass chapters to `episodeHasMatch`

**Files:**
- Modify: `src/sidebar.ts`

- [ ] **Step 1: Update `updateSidebarState` to accept and pass `chapterMap`**

Replace `src/sidebar.ts` with:

```typescript
import type { Chapter, EpisodeIndex, EpisodeLines } from "./types.js";
import { episodeHasMatch, MIN_QUERY_LENGTH } from "./search.js";

export function renderSidebar(
  container: HTMLElement,
  index: EpisodeIndex,
): void {
  const ul = document.createElement("ul");
  ul.className = "sidebar-list";
  for (const ep of index) {
    const li = document.createElement("li");
    li.className = "sidebar-item";
    li.dataset["epId"] = ep.id;

    const a = document.createElement("a");
    a.className = "sidebar-link";
    a.href = `#episode/${ep.id}`;
    a.textContent = ep.title;
    a.title = ep.title;

    li.appendChild(a);
    ul.appendChild(li);
  }
  container.replaceChildren(ul);
}

/**
 * Update sidebar item states (current / has-match / no-match) without
 * re-creating the DOM.
 */
export function updateSidebarState(
  container: HTMLElement,
  subtitles: Map<string, EpisodeLines>,
  query: string,
  currentEpisodeId?: string,
  chapterMap?: Map<string, Chapter[]>,
): void {
  const q = query.trim().toLowerCase();
  const filtering = q.length >= MIN_QUERY_LENGTH && subtitles.size > 0;

  const listEl = container.querySelector<HTMLElement>(".sidebar-list");
  listEl?.classList.toggle("filtered", filtering);

  let currentEl: HTMLElement | null = null;

  for (const li of container.querySelectorAll<HTMLElement>(".sidebar-item")) {
    const epId = li.dataset["epId"] ?? "";

    const isCurrent = epId === currentEpisodeId;
    li.classList.toggle("current", isCurrent);

    if (isCurrent) {
      currentEl = li;
    }

    if (filtering) {
      const lines = subtitles.get(epId);
      const chapters = chapterMap?.get(epId);
      const hasMatch = lines ? episodeHasMatch(lines, q, chapters) : false;
      li.classList.toggle("has-match", hasMatch);
      li.classList.toggle("no-match", !hasMatch);
    } else {
      li.classList.remove("has-match", "no-match");
    }
  }

  currentEl?.scrollIntoView({ block: "nearest" });
}
```

- [ ] **Step 2: Run tests and verify they still pass**

```bash
npm run test:unit 2>&1 | tail -10
```

Expected: all tests pass (the sidebar tests don't pass `chapterMap`, which is fine — it's optional).

- [ ] **Step 3: Commit**

```bash
git add src/sidebar.ts
git commit -m "feat(sidebar): pass chapterMap to episodeHasMatch for chapter/tag filtering"
```

---

## Task 9: Episode view — tag pills and filter update

**Files:**
- Modify: `src/views/episode.ts`

- [ ] **Step 1: Replace `src/views/episode.ts`**

```typescript
import type { Chapter, EpisodeMetadata, EpisodeLines, Line } from "../types.js";
import { MIN_QUERY_LENGTH } from "../search.js";
import { applyHighlights, clearHighlights } from "../highlight.js";
import { formatTime, tagColor } from "../utils.js";
import { buildTagHash } from "../router.js";

export interface ChapterBlockData {
  el: HTMLElement;
  headerEl: HTMLElement;
  lineEls: HTMLElement[];
  chapter: Chapter;
  chapterIdx: number; // 1-based
}

export interface RenderResult {
  listEl: HTMLElement;
  lineEls: HTMLElement[];
  chapterBlocks?: ChapterBlockData[];
}

export function renderEpisode(
    container: HTMLElement,
    episode: EpisodeMetadata,
    lines: EpisodeLines,
    query: string,
    scrollToLine?: number,
    chapters?: Chapter[],
): RenderResult {
  clearHighlights();
  container.replaceChildren();

  const header = document.createElement("div");
  header.className = "episode-header";
  const h2 = document.createElement("h2");
  const titleLink = document.createElement("a");
  titleLink.href = `#episode/${encodeURIComponent(episode.id)}`;
  titleLink.textContent = episode.title;
  h2.appendChild(titleLink);
  header.appendChild(h2);
  container.appendChild(header);

  const list = document.createElement("div");
  list.className = "transcript-list";
  container.appendChild(list);

  const lineEls: HTMLElement[] = [];

  let chapterBlocks: ChapterBlockData[] | undefined;

  if (chapters && chapters.length > 0) {
    chapterBlocks = renderWithChapters(list, lines, chapters, lineEls, episode.id);
  } else {
    renderFlat(list, lines, lineEls);
  }

  applyQueryFilter(list, lineEls, lines, query, chapterBlocks);

  if (scrollToLine !== undefined) {
    const target = lineEls[scrollToLine];

    if (target) {
      target.classList.add("highlighted");
      requestAnimationFrame(() => {
        target.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    }
  }

  return { listEl: list, lineEls, chapterBlocks };
}

function makeLineEl(line: Line, idx: number): HTMLElement {
  const el = document.createElement("div");
  el.className = "transcript-line";
  el.dataset["idx"] = String(idx);

  const ts = document.createElement("time");
  ts.className = "ts";
  ts.textContent = formatTime(line.start);

  const text = document.createElement("span");
  text.className = "text";
  text.textContent = line.text;

  el.appendChild(ts);
  el.appendChild(text);
  return el;
}

function makeTagEl(tag: string): HTMLElement {
  const span = document.createElement("span");
  span.className = "tag";
  span.textContent = tag;
  span.style.setProperty("--tag-color", tagColor(tag));
  return span;
}

function renderFlat(
    list: HTMLElement,
    lines: EpisodeLines,
    lineEls: HTMLElement[],
): void {
  const frag = document.createDocumentFragment();

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line) {
      continue;
    }

    const el = makeLineEl(line, i);
    frag.appendChild(el);
    lineEls.push(el);
  }

  list.appendChild(frag);
}

function countLinesPerChapter(lines: EpisodeLines, chapters: Chapter[]): number[] {
  const counts = new Array<number>(chapters.length).fill(0);
  let chapIdx = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line) {
      continue;
    }

    while (chapIdx + 1 < chapters.length && chapters[chapIdx + 1].start <= line.start) {
      chapIdx++;
    }

    counts[chapIdx]++;
  }

  return counts;
}

function renderWithChapters(
    list: HTMLElement,
    lines: EpisodeLines,
    chapters: Chapter[],
    lineEls: HTMLElement[],
    episodeId: string,
): ChapterBlockData[] {
  const frag = document.createDocumentFragment();
  const lineCounts = countLinesPerChapter(lines, chapters);

  const chapterBlocks: ChapterBlockData[] = chapters.map((ch, i) => {
    const chapterHref = `#episode/${encodeURIComponent(episodeId)}/ch-${i + 1}`;

    const block = document.createElement("div");
    block.className = "chapter-block";
    block.id = `ch-${i + 1}`;

    const hasLines = lineCounts[i] > 0;

    const headerEl = hasLines
        ? Object.assign(document.createElement("a"), { href: chapterHref })
        : document.createElement("div");
    headerEl.className = "chapter-block-header";

    if (ch.name) {
      const titleEl = document.createElement("strong");
      titleEl.textContent = ch.name;
      headerEl.appendChild(titleEl);
    }

    const timeEl = document.createElement("small");
    timeEl.textContent = `${formatTime(ch.start)} – ${formatTime(ch.end)}`;
    headerEl.appendChild(timeEl);

    if (ch.tags.length > 0) {
      const tagsEl = document.createElement("div");
      tagsEl.className = "chapter-tags";
      for (const tag of ch.tags) {
        tagsEl.appendChild(makeTagEl(tag));
      }
      headerEl.appendChild(tagsEl);
    }

    block.appendChild(headerEl);

    frag.appendChild(block);
    return { el: block, headerEl: headerEl, lineEls: [], chapter: ch, chapterIdx: i + 1 };
  });

  let chapIdx = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line) {
      continue;
    }

    while (chapIdx + 1 < chapters.length && chapters[chapIdx + 1].start <= line.start) {
      chapIdx++;
    }

    const el = makeLineEl(line, i);
    chapterBlocks[chapIdx].el.appendChild(el);
    chapterBlocks[chapIdx].lineEls.push(el);
    lineEls.push(el);
  }

  list.appendChild(frag);
  return chapterBlocks;
}

/**
 * Filter visible lines and refresh highlights in-place.
 * Called both on initial render and when the user types in the search bar
 * while in the episode view.
 */
export function applyQueryFilter(
    list: HTMLElement,
    lineEls: HTMLElement[],
    lines: EpisodeLines,
    query: string,
    chapterBlocks?: ChapterBlockData[],
): void {
  clearHighlights();

  const q = query.trim().toLowerCase();
  const filtering = q.length >= MIN_QUERY_LENGTH;

  for (let i = 0; i < lineEls.length; i++) {
    const el = lineEls[i];
    const line = lines[i];
    if (!el || !line) {
      continue;
    }

    const matches = filtering ? line.text.toLowerCase().includes(q) : true;
    el.classList.toggle("hidden", !matches);
  }

  if (chapterBlocks) {
    for (const block of chapterBlocks) {
      updateChapterBlock(block, q, filtering);
    }
  }

  if (filtering) {
    applyHighlights(query, list);
  }
}

function chapterMatchesQuery(chapter: Chapter, q: string): boolean {
  if (chapter.name.toLowerCase().includes(q)) return true;
  return chapter.tags.some((t) => t.toLowerCase().includes(q));
}

function updateChapterBlock(block: ChapterBlockData, q: string, filtering: boolean): void {
  const hasVisibleLines = block.lineEls.some((el) => !el.classList.contains("hidden"));
  const chapterSelfMatch = filtering && chapterMatchesQuery(block.chapter, q);

  if (filtering && !hasVisibleLines && !chapterSelfMatch) {
    block.el.hidden = true;
    return;
  }

  block.el.hidden = false;

  if (!block.chapter.name) {
    // Unnamed chapters always show their timestamp as a divider when the block is visible.
    block.headerEl.hidden = false;
    return;
  }

  // Named chapters: show header when the chapter itself matches (surfaces the match reason).
  // Otherwise preserve old behavior: header hidden when lines are visible (lines provide context).
  block.headerEl.hidden = !chapterSelfMatch && hasVisibleLines;
}
```

Note: the delegated tag click listener for this view is added globally in `main.ts` (Task 12), so no per-element listener is needed here.

- [ ] **Step 2: Build to verify no errors**

```bash
npm run build:ts 2>&1 | head -20
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add src/views/episode.ts
git commit -m "feat(episode): render tag pills on chapter headers; filter chapters by name/tag"
```

---

## Task 10: Results view — chapter match cards

**Files:**
- Modify: `src/views/results.ts`

- [ ] **Step 1: Replace `src/views/results.ts`**

```typescript
import type { ChapterMatch, EpisodeSearchResult, EpisodeLines } from "../types.js";
import { MAX_ENTRIES_PER_GROUP } from "../search.js";
import { applyHighlights } from "../highlight.js";
import { buildEpisodeHash } from "../router.js";
import { formatTime, tagColor } from "../utils.js";

const noResultsEl = document.createElement("p");
noResultsEl.className = "state-message";
noResultsEl.textContent = "לא נמצאו תוצאות";

export function renderResults(
  container: HTMLElement,
  results: EpisodeSearchResult[],
  subtitles: Map<string, EpisodeLines>,
  query: string,
): void {
  container.replaceChildren();

  if (results.length === 0) {
    container.replaceChildren(noResultsEl);
    return;
  }

  const totalMatches = results.reduce((s, r) => s + r.totalMatches, 0);
  const summary = document.createElement("p");
  summary.className = "results-summary";
  summary.textContent = `${totalMatches} תוצאות ב־${results.length} פרקים`;
  container.appendChild(summary);

  const frag = document.createDocumentFragment();

  for (const { episode, entries, totalMatches: epTotal, chapterMatches } of results) {
    const lines = subtitles.get(episode.id) ?? [];

    const section = document.createElement("div");
    section.className = "results-episode";

    const header = document.createElement("div");
    header.className = "results-episode-header";

    const titleEl = document.createElement("a");
    titleEl.className = "results-episode-title";
    titleEl.href = `#${buildEpisodeHash(episode.id, undefined, query)}`;
    titleEl.textContent = episode.title;

    const countEl = document.createElement("span");
    countEl.className = "results-episode-count";
    countEl.textContent = `${epTotal} תוצאות`;

    header.appendChild(titleEl);
    header.appendChild(countEl);
    section.appendChild(header);

    if (chapterMatches && chapterMatches.length > 0) {
      for (const match of chapterMatches) {
        section.appendChild(renderChapterMatchCard(match, episode.id));
      }
    }

    const visible = entries.slice(0, MAX_ENTRIES_PER_GROUP);
    const overflow = entries.slice(MAX_ENTRIES_PER_GROUP);

    for (const entry of visible) {
      section.appendChild(renderEntry(entry, lines, episode.id, query));
    }

    if (overflow.length > 0) {
      const btn = document.createElement("button");
      btn.className = "show-more-btn";
      btn.textContent = `הצג עוד ${overflow.length} תוצאות`;
      btn.addEventListener("click", () => {
        const frag = document.createDocumentFragment();
        for (const entry of overflow) {
          frag.appendChild(renderEntry(entry, lines, episode.id, query));
        }
        btn.replaceWith(frag);
        applyHighlights(query, container);
      });
      section.appendChild(btn);
    }

    frag.appendChild(section);
  }

  container.appendChild(frag);
}

function renderChapterMatchCard(match: ChapterMatch, episodeId: string): HTMLElement {
  const card = document.createElement("a");
  card.className = "chapter-match-card";
  card.href = `#episode/${encodeURIComponent(episodeId)}/ch-${match.chapterIdx}`;

  if (match.chapter.name) {
    const nameEl = document.createElement("strong");
    nameEl.textContent = match.chapter.name;
    card.appendChild(nameEl);
  }

  const timeEl = document.createElement("small");
  timeEl.textContent = `${formatTime(match.chapter.start)} – ${formatTime(match.chapter.end)}`;
  card.appendChild(timeEl);

  if (match.chapter.tags.length > 0) {
    const tagsEl = document.createElement("div");
    tagsEl.className = "chapter-tags";
    for (const tag of match.chapter.tags) {
      const tagEl = document.createElement("span");
      tagEl.className = "tag";
      tagEl.textContent = tag;
      tagEl.style.setProperty("--tag-color", tagColor(tag));
      tagsEl.appendChild(tagEl);
    }
    card.appendChild(tagsEl);
  }

  return card;
}

function renderEntry(
  entry: import("../types.js").DisplayEntry,
  lines: EpisodeLines,
  episodeId: string,
  query: string,
): HTMLElement {
  const el = document.createElement("div");
  el.className = "result-entry";

  for (let i = entry.startIdx; i <= entry.endIdx; i++) {
    const line = lines[i];
    if (!line) continue;

    const isMatch = entry.matchIndices.has(i);
    const row = document.createElement("a");
    row.className = `result-line ${isMatch ? "match" : "context"}`;
    row.href = `#${buildEpisodeHash(episodeId, i, query)}`;

    const ts = document.createElement("time");
    ts.className = "ts";
    ts.textContent = formatTime(line.start);

    const text = document.createElement("span");
    text.className = "text";
    text.textContent = line.text;

    row.appendChild(ts);
    row.appendChild(text);
    el.appendChild(row);
  }

  return el;
}
```

- [ ] **Step 2: Build to verify**

```bash
npm run build:ts 2>&1 | head -20
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add src/views/results.ts
git commit -m "feat(results): render chapter match cards above subtitle entries"
```

---

## Task 11: Tag view

**Files:**
- Create: `src/views/tag.ts`

- [ ] **Step 1: Create `src/views/tag.ts`**

```typescript
import type { Chapter, EpisodeIndex } from "../types.js";
import { formatTime, tagColor } from "../utils.js";

function makeTagEl(tag: string): HTMLElement {
  const span = document.createElement("span");
  span.className = "tag";
  span.textContent = tag;
  span.style.setProperty("--tag-color", tagColor(tag));
  return span;
}

export function renderTagView(
  container: HTMLElement,
  tag: string,
  tagIndex: Map<string, { episodeId: string; chapterIdx: number }[]>,
  episodeIndex: EpisodeIndex,
  chapterMap: Map<string, Chapter[]>,
): void {
  container.replaceChildren();

  const entries = tagIndex.get(tag) ?? [];

  const heading = document.createElement("div");
  heading.className = "tag-view-heading";
  heading.appendChild(makeTagEl(tag));
  const countEl = document.createElement("span");
  countEl.className = "tag-view-count";
  countEl.textContent = `${entries.length} סצינות`;
  heading.appendChild(countEl);
  container.appendChild(heading);

  // Group entries by episodeId, preserving episode order
  const byEpisode = new Map<string, { episodeId: string; chapterIdx: number }[]>();
  for (const entry of entries) {
    const list = byEpisode.get(entry.episodeId) ?? [];
    list.push(entry);
    byEpisode.set(entry.episodeId, list);
  }

  const frag = document.createDocumentFragment();

  for (const ep of episodeIndex) {
    const epEntries = byEpisode.get(ep.id);
    if (!epEntries) continue;

    const chapters = chapterMap.get(ep.id) ?? [];

    const section = document.createElement("div");
    section.className = "tag-episode-section";

    const epLink = document.createElement("a");
    epLink.className = "tag-episode-title";
    epLink.href = `#episode/${encodeURIComponent(ep.id)}`;
    epLink.textContent = ep.title;
    section.appendChild(epLink);

    for (const { chapterIdx } of epEntries) {
      const ch = chapters[chapterIdx - 1]; // chapterIdx is 1-based
      if (!ch) continue;

      const card = document.createElement("a");
      card.className = "tag-chapter-card";
      card.href = `#episode/${encodeURIComponent(ep.id)}/ch-${chapterIdx}`;

      if (ch.name) {
        const nameEl = document.createElement("strong");
        nameEl.textContent = ch.name;
        card.appendChild(nameEl);
      }

      const timeEl = document.createElement("small");
      timeEl.textContent = `${formatTime(ch.start)} – ${formatTime(ch.end)}`;
      card.appendChild(timeEl);

      if (ch.tags.length > 0) {
        const tagsEl = document.createElement("div");
        tagsEl.className = "chapter-tags";
        for (const t of ch.tags) {
          tagsEl.appendChild(makeTagEl(t));
        }
        card.appendChild(tagsEl);
      }

      section.appendChild(card);
    }

    frag.appendChild(section);
  }

  container.appendChild(frag);
}
```

- [ ] **Step 2: Build to verify**

```bash
npm run build:ts 2>&1 | head -20
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add src/views/tag.ts
git commit -m "feat: add tag filter view (renderTagView)"
```

---

## Task 12: Wire up `main.ts`

**Files:**
- Modify: `src/main.ts`

- [ ] **Step 1: Update imports**

At the top of `src/main.ts`, update/add the following imports. Replace the existing import block with:

```typescript
import type {EpisodeIndex, EpisodeLines, EpisodeMetadata} from "./types.js";
import {parseHash, buildEpisodeHash, buildTagHash} from "./router.js";
import type {Route} from "./router.js";
import {loadBundle, loadEpisode, getCachedSubtitles, getEpisodeChapters, getCachedChapters, getTagIndex} from "./loader.js";
import {searchEpisodes, MIN_QUERY_LENGTH} from "./search.js";
import {applyHighlights, clearHighlights} from "./highlight.js";
import {renderSidebar, updateSidebarState} from "./sidebar.js";
import {renderWelcome} from "./views/list.js";
import {renderResults} from "./views/results.js";
import {renderEpisode, applyQueryFilter} from "./views/episode.js";
import type {ChapterBlockData} from "./views/episode.js";
import {renderTagView} from "./views/tag.js";
import {ensure} from "./utils.js";
import {measure} from "./perf.js";
```

- [ ] **Step 2: Add delegated tag click listener on `mainPaneEl`**

After the `backdropEl.addEventListener("click", closeSidebar);` line (around line 104 in the original), add:

```typescript
mainPaneEl.addEventListener("click", (e) => {
    const tagEl = (e.target as Element).closest<HTMLElement>(".tag");
    if (!tagEl) return;
    const tag = tagEl.textContent ?? "";
    if (tag) {
        e.preventDefault();
        window.location.hash = `#${buildTagHash(tag)}`;
    }
});
```

- [ ] **Step 3: Update `syncSidebar` to pass `getCachedChapters()`**

Find the `syncSidebar` function (around line 169) and update it:

```typescript
function syncSidebar() {
    const activeId =
        currentRoute.kind === "episode" ? currentRoute.id :
        currentRoute.kind === "chapter" ? currentRoute.episodeId :
        undefined;
    updateSidebarState(sidebarEl, getCachedSubtitles(), queryEl.value, activeId, getCachedChapters());
}
```

- [ ] **Step 4: Update `setBreadcrumb` to handle the tag route**

In the `setBreadcrumb` function, add a tag case before the final closing brace. After the `if (route.kind === "chapter") { ... }` block, add:

```typescript
    if (route.kind === "tag") {
        breadcrumbEl.replaceChildren(bcHomeLink, makeSep(), makeSpan(`תג: ${route.tag}`));
        return;
    }
```

- [ ] **Step 5: Update `handleRoute` to handle the tag route**

At the end of the `handleRoute` function, before the closing `}`, add:

```typescript
    if (route.kind === "tag") {
        renderTagView(
            mainPaneEl,
            route.tag,
            getTagIndex(),
            episodeIndex,
            getCachedChapters(),
        );
        mainPaneEl.scrollTop = savedScroll;
        return;
    }
```

- [ ] **Step 6: Update all `searchEpisodes` calls to pass `getCachedChapters()`**

There are three calls to `searchEpisodes` in `main.ts`. Update each one to add `getCachedChapters()` as the fourth argument:

**In `handleRoute` results branch:**
```typescript
        const results = measure("search", () => searchEpisodes(episodeIndex, subs, route.query, getCachedChapters()));
```

**In the `queryEl` input handler (search while typing):**
```typescript
        const results = measure("search", () => searchEpisodes(episodeIndex, subs, q, getCachedChapters()));
```

**In `init` (re-render after load):**
```typescript
        const results = measure("search", () => {
            if (currentRoute.kind === "results") {
                return searchEpisodes(episodeIndex, subs, currentRoute.query, getCachedChapters());
            }
            return [];
        });
```

- [ ] **Step 7: Full build**

```bash
npm run build 2>&1 | tail -20
```

Expected: data build succeeds, TypeScript build succeeds, no errors.

- [ ] **Step 8: Run all unit tests**

```bash
npm run test:unit 2>&1
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add src/main.ts
git commit -m "feat(main): wire tag route, delegated tag nav, chapter-aware search and sidebar"
```

---

## Task 13: Manual verification

- [ ] **Step 1: Start dev server**

```bash
npm run dev
```

Open `http://localhost:3000` in a browser.

- [ ] **Step 2: Verify tag pills appear on chapters**

Navigate to an episode that has chapters with tags (e.g., פרק 1). Confirm:
- Tag pills appear below the chapter name/timestamp in the header
- Pills have distinct background colors

- [ ] **Step 3: Verify tag click navigates to tag view**

Click a tag pill. Confirm:
- URL changes to `#tag/{tagName}`
- Tag view renders: heading with tag + count, episodes grouped, chapter cards

- [ ] **Step 4: Verify tag view chapter cards link to chapters**

Click a chapter card in the tag view. Confirm it navigates to the episode/chapter view.

- [ ] **Step 5: Verify text search matches chapter titles and tags**

Type a character name (e.g., "יש-לי") in the search box. Confirm:
- Results include chapter match cards (above subtitle entries) for episodes where that name appears as a chapter name or tag

- [ ] **Step 6: Verify episode view filter works on chapter name/tag**

Navigate to an episode with chapters. Type a tag name in the search box. Confirm:
- Chapters whose name or tag matches are shown (even if their subtitle lines don't match)
- Other chapters are hidden

- [ ] **Step 7: Verify breadcrumb**

In the tag view, confirm breadcrumb shows `ראשי › תג: {tagName}`.

- [ ] **Step 8: Verify browser back works**

From tag view → chapter card → confirm browser back returns to tag view.
