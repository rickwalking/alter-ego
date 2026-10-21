import {
  PRESENTATION_STRUCTURED_EXTRA_KEYS,
  PRESENTATION_STRUCTURED_ITEM_LIST_KEYS,
} from "./presentation-review-utils";

/**
 * A locale column shows every structured field the other locale has.
 *
 * Prod carousel 5344b6c6: PT slide 1 had a TL;DR strip and EN had none, so the
 * EN column offered no TL;DR field and the blocking
 * ``translation_shape_mismatch`` could not be fixed by hand. A field the other
 * locale has and this one lacks (or an item list with fewer items) is mirrored
 * with empty texts, keeping the non-text parts (``icon_name``,
 * ``content_kind``), so the reviewer can fill it in.
 */

export type PresentationLocaleKey = "presentation_pt" | "presentation_en";

const ITEM_TEXT_FIELDS = ["title", "body"] as const;
const OBJECT_TEXT_FIELDS = ["title", "body", "quote", "attribution"] as const;
const ITEM_LIST_KEYS: ReadonlySet<string> = new Set(
  PRESENTATION_STRUCTURED_ITEM_LIST_KEYS,
);

const OTHER_LOCALE: Record<PresentationLocaleKey, PresentationLocaleKey> = {
  presentation_pt: "presentation_en",
  presentation_en: "presentation_pt",
};

export function otherLocaleKey(
  locale: PresentationLocaleKey,
): PresentationLocaleKey {
  return OTHER_LOCALE[locale];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isEmpty(value: unknown): boolean {
  return (
    value === undefined ||
    value === null ||
    value === "" ||
    (Array.isArray(value) && value.length === 0)
  );
}

function blankTexts(
  value: Record<string, unknown>,
  fields: readonly string[],
): Record<string, unknown> {
  const blank: Record<string, unknown> = { ...value };
  for (const field of fields) {
    if (typeof blank[field] === "string") {
      blank[field] = "";
    }
  }
  return blank;
}

function blankItem(item: unknown): unknown {
  return isRecord(item) ? blankTexts(item, ITEM_TEXT_FIELDS) : item;
}

function mirroredList(current: unknown, source: unknown[]): unknown {
  const items: unknown[] = Array.isArray(current) ? current : [];
  if (Array.isArray(current) && items.length >= source.length) {
    return current;
  }
  return [...items, ...source.slice(items.length).map(blankItem)];
}

function mirroredValue(
  key: string,
  current: unknown,
  source: unknown,
): unknown {
  if (ITEM_LIST_KEYS.has(key) && Array.isArray(source)) {
    return mirroredList(current, source);
  }
  if (!isEmpty(current)) {
    return current;
  }
  if (typeof source === "string") {
    return key === "content_kind" ? source : "";
  }
  return isRecord(source) ? blankTexts(source, OBJECT_TEXT_FIELDS) : current;
}

/** ``target`` plus every structured field ``source`` has and it lacks. */
export function mirrorLocaleStructure(
  target: Record<string, unknown>,
  source: Record<string, unknown> | undefined,
): Record<string, unknown> {
  if (!source) {
    return target;
  }
  let mirrored = target;
  for (const key of PRESENTATION_STRUCTURED_EXTRA_KEYS) {
    const sourceValue = source[key];
    if (isEmpty(sourceValue)) {
      continue;
    }
    const next = mirroredValue(key, target[key], sourceValue);
    if (next !== target[key]) {
      mirrored = { ...mirrored, [key]: next };
    }
  }
  return mirrored;
}
