/**
 * The curated cover scenes: physically coherent combinations, fresh rounds
 * on "Outras ideias", pairwise distinct and deterministic per seed and round.
 */
import { describe, expect, it } from "vitest";
import en from "@/i18n/locales/en.json";
import {
  COVER_IDEA_PROP_POOL_SIZE,
  type CoverIdeaTheme,
} from "@/constants/cover-prompt-ideas";
import {
  COVER_IDEA_DIMENSION_RULES,
  COVER_IDEA_PROP_RULES,
  type CoverIdeaTag,
} from "@/constants/cover-prompt-compat";
import {
  buildCatalogueIdeas,
  type CoverIdeasTranslator,
} from "./cover-prompt-catalogue";
import {
  COVER_SCENE_DIMENSIONS,
  catalogueScenes,
  type CoverScene,
} from "./cover-prompt-scenes";

const THEMES: CoverIdeaTheme[] = [
  "ai",
  "code",
  "money",
  "social",
  "career",
  "general",
];
const SEEDS = Array.from({ length: 40 }, (_, i) => `carousel-${i}`);
const ROUNDS = 6;
const HEX = /#[0-9a-f]{3,6}\b/i;

function rulesOf(theme: CoverIdeaTheme) {
  return { ...COVER_IDEA_DIMENSION_RULES, prop: COVER_IDEA_PROP_RULES[theme] };
}

function unmetNeeds(scene: CoverScene, theme: CoverIdeaTheme): CoverIdeaTag[] {
  const rules = rulesOf(theme);
  const provided = new Set<CoverIdeaTag>();
  for (const dimension of COVER_SCENE_DIMENSIONS) {
    for (const tag of rules[dimension][scene[dimension]]?.provides ?? []) {
      provided.add(tag);
    }
  }
  return COVER_SCENE_DIMENSIONS.flatMap((dimension) =>
    (rules[dimension][scene[dimension]]?.needs ?? []).filter(
      (tag) => !provided.has(tag),
    ),
  );
}

function shared(a: CoverScene, b: CoverScene): number {
  return COVER_SCENE_DIMENSIONS.filter(
    (dimension) => a[dimension] === b[dimension],
  ).length;
}

function everyRound(
  check: (theme: CoverIdeaTheme, rounds: CoverScene[][]) => void,
): void {
  for (const theme of THEMES) {
    for (const seed of SEEDS) {
      check(
        theme,
        Array.from({ length: ROUNDS }, (_, round) =>
          catalogueScenes(seed, theme, round),
        ),
      );
    }
  }
}

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

describe("catalogueScenes", () => {
  /** Scenario: Every suggestion is a physically coherent scene */
  it("only combines compatible options", () => {
    everyRound((theme, rounds) => {
      for (const scene of rounds.flat()) {
        expect(unmetNeeds(scene, theme)).toEqual([]);
      }
    });
  });

  /** Scenario: Every suggestion is a physically coherent scene */
  it("rejects the incoherent scenes seen in production", () => {
    const metroMiddaySun = {
      location: 4,
      shot: 5,
      wardrobe: 1,
      pose: 6,
      light: 3,
      prop: 0,
    };
    const linenCollar = { ...metroMiddaySun, light: 0, wardrobe: 2, pose: 5 };
    const closeUpStairs = { ...metroMiddaySun, light: 0, shot: 3, pose: 4 };
    const robotOnStreet = { ...metroMiddaySun, location: 0, light: 0, prop: 2 };

    expect(unmetNeeds(metroMiddaySun, "ai")).toEqual(["outdoor"]);
    expect(unmetNeeds(linenCollar, "ai")).toEqual(["collar"]);
    expect(unmetNeeds(closeUpStairs, "ai")).toEqual(["fullBody"]);
    expect(unmetNeeds(robotOnStreet, "ai")).toEqual(["surface"]);
  });

  /** Scenario: Outras ideias brings genuinely new scenes */
  it("shares at most one value with any scene of the previous round", () => {
    everyRound((_, rounds) => {
      for (let round = 1; round < rounds.length; round += 1) {
        for (const scene of rounds[round] ?? []) {
          for (const old of rounds[round - 1] ?? []) {
            expect(shared(scene, old)).toBeLessThanOrEqual(1);
          }
        }
      }
    });
  });

  /** Scenario: Outras ideias brings genuinely new scenes */
  it("brings mostly new props from a pool of at least twelve", () => {
    expect(COVER_IDEA_PROP_POOL_SIZE).toBeGreaterThanOrEqual(12);
    for (const theme of THEMES) {
      expect(Object.keys(en.create.coverIdeas.props[theme])).toHaveLength(
        COVER_IDEA_PROP_POOL_SIZE,
      );
    }
    everyRound((_, rounds) => {
      for (let round = 1; round < rounds.length; round += 1) {
        const before = new Set(rounds[round - 1]?.map((scene) => scene.prop));
        const fresh = (rounds[round] ?? []).filter(
          (scene) => !before.has(scene.prop),
        );
        expect(fresh.length).toBeGreaterThanOrEqual(4);
      }
    });
  });

  /** Scenario: Each round stays varied and stable */
  it("keeps six pairwise distinct scenes in every round", () => {
    everyRound((_, rounds) => {
      for (const scenes of rounds) {
        expect(scenes).toHaveLength(6);
        for (const dimension of COVER_SCENE_DIMENSIONS) {
          expect(new Set(scenes.map((scene) => scene[dimension])).size).toBe(6);
        }
      }
    });
  });

  /** Scenario: Each round stays varied and stable */
  it("is deterministic per seed and round", () => {
    expect(catalogueScenes("carousel-1", "ai", 3)).toEqual(
      catalogueScenes("carousel-1", "ai", 3),
    );
    expect(catalogueScenes("carousel-1", "ai", 3)).not.toEqual(
      catalogueScenes("carousel-1", "ai", 2),
    );
  });

  /** Scenario: Each round stays varied and stable */
  it("never writes a hex code", () => {
    for (const seed of SEEDS) {
      const ideas = buildCatalogueIdeas(t, {
        topic: "Agentes de IA",
        palette: {
          name: "Mono Indigo",
          mode: "dark",
          background: "#0b0b14",
          primary: "#6366f1",
          accent: "#4f46e5",
        },
        seed,
        round: 1,
      });
      expect(ideas.some((idea) => HEX.test(idea))).toBe(false);
    }
  });
});
