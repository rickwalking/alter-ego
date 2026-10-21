import { describe, expect, it } from "vitest";
import { SEC_1, image, v2Document } from "./editor.test-utils";
import {
  BLOG_EDITOR_ERR_ALT_REQUIRED,
  BLOG_EDITOR_ERR_BODY_TOO_LONG,
  BLOG_EDITOR_ERR_EXCERPT_TOO_LONG,
  BLOG_EDITOR_ERR_HEADING_INVALID,
  BLOG_EDITOR_ERR_NO_SECTIONS,
  BLOG_EDITOR_ERR_TITLE_REQUIRED,
  BLOG_EDITOR_ERR_TITLE_TOO_LONG,
  BLOG_EXCERPT_MAX_LENGTH,
  BLOG_TITLE_MAX_LENGTH,
  buildBlogPostUpdate,
  hasValidationErrors,
  validateBlogEditorDraft,
  type BlogEditorDraft,
} from "./editor-content";
import { setCover, updateSection } from "./lib/editor-document";

/** Gherkin: tests/features/blog_editor_ae0424.feature, tests/features/blog-dashboard-ae0411.feature. */

function draft(overrides: Partial<BlogEditorDraft> = {}): BlogEditorDraft {
  return {
    title: "GPT 5.6 saiu",
    excerpt: "",
    document: v2Document(true),
    ...overrides,
  };
}

describe("validateBlogEditorDraft", () => {
  it("accepts a valid draft", () => {
    const validation = validateBlogEditorDraft(draft());
    expect(validation).toEqual({ title: null, excerpt: null, document: {} });
    expect(hasValidationErrors(validation)).toBe(false);
  });

  it("mirrors the title and excerpt 422 rules", () => {
    expect(validateBlogEditorDraft(draft({ title: "  " })).title).toBe(
      BLOG_EDITOR_ERR_TITLE_REQUIRED,
    );
    expect(
      validateBlogEditorDraft(
        draft({ title: "x".repeat(BLOG_TITLE_MAX_LENGTH + 1) }),
      ).title,
    ).toBe(BLOG_EDITOR_ERR_TITLE_TOO_LONG);
    const excerpt = "x".repeat(BLOG_EXCERPT_MAX_LENGTH + 1);
    const validation = validateBlogEditorDraft(draft({ excerpt }));
    expect(validation.excerpt).toBe(BLOG_EDITOR_ERR_EXCERPT_TOO_LONG);
    expect(hasValidationErrors(validation)).toBe(true);
  });

  // Scenario: An empty alt is rejected
  it("requires alt text on section and cover images", () => {
    let document = updateSection(v2Document(), "pt", {
      id: SEC_1,
      patch: { image: image(undefined, " ") },
    });
    document = setCover(document, "pt", image(undefined, ""));
    const issues = validateBlogEditorDraft(draft({ document })).document;
    expect(issues[`pt:${SEC_1}`]).toBe(BLOG_EDITOR_ERR_ALT_REQUIRED);
    expect(issues["pt:cover"]).toBe(BLOG_EDITOR_ERR_ALT_REQUIRED);
  });

  it("flags markdown headings, oversized bodies and an empty document", () => {
    const heading = updateSection(v2Document(), "pt", {
      id: SEC_1,
      patch: { heading: "# Título" },
    });
    expect(
      validateBlogEditorDraft(draft({ document: heading })).document[
        `pt:${SEC_1}`
      ],
    ).toBe(BLOG_EDITOR_ERR_HEADING_INVALID);
    const long = updateSection(v2Document(), "pt", {
      id: SEC_1,
      patch: { body_md: "x".repeat(20_001) },
    });
    expect(
      validateBlogEditorDraft(draft({ document: long })).document[
        `pt:${SEC_1}`
      ],
    ).toBe(BLOG_EDITOR_ERR_BODY_TOO_LONG);
    const empty = { ...v2Document(), sections: [] };
    expect(
      validateBlogEditorDraft(draft({ document: empty })).document[
        "pt:document"
      ],
    ).toBe(BLOG_EDITOR_ERR_NO_SECTIONS);
  });
});

describe("buildBlogPostUpdate", () => {
  it("returns null when nothing changed", () => {
    expect(buildBlogPostUpdate(draft(), draft())).toBeNull();
  });

  it("sends only the title on a title-only edit (content untouched)", () => {
    expect(buildBlogPostUpdate(draft(), draft({ title: "Novo" }))).toEqual({
      title: "Novo",
    });
    expect(buildBlogPostUpdate(draft(), draft({ excerpt: "Resumo" }))).toEqual({
      excerpt: "Resumo",
    });
  });

  // Scenario: Editing the EN document never mutates PT
  it("sends the merged document with PT byte-identical on an EN edit", () => {
    const original = draft();
    const edited = updateSection(original.document, "en", {
      id: original.document.translations.en!.sections[0]!.id,
      patch: { body_md: "Edited EN" },
    });
    const payload = buildBlogPostUpdate(original, draft({ document: edited }));
    const content = payload?.content as typeof edited;
    expect(content.translations.en!.sections[0]!.body_md).toBe("Edited EN");
    expect(JSON.stringify(content.sections)).toBe(
      JSON.stringify(original.document.sections),
    );
  });

  it("treats a blank heading and null as the same (no spurious save)", () => {
    const original = draft();
    const blank = updateSection(original.document, "pt", {
      id: "sec_00000000-0000-4000-8000-000000000003",
      patch: { heading: "" },
    });
    expect(
      buildBlogPostUpdate(original, draft({ document: blank })),
    ).toBeNull();
  });
});
