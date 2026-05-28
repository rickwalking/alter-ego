/** Blog AI suggestion action types. */
export const BLOG_AI_ACTIONS = {
  IMPROVE: "improve",
  SHORTEN: "shorten",
  EXPAND: "expand",
  ADD_OPINION: "add_opinion",
} as const;

export type BlogAiAction =
  (typeof BLOG_AI_ACTIONS)[keyof typeof BLOG_AI_ACTIONS];

/** Voice match threshold aligned with backend. */
export const VOICE_MATCH_MIN_SCORE = 70;

/** Editorial workflow review actions. */
export const EDITORIAL_REVIEW_ACTIONS = {
  APPROVE: "approve",
  REVISE: "revise",
  REJECT: "reject",
  EDIT: "edit",
} as const;

/** Content source types aligned with backend ContentSourceCreate. */
export const CONTENT_SOURCE_TYPES = {
  URL: "url",
  DOCUMENT: "document",
  NOTE: "note",
  INTERVIEW: "interview",
  DATA: "data",
} as const;

export type ContentSourceType =
  (typeof CONTENT_SOURCE_TYPES)[keyof typeof CONTENT_SOURCE_TYPES];
