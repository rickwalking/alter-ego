import { describe, expect, it } from "vitest";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";

type TranslationNode = string | { [key: string]: TranslationNode };

function leafKeys(node: TranslationNode, prefix = ""): string[] {
  if (typeof node === "string") return [prefix];
  return Object.entries(node).flatMap(([key, value]) =>
    leafKeys(value, prefix ? `${prefix}.${key}` : key),
  );
}

function leafValue(node: TranslationNode, path: string): string | undefined {
  return path
    .split(".")
    .reduce<
      TranslationNode | undefined
    >((current, key) => (current && typeof current === "object" ? current[key] : undefined), node) as
    | string
    | undefined;
}

const HOME_EN = en.home as TranslationNode;
const HOME_PT = pt.home as TranslationNode;
const COMMON_NAV_EN = en.common.nav as TranslationNode;
const COMMON_NAV_PT = pt.common.nav as TranslationNode;

// Scenario: Landing copy is complete and in sync in both locales
describe("landing copy", () => {
  it("has the same landing keys in pt and en", () => {
    expect(leafKeys(HOME_PT).sort((a, b) => a.localeCompare(b))).toEqual(
      leafKeys(HOME_EN).sort((a, b) => a.localeCompare(b)),
    );
    expect(leafKeys(COMMON_NAV_PT).sort((a, b) => a.localeCompare(b))).toEqual(
      leafKeys(COMMON_NAV_EN).sort((a, b) => a.localeCompare(b)),
    );
  });

  it("removes the hero version badge and the infinite-topics stat", () => {
    for (const home of [HOME_EN, HOME_PT]) {
      expect(leafKeys(home)).not.toContain("hero.badgeVersion");
      expect(leafKeys(home)).not.toContain("stats.topics");
    }
  });

  it("keeps the carousels nav label in both locales", () => {
    expect(leafValue(COMMON_NAV_PT, "carousels")).toBe("Carrosséis");
    expect(leafValue(COMMON_NAV_EN, "carousels")).toBe("Carousels");
  });

  // Scenario: Landing copy makes no overclaim or grammar error
  it("does not claim the assistant knows everything", () => {
    expect(leafValue(HOME_PT, "hero.subtitle")).not.toMatch(/sabe tudo/i);
    expect(leafValue(HOME_EN, "hero.subtitle")).not.toMatch(
      /knows everything/i,
    );
  });

  it("fixes the Portuguese about grammar and standardizes Alter-Ego", () => {
    expect(leafValue(HOME_PT, "about.paragraph2")).not.toContain(
      "Especializo me",
    );
    expect(leafValue(HOME_PT, "about.paragraph4")).toContain("Alter-Ego");
    expect(leafValue(HOME_EN, "about.paragraph4")).toContain("Alter-Ego");
  });

  it("describes the latest-posts feed as carousels, not blog posts", () => {
    expect(leafValue(HOME_PT, "posts.subtitle")).toMatch(/Carrosséis/i);
    expect(leafValue(HOME_PT, "posts.subtitle")).not.toMatch(/posts de blog/i);
    expect(leafValue(HOME_EN, "posts.subtitle")).toMatch(/carousels/i);
    expect(leafValue(HOME_EN, "posts.subtitle")).not.toMatch(/blog posts/i);
  });
});
