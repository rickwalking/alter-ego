import { ApiError } from "@/lib/api-client";
import type {
  CarouselCopyTexts,
  CopyField,
  CopySource,
  CopyTextsState,
} from "@/modules/publishing/distribution/hooks/types";

export const COPY_FIELDS: readonly CopyField[] = [
  "caption",
  "linkedinPt",
  "linkedinEn",
];

/** The API field names of the caption and the LinkedIn posts. */
export const DISTRIBUTION_FIELDS = {
  CAPTION: "caption",
  LINKEDIN_PT: "linkedin_post_pt",
  LINKEDIN_EN: "linkedin_post_en",
} as const satisfies Record<string, keyof CarouselCopyTexts>;

/** The API field name of each editor field. */
export const API_FIELD: Readonly<Record<CopyField, keyof CarouselCopyTexts>> = {
  caption: DISTRIBUTION_FIELDS.CAPTION,
  linkedinPt: DISTRIBUTION_FIELDS.LINKEDIN_PT,
  linkedinEn: DISTRIBUTION_FIELDS.LINKEDIN_EN,
};

const ERROR_KEY_BY_DETAIL: Readonly<Record<string, string>> = {
  version_conflict: "copy.errors.stale",
  caption_published: "copy.errors.captionPublished",
  resume_already_in_progress: "copy.errors.runInProgress",
};

const ERROR_KEY_FALLBACK = "copy.errors.save";

/** The saved texts of a project (a missing text is an empty one). */
export function savedCopyTexts(project: CopySource): CopyTextsState {
  return {
    caption: project.caption ?? "",
    linkedinPt: project.linkedin_post_pt ?? "",
    linkedinEn: project.linkedin_post_en ?? "",
  };
}

/**
 * Move the editor onto newly saved texts: a field the owner had not edited
 * takes the new saved text, an edited one keeps the owner's draft.
 */
export function rebaseDrafts(
  draft: CopyTextsState,
  oldSaved: CopyTextsState,
  newSaved: CopyTextsState,
): CopyTextsState {
  const next = { ...newSaved };
  for (const field of COPY_FIELDS) {
    if (draft[field] !== oldSaved[field]) {
      next[field] = draft[field];
    }
  }
  return next;
}

/** The fields among ``fields`` whose draft differs from the saved text. */
export function dirtyFields(
  draft: CopyTextsState,
  saved: CopyTextsState,
  fields: readonly CopyField[] = COPY_FIELDS,
): CopyField[] {
  return fields.filter((field) => draft[field] !== saved[field]);
}

/** The request body saving ``fields`` from the draft. */
export function toCopyPayload(
  draft: CopyTextsState,
  fields: readonly CopyField[],
): CarouselCopyTexts {
  const payload: CarouselCopyTexts = {};
  for (const field of fields) {
    payload[API_FIELD[field]] = draft[field];
  }
  return payload;
}

/** The texts keyed by API field name (what the version history compares). */
export function apiTexts(texts: CopyTextsState): Record<string, string> {
  return {
    [DISTRIBUTION_FIELDS.CAPTION]: texts.caption,
    [DISTRIBUTION_FIELDS.LINKEDIN_PT]: texts.linkedinPt,
    [DISTRIBUTION_FIELDS.LINKEDIN_EN]: texts.linkedinEn,
  };
}

/** The ``publish`` i18n key explaining why a save was refused. */
export function copySaveErrorKey(error: unknown): string {
  if (error instanceof ApiError && typeof error.detail === "string") {
    return ERROR_KEY_BY_DETAIL[error.detail] ?? ERROR_KEY_FALLBACK;
  }
  return ERROR_KEY_FALLBACK;
}
