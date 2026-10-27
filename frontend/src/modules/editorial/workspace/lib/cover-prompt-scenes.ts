import {
  COVER_IDEA_CATALOGUE_SIZE,
  COVER_IDEA_POOL_SIZE,
  COVER_IDEA_PROP_POOL_SIZE,
  type CoverIdeaTheme,
} from "@/constants/cover-prompt-ideas";
import {
  COVER_IDEA_DIMENSION_RULES,
  COVER_IDEA_PROP_RULES,
  type CoverIdeaPoolRules,
  type CoverIdeaTag,
} from "@/constants/cover-prompt-compat";

const SEED_SEPARATOR = ":";
const FNV_OFFSET = 2166136261;
const FNV_PRIME = 16777619;
const SEARCH_BUDGET = 5000;
const LAST_RESORT_BUDGET = 1000000;
const ALTERNATIVE_KEYS = 8;
const MAX_SHARED_WITH_PREVIOUS = 1;

/** A scene dimension: one of the shared pools, or the theme prop. */
export type CoverSceneDimension =
  | keyof typeof COVER_IDEA_DIMENSION_RULES
  | "prop";

/** One curated scene: the option index picked in every dimension. */
export type CoverScene = Readonly<Record<CoverSceneDimension, number>>;

/** The dimensions in pick order; needs only refer to tags of earlier ones. */
export const COVER_SCENE_DIMENSIONS: readonly CoverSceneDimension[] = [
  ...(Object.keys(COVER_IDEA_DIMENSION_RULES) as CoverSceneDimension[]),
  "prop",
];

interface Choice {
  dimension: CoverSceneDimension;
  index: number;
}

/** The previous round to stay away from, and whether its props are banned. */
interface RoundLimits {
  previous: readonly CoverScene[];
  freshPropsOnly: boolean;
  budget: number;
}

interface Search {
  orders: Record<CoverSceneDimension, number[]>;
  rules: Record<CoverSceneDimension, CoverIdeaPoolRules>;
  previous: readonly CoverScene[];
  scenes: Record<CoverSceneDimension, number>[];
  steps: number;
  budget: number;
}

function hashSeed(seed: string): number {
  let hash = FNV_OFFSET;
  for (let i = 0; i < seed.length; i += 1) {
    hash = Math.imul(hash ^ seed.charCodeAt(i), FNV_PRIME);
  }
  return hash >>> 0;
}

/** Every index of ``0..poolSize-1`` in an order fixed by ``key``. */
function shuffled(key: string, poolSize: number): number[] {
  const rank = (index: number): number =>
    hashSeed(`${key}${SEED_SEPARATOR}${index}`);
  return Array.from({ length: poolSize }, (_, i) => i).sort(
    (a, b) => rank(a) - rank(b),
  );
}

/** The tags the scene's already picked options provide. */
function providedTags(
  search: Search,
  scene: Partial<Record<CoverSceneDimension, number>>,
): Set<CoverIdeaTag> {
  const tags = new Set<CoverIdeaTag>();
  for (const [dimension, index] of Object.entries(scene)) {
    const rule = search.rules[dimension as CoverSceneDimension][index];
    for (const tag of rule?.provides ?? []) tags.add(tag);
  }
  return tags;
}

function fits(
  search: Search,
  scene: Partial<Record<CoverSceneDimension, number>>,
  { dimension, index }: Readonly<Choice>,
): boolean {
  if (search.scenes.some((other) => other[dimension] === index)) return false;
  const needs = search.rules[dimension][index]?.needs ?? [];
  const tags = providedTags(search, scene);
  if (!needs.every((tag) => tags.has(tag))) return false;
  const next = { ...scene, [dimension]: index };
  return search.previous.every(
    (old) =>
      Object.entries(next).filter(
        ([key, value]) => old[key as CoverSceneDimension] === value,
      ).length <= MAX_SHARED_WITH_PREVIOUS,
  );
}

