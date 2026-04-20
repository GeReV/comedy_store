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
