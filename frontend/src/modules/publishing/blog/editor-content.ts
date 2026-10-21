/**
 * Blog editor draft helpers (validation and the `blog.v2` draft).
 *
 * The editor edits a draft `{ title, excerpt, document }` where `document` is
 * the strict `blog.v2` document (no v1 body/markdown branch). These helpers
 * validate it with the backend's 422 rules and build a PUT payload that only
 * carries what changed — a title-only save never touches the stored content.
 */

import type { BlogDocument } from "@/schemas/blog-document";
import {
  BLOG_HEADING_MARKER,
  BLOG_HEADING_MAX_LENGTH,
  BLOG_SECTION_MAX_LENGTH,
} from "@/constants/blog-editor";
import { normalizeForSave } from "./lib/editor-document";
import type { BlogPostUpdatePayload } from "./types";

/** Title limit — mirrors the backend `BlogPostUpdate.title` max_length. */
export const BLOG_TITLE_MAX_LENGTH = 255;
/** Excerpt limit — mirrors the backend `BLOG_EXCERPT_MAX_LENGTH`. */
export const BLOG_EXCERPT_MAX_LENGTH = 500;

export const BLOG_EDITOR_ERR_TITLE_REQUIRED = "titleRequired";
export const BLOG_EDITOR_ERR_TITLE_TOO_LONG = "titleTooLong";
export const BLOG_EDITOR_ERR_EXCERPT_TOO_LONG = "excerptTooLong";
export const BLOG_EDITOR_ERR_HEADING_INVALID = "headingInvalid";
export const BLOG_EDITOR_ERR_BODY_TOO_LONG = "bodyTooLong";
export const BLOG_EDITOR_ERR_ALT_REQUIRED = "altRequired";
export const BLOG_EDITOR_ERR_NO_SECTIONS = "noSections";

export type BlogEditorFieldError =
  | typeof BLOG_EDITOR_ERR_TITLE_REQUIRED
  | typeof BLOG_EDITOR_ERR_TITLE_TOO_LONG
  | typeof BLOG_EDITOR_ERR_EXCERPT_TOO_LONG;

export type BlogDocumentIssue =
  | typeof BLOG_EDITOR_ERR_HEADING_INVALID
  | typeof BLOG_EDITOR_ERR_BODY_TOO_LONG
  | typeof BLOG_EDITOR_ERR_ALT_REQUIRED
  | typeof BLOG_EDITOR_ERR_NO_SECTIONS;

/** Issue keys of the cover / the whole language in `validation.document`. */
export const BLOG_COVER_ISSUE_KEY = "cover";
export const BLOG_DOCUMENT_ISSUE_KEY = "document";

export interface BlogEditorDraft {
  title: string;
  excerpt: string;
  document: BlogDocument;
}

export interface BlogEditorValidation {
  title: BlogEditorFieldError | null;
  excerpt: BlogEditorFieldError | null;
  /** Issues keyed by `<lang>:<sectionId>`, `<lang>:cover` or `<lang>:document`. */
  document: Record<string, BlogDocumentIssue>;
}

function validateTitle(title: string): BlogEditorFieldError | null {
  if (title.trim().length === 0) {
    return BLOG_EDITOR_ERR_TITLE_REQUIRED;
  }
  return title.length > BLOG_TITLE_MAX_LENGTH
    ? BLOG_EDITOR_ERR_TITLE_TOO_LONG
    : null;
}

function headingIssue(heading: string | null): BlogDocumentIssue | null {
  const trimmed = (heading ?? "").trim();
  const invalid =
    trimmed.startsWith(BLOG_HEADING_MARKER) ||
    (heading ?? "").length > BLOG_HEADING_MAX_LENGTH;
  return invalid ? BLOG_EDITOR_ERR_HEADING_INVALID : null;
}

function sectionIssue(
  section: BlogDocument["sections"][number],
): BlogDocumentIssue | null {
  if (section.image && !section.image.alt.trim()) {
    return BLOG_EDITOR_ERR_ALT_REQUIRED;
  }
  if (section.body_md.length > BLOG_SECTION_MAX_LENGTH) {
    return BLOG_EDITOR_ERR_BODY_TOO_LONG;
  }
  return headingIssue(section.heading);
}

/** Section/cover issues of every language (mirrors the backend 422 rules). */
export function validateDocument(
  document: BlogDocument,
): Record<string, BlogDocumentIssue> {
  const issues: Record<string, BlogDocumentIssue> = {};
  const languages = { pt: document, ...document.translations };
  for (const [lang, doc] of Object.entries(languages)) {
    if (doc.cover && !doc.cover.alt.trim()) {
      issues[`${lang}:${BLOG_COVER_ISSUE_KEY}`] = BLOG_EDITOR_ERR_ALT_REQUIRED;
    }
    if (doc.sections.length === 0) {
      issues[`${lang}:${BLOG_DOCUMENT_ISSUE_KEY}`] =
        BLOG_EDITOR_ERR_NO_SECTIONS;
    }
    for (const section of doc.sections) {
      const issue = sectionIssue(section);
      if (issue) {
        issues[`${lang}:${section.id}`] = issue;
      }
    }
  }
  return issues;
}

/** Client-side checks that mirror the backend 422 rules. */
export function validateBlogEditorDraft(
  draft: BlogEditorDraft,
): BlogEditorValidation {
  return {
    title: validateTitle(draft.title),
    excerpt:
      draft.excerpt.length > BLOG_EXCERPT_MAX_LENGTH
        ? BLOG_EDITOR_ERR_EXCERPT_TOO_LONG
        : null,
    document: validateDocument(draft.document),
  };
}

export function hasValidationErrors(validation: BlogEditorValidation): boolean {
  return (
    validation.title !== null ||
    validation.excerpt !== null ||
    Object.keys(validation.document).length > 0
  );
}

function sameDocument(a: BlogDocument, b: BlogDocument): boolean {
  return (
    JSON.stringify(normalizeForSave(a)) === JSON.stringify(normalizeForSave(b))
  );
}

/** The PUT payload of what changed since load, or `null` when nothing did. */
export function buildBlogPostUpdate(
  original: BlogEditorDraft,
  draft: BlogEditorDraft,
): BlogPostUpdatePayload | null {
  const payload: BlogPostUpdatePayload = {};
  if (draft.title !== original.title) {
    payload.title = draft.title;
  }
  if (draft.excerpt !== original.excerpt) {
    payload.excerpt = draft.excerpt;
  }
  if (!sameDocument(original.document, draft.document)) {
    payload.content = normalizeForSave(draft.document);
  }
  return Object.keys(payload).length > 0 ? payload : null;
}