/** Depth-first: fill the next scene dimension by dimension, backtracking on a dead end. */
function fill(
  search: Search,
  depth: number,
  scene: Partial<Record<CoverSceneDimension, number>>,
): boolean {
  if (search.scenes.length === COVER_IDEA_CATALOGUE_SIZE) return true;
  const dimension = COVER_SCENE_DIMENSIONS[depth];
  if (dimension === undefined) {
    search.scenes.push(scene as Record<CoverSceneDimension, number>);
    if (fill(search, 0, {})) return true;
    search.scenes.pop();
    return false;
  }
  for (const index of search.orders[dimension]) {
    search.steps += 1;
    if (search.steps > search.budget) return false;
    if (!fits(search, scene, { dimension, index })) continue;
    if (fill(search, depth + 1, { ...scene, [dimension]: index })) {
      return true;
    }
  }
  return false;
}

function searchRound(
  key: string,
  theme: CoverIdeaTheme,
  { previous, freshPropsOnly, budget }: Readonly<RoundLimits>,
): CoverScene[] | null {
  const usedProps = new Set(previous.map((scene) => scene.prop));
  const props = shuffled(
    `${key}${SEED_SEPARATOR}prop`,
    COVER_IDEA_PROP_POOL_SIZE,
  );
  const orders = {} as Record<CoverSceneDimension, number[]>;
  for (const dimension of COVER_SCENE_DIMENSIONS) {
    orders[dimension] = shuffled(
      `${key}${SEED_SEPARATOR}${dimension}`,
      COVER_IDEA_POOL_SIZE,
    );
  }
  orders.prop = [
    ...props.filter((index) => !usedProps.has(index)),
    ...(freshPropsOnly ? [] : props.filter((index) => usedProps.has(index))),
  ];
  const search: Search = {
    orders,
    rules: {
      ...COVER_IDEA_DIMENSION_RULES,
      prop: COVER_IDEA_PROP_RULES[theme],
    },
    previous,
    scenes: [],
    steps: 0,
    budget,
  };
  return fill(search, 0, {}) ? search.scenes : null;
}

/**
 * One round after ``previous``: the seeded key and then alternative keys,
 * first with fresh props only and then with any prop, so the consecutive-round
 * rule holds whenever a few orders can satisfy it. Only when none does is the
 * round picked without it, and as a last resort the previous round is kept.
 */
function nextRound(
  key: string,
  theme: CoverIdeaTheme,
  previous: readonly CoverScene[],
): CoverScene[] {
  for (const freshPropsOnly of [true, false]) {
    for (let attempt = 0; attempt < ALTERNATIVE_KEYS; attempt += 1) {
      const attemptKey =
        attempt === 0 ? key : `${key}${SEED_SEPARATOR}${attempt}`;
      const scenes = searchRound(attemptKey, theme, {
        previous,
        freshPropsOnly,
        budget: SEARCH_BUDGET,
      });
      if (scenes) return scenes;
    }
  }
  return (
    searchRound(key, theme, {
      previous: [],
      freshPropsOnly: false,
      budget: LAST_RESORT_BUDGET,
    }) ?? [...previous]
  );
}

/**
 * Rounds ``0..count-1`` of the catalogue, each derived from the one before.
 */
export function catalogueRounds(
  seed: string,
  theme: CoverIdeaTheme,
  count: number,
): CoverScene[][] {
  const rounds: CoverScene[][] = [];
  let previous: CoverScene[] = [];
  for (let current = 0; current < count; current += 1) {
    const key = [seed, String(current)].join(SEED_SEPARATOR);
    previous = nextRound(key, theme, previous);
    rounds.push(previous);
  }
  return rounds;
}

/**
 * The six scenes of one catalogue round: pairwise distinct on every dimension,
 * only physically compatible combinations (an indoor light needs an indoor
 * location, a collar pose needs a jacket, a close-up hides a full-body pose,
 * a desk prop needs a surface), and, after round 0, sharing at most one value
 * with any scene of the previous round and, where the scenes allow it, using
 * only props it did not use.
 * Deterministic per seed, theme and round.
 */
export function catalogueScenes(
  seed: string,
  theme: CoverIdeaTheme,
  round: number,
): CoverScene[] {
  return catalogueRounds(seed, theme, Math.max(round, 0) + 1).at(-1) ?? [];
}
