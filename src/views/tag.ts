import type { Chapter, EpisodeIndex, EpisodeLines } from "../types.js";
import { formatTime, makeLineEl, makeTagEl } from "../utils.js";

export function renderTagView(
  container: HTMLElement,
  tag: string,
  tagIndex: Map<string, { episodeId: string; chapterIdx: number }[]>,
  episodeIndex: EpisodeIndex,
  chapterMap: Map<string, Chapter[]>,
  subtitles: Map<string, EpisodeLines>,
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

    const lines = subtitles.get(ep.id) ?? [];

    for (const { chapterIdx } of epEntries) {
      const ch = chapters[chapterIdx - 1]; // chapterIdx is 1-based
      if (!ch) continue;

      const card = document.createElement("div");
      card.className = "tag-chapter-card";

      const cardLink = document.createElement("a");
      cardLink.className = "tag-chapter-card-link";
      cardLink.href = `#episode/${encodeURIComponent(ep.id)}/ch-${chapterIdx}`;

      const cardHeader = document.createElement("div");
      cardHeader.className = "tag-chapter-card-header";

      if (ch.name) {
        const nameEl = document.createElement("strong");
        nameEl.textContent = ch.name;
        cardHeader.appendChild(nameEl);
      }

      const timeEl = document.createElement("small");
      timeEl.textContent = `${formatTime(ch.start)} – ${formatTime(ch.end)}`;
      cardHeader.appendChild(timeEl);

      cardLink.appendChild(cardHeader);

      const chapterLines = lines.filter((l) => l.start >= ch.start && l.start < ch.end);
      if (chapterLines.length > 0) {
        const linesEl = document.createElement("div");
        linesEl.className = "tag-chapter-lines";
        for (const l of chapterLines) {
          linesEl.appendChild(makeLineEl(l, "transcript-line"));
        }
        cardLink.appendChild(linesEl);
      }

      card.appendChild(cardLink);

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
