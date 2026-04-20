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
