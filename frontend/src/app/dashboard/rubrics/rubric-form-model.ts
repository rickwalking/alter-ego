import type {
  QualityRubric,
  QualityRubricCreatePayload,
} from "@/modules/quality";
import { fieldErrorsOf } from "@/lib/zod-field-errors";
import {
  EVALUATION_METHODS,
  RUBRIC_CONTENT_TYPES,
  SCORING_SCALES,
  rubricFormSchema,
  type EvaluationMethod,
  type ScoringScale,
} from "@/schemas/rubric";

/** One criterion while editing; numbers stay text until the form is sent. */
export interface CriterionDraft {
  id: string;
  name: string;
  description: string;
  weight: string;
  evaluation_method: EvaluationMethod;
  min_threshold: string;
  scoring_scale: ScoringScale;
  prompt_template: string;
}

export interface RubricFormState {
  name: string;
  description: string;
  applicable_content_types: string[];
  criteria: CriterionDraft[];
}

/** Field path (`name`, `criteria.0.weight`, …) → i18n key of its error. */
export type RubricFormErrors = Record<string, string>;

const NEW_CRITERION_WEIGHT = "0.5";
const NEW_CRITERION_THRESHOLD = "0.7";

/** The error message key of each validated field (keyed by its path without the criterion index). */
const FIELD_ERROR_KEYS: Record<string, string> = {
  name: "errors.name",
  "criteria.name": "errors.criterionName",
  applicable_content_types: "errors.contentTypes",
  criteria: "errors.criteriaRequired",
  "criteria.weight": "errors.unitInterval",
  "criteria.min_threshold": "errors.unitInterval",
  "criteria.evaluation_method": "errors.choice",
  "criteria.scoring_scale": "errors.choice",
};
const GENERIC_FIELD_ERROR = "errors.invalid";

function asMethod(value: string): EvaluationMethod {
  return EVALUATION_METHODS.find((m) => m === value) ?? EVALUATION_METHODS[0];
}

function asScale(value: string): ScoringScale {
  return SCORING_SCALES.find((s) => s === value) ?? SCORING_SCALES[0];
}

/** A blank criterion with a fresh id and the form's starting weight/threshold. */
export function newCriterion(): CriterionDraft {
  return {
    id: crypto.randomUUID(),
    name: "",
    description: "",
    weight: NEW_CRITERION_WEIGHT,
    evaluation_method: EVALUATION_METHODS[0],
    min_threshold: NEW_CRITERION_THRESHOLD,
    scoring_scale: SCORING_SCALES[0],
    prompt_template: "",
  };
}

/** The form's starting values: a blank carousel rubric, or the rubric being edited. */
export function initialRubricFormState(
  rubric?: QualityRubric,
): RubricFormState {
  if (!rubric) {
    return {
      name: "",
      description: "",
      applicable_content_types: [RUBRIC_CONTENT_TYPES[0]],
      criteria: [],
    };
  }
  return {
    name: rubric.name,
    description: rubric.description ?? "",
    applicable_content_types: [...rubric.applicable_content_types],
    criteria: rubric.criteria.map((c) => ({
      ...c,
      weight: String(c.weight),
      min_threshold: String(c.min_threshold),
      evaluation_method: asMethod(c.evaluation_method),
      scoring_scale: asScale(c.scoring_scale),
    })),
  };
}

/** An empty or non-numeric entry becomes NaN, which the schema rejects. */
function toNumber(raw: string): number {
  return raw.trim() === "" ? Number.NaN : Number(raw);
}

function toCandidate(state: RubricFormState): Record<string, unknown> {
  return {
    ...state,
    criteria: state.criteria.map((c) => ({
      ...c,
      weight: toNumber(c.weight),
      min_threshold: toNumber(c.min_threshold),
    })),
  };
}

/** `criteria.<i>.<field>` → `criteria.<field>`; top-level paths stay as they are. */
function errorKeyOf(path: readonly PropertyKey[]): string {
  const [head, , field] = path;
  return field === undefined
    ? String(head)
    : `${String(head)}.${String(field)}`;
}

/** Validate with the backend-mirroring schema; errors keyed by field path. */
export function validateRubricForm(state: RubricFormState): RubricFormErrors {
  const result = rubricFormSchema.safeParse(toCandidate(state));
  if (result.success) return {};
  return fieldErrorsOf(
    result.error.issues,
    (path) => FIELD_ERROR_KEYS[errorKeyOf(path)],
    GENERIC_FIELD_ERROR,
  );
}

/** The trimmed create/update payload of a valid form. */
export function toRubricPayload(
  state: RubricFormState,
): QualityRubricCreatePayload {
  const payload = rubricFormSchema.parse(toCandidate(state));
  return {
    ...payload,
    description: payload.description.trim() || null,
  };
}

/** The list with item `index` moved by `offset` (out-of-range moves are no-ops). */
export function moveItem<T>(
  items: readonly T[],
  index: number,
  offset: number,
): T[] {
  const target = index + offset;
  const next = [...items];
  if (target < 0 || target >= items.length) return next;
  const [moved] = next.splice(index, 1);
  next.splice(target, 0, moved as T);
  return next;
}

/** The content types a checkbox list offers: the known ones plus any stored extras. */
export function contentTypeOptions(selected: readonly string[]): string[] {
  const known: string[] = [...RUBRIC_CONTENT_TYPES];
  return [...known, ...selected.filter((type) => !known.includes(type))];
}
