/**
 * Pure edits of the `blog.v2` document in the section editor (AE-0424,
 * ADR-0025).
 *
 * The editor edits ONE content language at a time: PT is the top-level
 * `cover` + `sections`, EN is `translations.en` (same shape). Every helper
 * here returns a new document where only the active language changed, so the
 * other language stays byte-identical when the merged document is saved.
 */

import type {
  BlogDocument,
  BlogImage,
  BlogLanguageDocument,
  BlogSection,
} from "@/schemas/blog-document";
import { BLOG_SCHEMA_V2 } from "@/schemas/blog-document";

export const BLOG_CONTENT_LANGUAGES = ["pt", "en"] as const;
export type BlogContentLanguage = (typeof BLOG_CONTENT_LANGUAGES)[number];
export const BLOG_CONTENT_PT: BlogContentLanguage = "pt";
export const BLOG_CONTENT_EN: BlogContentLanguage = "en";

/** Section ids are `sec_<uuid4>` (mirrors the backend id pattern). */
export const BLOG_SECTION_ID_PREFIX = "sec_";

export type SectionPatch = Partial<
  Pick<BlogSection, "heading" | "body_md" | "image">
>;

/** The image slot an action targets: the cover or one section's image. */
export interface BlogImageSlotRef {
  language: BlogContentLanguage;
  sectionId: string | null;
}

export function newSectionId(): string {
  return `${BLOG_SECTION_ID_PREFIX}${crypto.randomUUID()}`;
}

/** The document of `language`, or `null` when that translation is missing. */
export function activeDocument(
  document: BlogDocument,
  language: BlogContentLanguage,
): BlogLanguageDocument | null {
  if (language === BLOG_CONTENT_PT) {
    return document;
  }
  return document.translations[language] ?? null;
}

function replaceActive(
  document: BlogDocument,
  language: BlogContentLanguage,
  updated: BlogLanguageDocument,
): BlogDocument {
  if (language === BLOG_CONTENT_PT) {
    return { ...document, cover: updated.cover, sections: updated.sections };
  }
  return {
    ...document,
    translations: { ...document.translations, [language]: updated },
  };
}

function editActive(
  document: BlogDocument,
  language: BlogContentLanguage,
  edit: (current: BlogLanguageDocument) => BlogLanguageDocument,
): BlogDocument {
  const current = activeDocument(document, language);
  return current ? replaceActive(document, language, edit(current)) : document;
}

export function updateSection(
  document: BlogDocument,
  language: BlogContentLanguage,
  change: { id: string; patch: SectionPatch },
): BlogDocument {
  return editActive(document, language, (current) => ({
    ...current,
    sections: current.sections.map((section) =>
      section.id === change.id ? { ...section, ...change.patch } : section,
    ),
  }));
}

/** Append an empty section with a fresh stable id. */
export function addSection(
  document: BlogDocument,
  language: BlogContentLanguage,
  id: string = newSectionId(),
): BlogDocument {
  const section: BlogSection = { id, heading: "", body_md: "", image: null };
  return editActive(document, language, (current) => ({
    ...current,
    sections: [...current.sections, section],
  }));
}

export function deleteSection(
  document: BlogDocument,
  language: BlogContentLanguage,
  id: string,
): BlogDocument {
  return editActive(document, language, (current) => ({
    ...current,
    sections: current.sections.filter((section) => section.id !== id),
  }));
}

/** Move a section by `delta` positions; its id and image move with it. */
export function moveSection(
  document: BlogDocument,
  language: BlogContentLanguage,
  change: { id: string; delta: number },
): BlogDocument {
  return editActive(document, language, (current) => {
    const from = current.sections.findIndex((s) => s.id === change.id);
    const to = from + change.delta;
    if (from < 0 || to < 0 || to >= current.sections.length) {
      return current;
    }
    const sections = [...current.sections];
    const [moved] = sections.splice(from, 1);
    sections.splice(to, 0, moved);
    return { ...current, sections };
  });
}

export function setCover(
  document: BlogDocument,
  language: BlogContentLanguage,
  cover: BlogImage | null,
): BlogDocument {
  return editActive(document, language, (current) => ({ ...current, cover }));
}

/** The image currently in `slot` (cover or section), `null` when empty. */
export function slotImage(
  document: BlogDocument,
  slot: BlogImageSlotRef,
): BlogImage | null {
  const current = activeDocument(document, slot.language);
  if (!current) {
    return null;
  }
  if (slot.sectionId === null) {
    return current.cover;
  }
  return current.sections.find((s) => s.id === slot.sectionId)?.image ?? null;
}

/** Copy the server's value of one image slot into the local draft. */
export function withServerImage(
  draft: BlogDocument,
  server: BlogDocument,
  slot: BlogImageSlotRef,
): BlogDocument {
  const image = slotImage(server, slot);
  if (slot.sectionId === null) {
    return setCover(draft, slot.language, image);
  }
  return updateSection(draft, slot.language, {
    id: slot.sectionId,
    patch: { image },
  });
}

/** Copy the server's body of one section (after "rewrite in my voice"). */
export function withServerBody(
  draft: BlogDocument,
  server: BlogDocument,
  slot: { language: BlogContentLanguage; sectionId: string },
): BlogDocument {
  const section = activeDocument(server, slot.language)?.sections.find(
    (s) => s.id === slot.sectionId,
  );
  if (!section) {
    return draft;
  }
  return updateSection(draft, slot.language, {
    id: slot.sectionId,
    patch: { body_md: section.body_md },
  });
}

/** Copy the server's EN translation into the draft (PT untouched). */
export function withServerTranslation(
  draft: BlogDocument,
  server: BlogDocument,
): BlogDocument {
  const english = server.translations[BLOG_CONTENT_EN];
  if (!english) {
    return draft;
  }
  return {
    ...draft,
    translations: { ...draft.translations, [BLOG_CONTENT_EN]: english },
  };
}

/** Blank headings are stored as `null` (a lede/intro section). */
export function normalizeForSave(document: BlogDocument): BlogDocument {
  const normalize = (doc: BlogLanguageDocument): BlogLanguageDocument => ({
    ...doc,
    schema: BLOG_SCHEMA_V2,
    sections: doc.sections.map((s) => ({
      ...s,
      heading: s.heading?.trim() ? s.heading : null,
    })),
  });
  const translations = Object.fromEntries(
    Object.entries(document.translations).map(([lang, doc]) => [
      lang,
      normalize(doc),
    ]),
  );
  return { ...(normalize(document) as BlogDocument), translations };
}

/** Replace the selected text of one section's body with an AI suggestion. */
export function applySuggestion(
  document: BlogDocument,
  change: {
    language: BlogContentLanguage;
    selection: { sectionId: string; text: string } | null;
    text: string;
  },
): BlogDocument {
  const { selection } = change;
  if (!selection?.text) {
    return document;
  }
  const section = activeDocument(document, change.language)?.sections.find(
    (s) => s.id === selection.sectionId,
  );
  if (!section?.body_md.includes(selection.text)) {
    return document;
  }
  const body_md = section.body_md.replace(selection.text, change.text);
  return updateSection(document, change.language, {
    id: section.id,
    patch: { body_md },
  });
}
