/**
 * Blog editor content helpers (AE-0411).
 *
 * Stored blog content comes in two shapes:
 *  - hand-authored posts: `{ body: string, ... }`
 *  - carousel posts (dual-write): `{ markdown: string, translations: {...} }`
 *
 * The editor edits one text field. These helpers read that field from either
 * shape and write it back **without dropping any other key**, and build an
 * update payload that only carries the fields the user actually changed —
 * so a title-only save never touches the stored content (B05).
 */

import type { BlogPostUpdatePayload } from "./types";

export const BLOG_CONTENT_BODY_KEY = "body";
export const BLOG_CONTENT_MARKDOWN_KEY = "markdown";

export type BlogContentBodyKey =
  | typeof BLOG_CONTENT_BODY_KEY
  | typeof BLOG_CONTENT_MARKDOWN_KEY;

export interface EditableBody {
  key: BlogContentBodyKey;
  text: string;
}

/** Title limit — mirrors the backend `BlogPostUpdate.title` max_length. */
export const BLOG_TITLE_MAX_LENGTH = 255;
/** Excerpt limit — mirrors the backend `BLOG_EXCERPT_MAX_LENGTH`. */
export const BLOG_EXCERPT_MAX_LENGTH = 500;

export const BLOG_EDITOR_ERR_TITLE_REQUIRED = "titleRequired";
export const BLOG_EDITOR_ERR_TITLE_TOO_LONG = "titleTooLong";
export const BLOG_EDITOR_ERR_EXCERPT_TOO_LONG = "excerptTooLong";

export type BlogEditorFieldError =
  | typeof BLOG_EDITOR_ERR_TITLE_REQUIRED
  | typeof BLOG_EDITOR_ERR_TITLE_TOO_LONG
  | typeof BLOG_EDITOR_ERR_EXCERPT_TOO_LONG;

export interface BlogEditorFields {
  title: string;
  excerpt: string;
  bodyText: string;
}

export interface BlogEditorValidation {
  title: BlogEditorFieldError | null;
  excerpt: BlogEditorFieldError | null;
}

/**
 * Read the editable text from stored content. `body` wins when present; a
 * carousel row's `markdown` is used otherwise; anything else edits a new
 * `body` field.
 */
export function readEditableBody(
  content: Record<string, unknown> | null | undefined,
): EditableBody {
  const body = content?.[BLOG_CONTENT_BODY_KEY];
  if (typeof body === "string") {
    return { key: BLOG_CONTENT_BODY_KEY, text: body };
  }
  const markdown = content?.[BLOG_CONTENT_MARKDOWN_KEY];
  if (typeof markdown === "string") {
    return { key: BLOG_CONTENT_MARKDOWN_KEY, text: markdown };
  }
  return { key: BLOG_CONTENT_BODY_KEY, text: "" };
}

/** Write `text` back under `key`, keeping every other stored key. */
export function writeEditableBody(
  content: Record<string, unknown> | null | undefined,
  body: EditableBody,
): Record<string, unknown> {
  return { ...(content ?? {}), [body.key]: body.text };
}

/**
 * Build the PUT payload from what changed since load. Returns `null` when
 * nothing changed (no request needed).
 */
export function buildBlogPostUpdate(
  original: {
    title: string;
    excerpt: string;
    content: Record<string, unknown>;
  },
  fields: BlogEditorFields,
): BlogPostUpdatePayload | null {
  const payload: BlogPostUpdatePayload = {};
  if (fields.title !== original.title) {
    payload.title = fields.title;
  }
  if (fields.excerpt !== original.excerpt) {
    payload.excerpt = fields.excerpt;
  }
  const loaded = readEditableBody(original.content);
  if (fields.bodyText !== loaded.text) {
    payload.content = writeEditableBody(original.content, {
      key: loaded.key,
      text: fields.bodyText,
    });
  }
  return Object.keys(payload).length > 0 ? payload : null;
}

function validateTitle(title: string): BlogEditorFieldError | null {
  if (title.trim().length === 0) {
    return BLOG_EDITOR_ERR_TITLE_REQUIRED;
  }
  return title.length > BLOG_TITLE_MAX_LENGTH
    ? BLOG_EDITOR_ERR_TITLE_TOO_LONG
    : null;
}

/** Client-side checks that mirror the backend 422 rules. */
export function validateBlogEditorFields(
  fields: BlogEditorFields,
): BlogEditorValidation {
  return {
    title: validateTitle(fields.title),
    excerpt:
      fields.excerpt.length > BLOG_EXCERPT_MAX_LENGTH
        ? BLOG_EDITOR_ERR_EXCERPT_TOO_LONG
        : null,
  };
}

export function hasValidationErrors(validation: BlogEditorValidation): boolean {
  return validation.title !== null || validation.excerpt !== null;
}
