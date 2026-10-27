/**
 * The curated cover-photo prompts (AE-0509, varied by AE-0562): six scenes
 * distinct on every dimension, colour words instead of hex, a theme prop from
 * the topic words, stable per seed and reshuffled per round.
 */
import { describe, expect, it } from "vitest";
import en from "@/i18n/locales/en.json";
import { COVER_IDEA_DIMENSIONS } from "@/constants/cover-prompt-ideas";
import type { CoverIdeasPalette } from "@/schemas/cover-prompt-ideas";
import { colourName } from "./colour-name";
import {
  buildCatalogueIdeas,
  topicTheme,
  type CoverIdeasTranslator,
} from "./cover-prompt-catalogue";

const PALETTE: CoverIdeasPalette = {
  name: "Mono Indigo",
  mode: "dark",
  background: "#0b0b14",
  primary: "#6366f1",
  accent: "#4f46e5",
};
const TOPIC = "A Meta venceu a corrida dos agentes de IA pessoais?";
const HEX = /#[0-9a-f]{3,6}\b/i;
const pools = en.create.coverIdeas.pools as Record<
  string,
  Record<string, string>
>;
const aiProps = Object.values(en.create.coverIdeas.props.ai);

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

function build(
  seed: string,
  round = 0,
  palette: CoverIdeasPalette | null = PALETTE,
): string[] {
  return buildCatalogueIdeas(t, { topic: TOPIC, palette, seed, round });
}

describe("buildCatalogueIdeas", () => {
  /** Scenario: The six curated suggestions differ on every dimension */
  it("shows six ideas that never share an option of any dimension", () => {
    const ideas = build("carousel-1");

    expect(ideas).toHaveLength(6);
    for (const dimension of COVER_IDEA_DIMENSIONS) {
      const used = ideas.map((idea) =>
        Object.values(pools[dimension] ?? {}).filter((option) =>
          idea.toLowerCase().includes(option.toLowerCase()),
        ),
      );
      expect(used.every((options) => options.length >= 1)).toBe(true);
      expect(new Set(used.map((options) => options[0])).size).toBe(6);
    }
  });

  /** Scenario: Suggestions name colours in words, never hex codes */
  it("names the palette tones in words", () => {
    const ideas = build("carousel-1");

    expect(ideas.some((idea) => HEX.test(idea))).toBe(false);
    expect(ideas[0]).toContain("in black and indigo tones");
  });

  /** Scenario: Suggestions name colours in words, never hex codes */
  it("falls back to neutral tones without a palette", () => {
    expect(build("carousel-1", 0, null)[0]).toContain("in neutral tones");
  });

  /** Scenario: The theme shows up as a prop, not as the quoted title */
  it("gives each idea a different AI prop and never quotes the topic", () => {
    const ideas = build("carousel-1");
    const props = ideas.map((idea) =>
      aiProps.find((prop) => idea.includes(prop)),
    );

    expect(props.every(Boolean)).toBe(true);
    expect(new Set(props).size).toBe(6);
    expect(ideas.some((idea) => idea.includes("Meta venceu"))).toBe(false);
  });

  /** Scenario: Suggestions are stable per carousel and differ between carousels */
  it("is deterministic per seed and differs between seeds", () => {
    expect(build("carousel-1")).toEqual(build("carousel-1"));
    expect(build("carousel-2")).not.toEqual(build("carousel-1"));
  });

  /** Scenario: Outras ideias shuffles the catalogue without an AI call */
  it("changes the set on a new round", () => {
    expect(build("carousel-1", 1)).not.toEqual(build("carousel-1", 0));
  });

  /** Scenario: Every suggestion fits the prompt field */
  it("keeps every idea within 400 characters", () => {
    for (let round = 0; round < 20; round += 1) {
      expect(build("seed", round).every((idea) => idea.length <= 400)).toBe(
        true,
      );
    }
  });
});

describe("topicTheme", () => {
  /** Scenario: The theme shows up as a prop, not as the quoted title */
  it.each([
    [TOPIC, "ai"],
    ["Inteligência artificial no trabalho", "ai"],
    ["Como investir dinheiro", "money"],
    ["Programação para iniciantes", "code"],
    ["Marketing no Instagram", "social"],
    ["Liderança e carreira", "career"],
    ["Receitas de bolo", "general"],
  ])("maps %s to %s", (topic, theme) => {
    expect(topicTheme(topic)).toBe(theme);
  });
});

describe("colourName", () => {
  /** Scenario: Suggestions name colours in words, never hex codes */
  it.each([
    ["#0b0b14", "black"],
    ["#2a2a2a", "charcoal"],
    ["#9ca3af", "gray"],
    ["#f9fafb", "white"],
    ["#ef4444", "red"],
    ["#f97316", "orange"],
    ["#facc15", "yellow"],
    ["#22c55e", "green"],
    ["#14b8a6", "teal"],
    ["#3b82f6", "blue"],
    ["#4f46e5", "indigo"],
    ["#a855f7", "purple"],
    ["#ec4899", "pink"],
    ["#e11d48", "red"],
    ["not-a-colour", "gray"],
  ])("names %s as %s", (hex, name) => {
    expect(colourName(hex)).toBe(name);
  });
});
