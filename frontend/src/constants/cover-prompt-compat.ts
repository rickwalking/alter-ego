/**
 * Compatibility tags of the curated cover-idea pools. Each option lists the
 * tags it provides and the tags it needs from the rest of the scene; a scene
 * is only suggested when every need is provided. Indices match the
 * `create.coverIdeas.pools.<dimension>.<n>` and `props.<theme>.<n>` keys.
 */
import type { CoverIdeaTheme } from "./cover-prompt-ideas";

/** A physical feature one option brings to, or asks of, the scene. */
export const COVER_IDEA_TAGS = {
  INDOOR: "indoor",
  OUTDOOR: "outdoor",
  SURFACE: "surface",
  RAILING: "railing",
  STAIRS: "stairs",
  COLLAR: "collar",
  FULL_BODY: "fullBody",
} as const;

export type CoverIdeaTag =
  (typeof COVER_IDEA_TAGS)[keyof typeof COVER_IDEA_TAGS];

/** What one pool option provides to the scene and needs from it. */
export interface CoverIdeaOptionRule {
  provides?: readonly CoverIdeaTag[];
  needs?: readonly CoverIdeaTag[];
}

/** Rules of the options of one pool, by index; a missing index has none. */
export type CoverIdeaPoolRules = Readonly<Record<number, CoverIdeaOptionRule>>;

const { INDOOR, OUTDOOR, SURFACE, RAILING, STAIRS, COLLAR, FULL_BODY } =
  COVER_IDEA_TAGS;

/** Locations: indoor or outdoor, and which surfaces, railings or stairs they have. */
const LOCATION_RULES: CoverIdeaPoolRules = {
  0: { provides: [OUTDOOR] },
  1: { provides: [INDOOR, SURFACE] },
  2: { provides: [OUTDOOR, RAILING] },
  3: { provides: [INDOOR, SURFACE] },
  4: { provides: [INDOOR, STAIRS, RAILING] },
  5: { provides: [OUTDOOR, SURFACE] },
  6: { provides: [INDOOR, STAIRS, SURFACE] },
  7: { provides: [OUTDOOR, RAILING] },
};

/** Shots: every framing except the close-up and the half-body shows the whole pose. */
const SHOT_RULES: CoverIdeaPoolRules = {
  1: { provides: [FULL_BODY] },
  2: { provides: [FULL_BODY] },
  4: { provides: [FULL_BODY] },
  5: { provides: [FULL_BODY] },
  6: { provides: [FULL_BODY] },
  7: { provides: [FULL_BODY] },
};

/** Wardrobe: the outfits with a jacket collar to adjust. */
const WARDROBE_RULES: CoverIdeaPoolRules = {
  0: { provides: [COLLAR] },
  1: { provides: [COLLAR] },
  6: { provides: [COLLAR] },
};

/** Poses that need a railing, stairs, a jacket collar or the whole body in frame. */
const POSE_RULES: CoverIdeaPoolRules = {
  0: { needs: [FULL_BODY] },
  1: { needs: [RAILING] },
  4: { needs: [STAIRS, FULL_BODY] },
  5: { needs: [COLLAR] },
};

/** Lights that only exist outdoors (sun, sky) or indoors (window, lamps). */
const LIGHT_RULES: CoverIdeaPoolRules = {
  1: { needs: [OUTDOOR] },
  2: { needs: [OUTDOOR] },
  3: { needs: [OUTDOOR] },
  4: { needs: [INDOOR] },
  7: { needs: [INDOOR] },
};

/**
 * The pools in pick order: every need refers to a tag of an earlier pool, so
 * an incompatible option is rejected as soon as it is considered.
 */
export const COVER_IDEA_DIMENSION_RULES = {
  location: LOCATION_RULES,
  shot: SHOT_RULES,
  wardrobe: WARDROBE_RULES,
  pose: POSE_RULES,
  light: LIGHT_RULES,
} as const;

/** Theme props that sit on a desk or table, or hang on an indoor wall. */
export const COVER_IDEA_PROP_RULES: Readonly<
  Record<CoverIdeaTheme, CoverIdeaPoolRules>
> = {
  ai: {
    1: { needs: [INDOOR] },
    2: { needs: [SURFACE] },
    3: { needs: [SURFACE] },
    4: { needs: [INDOOR] },
    5: { needs: [SURFACE] },
  },
  code: {
    0: { needs: [SURFACE] },
    1: { needs: [SURFACE] },
    2: { needs: [SURFACE] },
    5: { needs: [INDOOR] },
  },
  money: {
    1: { needs: [SURFACE] },
    2: { needs: [SURFACE] },
    5: { needs: [SURFACE] },
  },
  social: {
    1: { needs: [INDOOR] },
    4: { needs: [INDOOR] },
  },
  career: {
    3: { needs: [INDOOR] },
    4: { needs: [INDOOR] },
  },
  general: {},
};
