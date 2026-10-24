/**
 * The curated cover-photo prompts: palette colours, neutral fallback and the
 * topic nod (cut when long).
 */
import { describe, expect, it } from "vitest";
import en from "@/i18n/locales/en.json";
import type { CoverIdeasPalette } from "@/schemas/cover-prompt-ideas";
import {
  buildCatalogueIdeas,
  type CoverIdeasTranslator,
} from "./cover-prompt-catalogue";

const PALETTE: CoverIdeasPalette = {
  name: "Night Blue",
  mode: "dark",
  background: "#0b1020",
  primary: "#38bdf8",
  accent: "#fde68a",
};

const t: CoverIdeasTranslator = (key, values = {}) => {
  const template = key
    .split(".")
    .reduce<unknown>(
      (node, part) => (node as Record<string, unknown>)[part],
      en.create.coverIdeas,
    ) as string;
  return template.replace(
    /\{(\w+)\}/g,
    (_, name: string) => values[name] ?? "",
  );
};

describe("buildCatalogueIdeas", () => {
  /** Scenario: The Slide 1 photo shows curated suggestions for the topic and palette */
  it("fills the palette colours and ends each idea with the topic", () => {
    const ideas = buildCatalogueIdeas(t, {
      topic: "  AI   at work ",
      palette: PALETTE,
    });

    expect(ideas).toHaveLength(6);
    expect(ideas[0]).toBe(
      "Half-body portrait facing the camera, slight smile, plain #0b1020 background, soft studio light, with one element that hints at “AI at work”",
    );
    expect(ideas[1]).toContain("in the Night Blue palette");
    expect(ideas[2]).toContain("details in the #fde68a colour");
    expect(ideas.every((idea) => idea.endsWith("“AI at work”"))).toBe(true);
  });

  /** Scenario: Without a palette or a topic the suggestions stay generic */
  it("uses neutral colours and no topic nod", () => {
    const ideas = buildCatalogueIdeas(t, { topic: "   ", palette: null });

    expect(ideas[0]).toBe(
      "Half-body portrait facing the camera, slight smile, plain neutral background, soft studio light",
    );
    expect(ideas[1]).toContain("in the neutral palette");
    expect(ideas[2]).toContain("details in the accent colour");
    expect(ideas.some((idea) => idea.includes("hints at"))).toBe(false);
  });

  /** Scenario: The Slide 1 photo shows curated suggestions for the topic and palette */
  it("cuts a long topic at 80 characters", () => {
    const topic = `${"a".repeat(79)} ${"b".repeat(30)}`;

    const [first] = buildCatalogueIdeas(t, { topic, palette: PALETTE });

    expect(first).toContain(`“${"a".repeat(79)}…”`);
  });

  /** Scenario: The Slide 1 photo shows curated suggestions for the topic and palette */
  it("keeps a topic of exactly 80 characters whole", () => {
    const topic = "c".repeat(80);

    const [first] = buildCatalogueIdeas(t, { topic, palette: PALETTE });

    expect(first).toContain(`“${topic}”`);
  });
});
