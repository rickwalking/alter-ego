import { BG_CARD, NEON_RED, TEXT, TEXT_DIM } from "@/constants/neon";

export const FAILED_CARD_STYLE = {
  background: BG_CARD,
  border: `1px solid ${NEON_RED}44`,
  borderRadius: "8px",
  padding: "24px",
} as const;

export const FAILED_CARD_HEADER_STYLE = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  marginBottom: "12px",
} as const;

export const FAILED_CARD_DOT_STYLE = {
  width: "10px",
  height: "10px",
  borderRadius: "50%",
  background: NEON_RED,
  flexShrink: 0 as const,
} as const;

export const FAILED_CARD_PHASE_LABEL_KEY: Record<string, string> = {
  research: "sendBack.phases.research",
  outline: "sendBack.phases.outline",
  content: "sendBack.phases.content",
  design: "sendBack.phases.design",
  images: "sendBack.phases.images",
  final_review: "review.finalReview.title",
};

export const FAILED_CARD_COLORS = {
  NEON_RED,
  TEXT,
  TEXT_DIM,
} as const;

/**
 * AE-0403: violation codes with a translated field-error message under
 * ``editorialWorkflow.review.fieldErrors.codes``. Any other code falls back to
 * the backend message.
 */
export const FIELD_ERROR_MESSAGE_CODES: ReadonlySet<string> = new Set([
  "body_too_long",
  "heading_too_long",
  "copy_too_many_lines",
  "dash_punctuation_forbidden",
  "heading_not_sentence_case_en",
  "heading_not_sentence_case_pt",
  "body_not_sentence_case_en",
  "body_not_sentence_case_pt",
  "emphasis_markup_invalid",
  "translation_shape_mismatch",
  "translation_not_english",
  "translation_missing",
  "proper_noun_casing",
  "visible_emoji_forbidden",
  "drafting_scaffold_present",
  "heading_empty",
  "body_empty",
  "heading_repeated_in_body",
  "icon_name_not_allowlisted",
]);

/** AE-0403: codes whose message needs the ``{limit}`` read from the backend. */
export const FIELD_ERROR_LIMIT_CODES: ReadonlySet<string> = new Set([
  "body_too_long",
  "heading_too_long",
  "copy_too_many_lines",
]);

/** AE-0403: the EN emphasis markup shown inside the emphasis field error. */
export const EMPHASIS_TAG_EXAMPLE = "<strong>…</strong>";

/** AE-0403: backend locale codes → the localized-slide payload keys. */
export const VIOLATION_LOCALE_TO_PRESENTATION_KEY: Readonly<
  Record<string, "presentation_pt" | "presentation_en">
> = {
  pt: "presentation_pt",
  en: "presentation_en",
};
