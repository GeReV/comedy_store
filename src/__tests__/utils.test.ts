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
            tagColor("א"), tagColor("ב"), tagColor("ג"), tagColor("ד"),
            tagColor("ה"), tagColor("ו"), tagColor("ז"), tagColor("ח"),
            tagColor("ט"), tagColor("י"), tagColor("כ"), tagColor("ל"),
            tagColor("מ"),
        ]);
        expect(colors.size).toBeLessThanOrEqual(12);
        expect(colors.size).toBeGreaterThanOrEqual(2);
    });
});
