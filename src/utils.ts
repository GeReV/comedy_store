import type { Line } from "./types.js";
import { buildTagHash } from "./router.js";

export function makeTagEl(tag: string): HTMLAnchorElement {
  const a = document.createElement("a");
  a.className = "tag";
  a.textContent = tag;
  a.href = `#${buildTagHash(tag)}`;
  a.style.setProperty("--tag-color", tagColor(tag));
  return a;
}

export function makeLineEl(line: Line, className: string, idx?: number): HTMLElement {
  const el = document.createElement("div");
  el.className = className;
  if (idx !== undefined) {
    el.dataset["idx"] = String(idx);
  }
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

export function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

export function ensure<T>(val: T | null | undefined, description: string): T {
  assert(val != null, `Required value missing: ${description}`);
  return val;
}

export function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) {
    return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

const TAG_PALETTE = [0, 25, 50, 100, 145, 175, 200, 220, 255, 280, 315, 345];

export function tagColor(tag: string): string {
  let hash = 0;
  for (let i = 0; i < tag.length; i++) {
    hash += tag.charCodeAt(i);
  }
  const hue = TAG_PALETTE[hash % TAG_PALETTE.length];
  return `hsl(${hue}, 60%, 42%)`;
}