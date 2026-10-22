import type { PersonaCreatePayload, PersonaProfile } from "@/modules/persona";
import { fieldErrorsOf } from "@/lib/zod-field-errors";
import {
  DEFAULT_TONE,
  personaFormSchema,
  type ToneKey,
} from "@/schemas/persona";

/** A writing sample while editing; the id only keys the list. */
export interface SampleDraft {
  id: string;
  text: string;
}

/** The phrase lists of a persona, edited as chips. */
export type PhraseListKey =
  | "expertise_areas"
  | "preferred_phrases"
  | "forbidden_phrases";

/** The free-text style fields of a persona. */
export type StyleTextKey =
  | "description"
  | "sentence_structure_preferences"
  | "paragraph_style"
  | "opinion_expression";

export type PersonaFormState = Record<StyleTextKey, string> &
  Record<PhraseListKey, string[]> & {
    name: string;
    tone: Record<ToneKey, number>;
    writing_samples: SampleDraft[];
  };

/** Field path (`name`, `writing_samples.0`, …) → i18n key of its error. */
export type PersonaFormErrors = Record<string, string>;

const GENERIC_FIELD_ERROR = "errors.invalid";

/** The error message key of each validated field (keyed by its path without the list index). */
const FIELD_ERROR_KEYS: Record<string, string> = {
  name: "errors.name",
  writing_samples: "errors.sample",
  tone_attributes: "errors.tone",
};

export function newSample(text = ""): SampleDraft {
  return { id: crypto.randomUUID(), text };
}

/** The form's starting values: a blank persona, or the persona being edited. */
export function initialPersonaFormState(
  persona?: PersonaProfile,
): PersonaFormState {
  if (!persona) {
    return {
      name: "",
      description: "",
      tone: { ...DEFAULT_TONE },
      expertise_areas: [],
      preferred_phrases: [],
      forbidden_phrases: [],
      sentence_structure_preferences: "",
      paragraph_style: "",
      opinion_expression: "",
      writing_samples: [],
    };
  }
  return {
    name: persona.name,
    description: persona.description ?? "",
    tone: { ...DEFAULT_TONE, ...persona.tone_attributes },
    expertise_areas: [...persona.expertise_areas],
    preferred_phrases: [...persona.preferred_phrases],
    forbidden_phrases: [...persona.forbidden_phrases],
    sentence_structure_preferences:
      persona.sentence_structure_preferences ?? "",
    paragraph_style: persona.paragraph_style ?? "",
    opinion_expression: persona.opinion_expression ?? "",
    writing_samples: persona.writing_samples.map((text) => newSample(text)),
  };
}

function toCandidate(state: PersonaFormState): Record<string, unknown> {
  const { tone, writing_samples, ...rest } = state;
  return {
    ...rest,
    tone_attributes: tone,
    writing_samples: writing_samples.map((sample) => sample.text),
  };
}

/** `writing_samples.<i>` → `writing_samples`; `tone_attributes.formal` → `tone_attributes`. */
function errorKeyOf(path: readonly PropertyKey[]): string {
  return String(path[0]);
}

/** Validate with the backend-mirroring schema; errors keyed by field path. */
export function validatePersonaForm(
  state: PersonaFormState,
): PersonaFormErrors {
  const result = personaFormSchema.safeParse(toCandidate(state));
  if (result.success) return {};
  return fieldErrorsOf(
    result.error.issues,
    (path) => FIELD_ERROR_KEYS[errorKeyOf(path)],
    GENERIC_FIELD_ERROR,
  );
}

/** The trimmed create/update payload of a valid form (blank text → null). */
export function toPersonaPayload(
  state: PersonaFormState,
): PersonaCreatePayload {
  return personaFormSchema.parse(toCandidate(state));
}

/** The list with the trimmed phrase added, unless it is blank or already there. */
export function addPhrase(list: readonly string[], raw: string): string[] {
  const phrase = raw.trim();
  return phrase && !list.includes(phrase) ? [...list, phrase] : [...list];
}
