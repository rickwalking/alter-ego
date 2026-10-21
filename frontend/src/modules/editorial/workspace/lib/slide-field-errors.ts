/**
 * Address slide validation violations to the form field that caused
 * them, so both review forms (publish-page slide editor, content-phase review)
 * can highlight the field, list a per-slide summary and clear an error as soon
 * as its field is edited.
 */
import { VIOLATION_LOCALE_TO_PRESENTATION_KEY } from "@/modules/editorial/workspace/constants";
import type { SlideValidationViolation } from "@/modules/editorial/workspace/types-ai";
import { isWarningViolation } from "./presentation-review-utils";
import type { PresentationLocaleKey } from "./presentation-slide-resolution";

/** Blocking violations keyed by ``fieldErrorKey`` (insertion order kept). */
export type SlideFieldErrors = ReadonlyMap<string, SlideValidationViolation[]>;

const KEY_SEPARATOR = ":";
const DOM_ID_UNSAFE = /[[\].]+/g;
const DOM_ID_DASH = "-";
const LIMIT_PATTERN = /max (\d+)/i;
/** Mirrors the backend ``STRUCTURED_ITEM_FIELD_PATTERN`` (``summary_points[0].body``). */
const STRUCTURED_ITEM_FIELD = /^([a-z_]+)\[(\d+)\]\.([a-z_]+)$/;

/** ``summary_points[0].body`` for an item, ``heading``/``body`` otherwise. */
export function structuredItemFieldPath(
  listKey: string,
  itemIndex: number,
  itemField: string,
): string {
  return `${listKey}[${itemIndex}].${itemField}`;
}

export function fieldErrorKey(
  slideIndex: number,
  locale: PresentationLocaleKey,
  fieldPath: string,
): string {
  return [slideIndex, locale, fieldPath].join(KEY_SEPARATOR);
}

/**
 * Fill ``item_list``/``item_index``/``item_field`` from a structured-item
 * ``field`` path when the source (workflow state) did not split it already.
 */
export function addressViolation(
  violation: SlideValidationViolation,
): SlideValidationViolation {
  if (typeof violation.item_index === "number") {
    return violation;
  }
  const match = STRUCTURED_ITEM_FIELD.exec(violation.field ?? "");
  if (!match) {
    return violation;
  }
  return {
    ...violation,
    item_list: match[1],
    item_index: Number(match[2]),
    item_field: match[3],
  };
}

export function addressViolations(
  violations: readonly SlideValidationViolation[],
): SlideValidationViolation[] {
  return violations.map(addressViolation);
}

function violationFieldPath(violation: SlideValidationViolation): string {
  const { item_list, item_index, item_field } = violation;
  if (item_list && typeof item_index === "number" && item_field) {
    return structuredItemFieldPath(item_list, item_index, item_field);
  }
  return violation.field ?? "";
}

/** The field a violation belongs to, or null when it has no single field. */
export function violationFieldKey(
  violation: SlideValidationViolation,
): string | null {
  const locale = VIOLATION_LOCALE_TO_PRESENTATION_KEY[violation.locale ?? ""];
  const fieldPath = violationFieldPath(violation);
  if (typeof violation.slide_index !== "number" || !locale || !fieldPath) {
    return null;
  }
  return fieldErrorKey(violation.slide_index, locale, fieldPath);
}

function blockers(
  violations: readonly SlideValidationViolation[],
): SlideValidationViolation[] {
  return violations.filter((violation) => !isWarningViolation(violation));
}

export function buildSlideFieldErrors(
  violations: readonly SlideValidationViolation[],
): SlideFieldErrors {
  const errors = new Map<string, SlideValidationViolation[]>();
  for (const violation of blockers(violations)) {
    const key = violationFieldKey(violation);
    if (key !== null) {
      errors.set(key, [...(errors.get(key) ?? []), violation]);
    }
  }
  return errors;
}

/** Blocking violations still open: a field's violations go once it is edited. */
export function openBlockingViolations(
  violations: readonly SlideValidationViolation[],
  clearedKeys: ReadonlySet<string>,
): SlideValidationViolation[] {
  return blockers(violations).filter((violation) => {
    const key = violationFieldKey(violation);
    return key === null || !clearedKeys.has(key);
  });
}

export function violationsForSlide(
  violations: readonly SlideValidationViolation[],
  slideIndex: number,
): SlideValidationViolation[] {
  return violations.filter((violation) => violation.slide_index === slideIndex);
}

/** Sorted, de-duplicated slide numbers that still carry a violation. */
export function invalidSlideIndexes(
  violations: readonly SlideValidationViolation[],
): number[] {
  const indexes = new Set<number>();
  for (const violation of violations) {
    if (typeof violation.slide_index === "number") {
      indexes.add(violation.slide_index);
    }
  }
  return [...indexes].sort((left, right) => left - right);
}

/** The ``max N`` limit the backend message carries, when present. */
export function violationLimit(
  violation: SlideValidationViolation,
): number | null {
  const match = LIMIT_PATTERN.exec(violation.message);
  return match ? Number(match[1]) : null;
}

/** ``{idPrefix}-{slide}-{locale}-{path}`` with the item path made id-safe. */
export function fieldDomId(idPrefix: string, key: string): string {
  const id = `${idPrefix}-${key.split(KEY_SEPARATOR).join("-")}`;
  return withoutTrailingDashes(id.replace(DOM_ID_UNSAFE, DOM_ID_DASH));
}

function withoutTrailingDashes(value: string): string {
  let end = value.length;
  while (end > 0 && value[end - 1] === DOM_ID_DASH) {
    end -= 1;
  }
  return value.slice(0, end);
}

/** The first field of ``slideIndex`` (or of the lowest flagged slide). */
export function firstInvalidFieldKey(
  errors: SlideFieldErrors,
  slideIndex?: number,
): string | null {
  let first: { key: string; slide: number } | null = null;
  for (const [key, violations] of errors) {
    const slide = violations[0]?.slide_index ?? Number.POSITIVE_INFINITY;
    const wanted = slideIndex === undefined || slide === slideIndex;
    if (wanted && (first === null || slide < first.slide)) {
      first = { key, slide };
    }
  }
  return first?.key ?? null;
}

export function slideDomId(idPrefix: string, slideIndex: number): string {
  return `${idPrefix}-slide-${slideIndex}`;
}

/**
 * Focus (and so scroll to) the first invalid field rendered in the form, or
 * the slide card itself when its violations have no editable field.
 */
export function focusInvalidField(
  idPrefix: string,
  errors: SlideFieldErrors,
  slideIndex?: number,
): void {
  const key = firstInvalidFieldKey(errors, slideIndex);
  const field = key ? document.getElementById(fieldDomId(idPrefix, key)) : null;
  if (field) {
    field.focus();
    return;
  }
  if (slideIndex !== undefined) {
    document.getElementById(slideDomId(idPrefix, slideIndex))?.focus();
  }
}
