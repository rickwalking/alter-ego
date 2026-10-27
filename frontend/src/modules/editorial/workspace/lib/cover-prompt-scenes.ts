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
}

interface Search {
  orders: Record<CoverSceneDimension, number[]>;
  rules: Record<CoverSceneDimension, CoverIdeaPoolRules>;
  previous: readonly CoverScene[];
  scenes: Record<CoverSceneDimension, number>[];
  steps: number;
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
    if (search.steps > SEARCH_BUDGET) return false;
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
  { previous, freshPropsOnly }: Readonly<RoundLimits>,
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
  };
  return fill(search, 0, {}) ? search.scenes : null;
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
  let previous: CoverScene[] = [];
  for (let current = 0; current <= round; current += 1) {
    const key = [seed, String(current)].join(SEED_SEPARATOR);
    previous =
      searchRound(key, theme, { previous, freshPropsOnly: true }) ??
      searchRound(key, theme, { previous, freshPropsOnly: false }) ??
      searchRound(key, theme, { previous: [], freshPropsOnly: false }) ??
      [];
  }
  return previous;
}
