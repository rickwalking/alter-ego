import { describe, expect, it } from "vitest";
import {
  BLOG_EDITOR_ERR_EXCERPT_TOO_LONG,
  BLOG_EDITOR_ERR_TITLE_REQUIRED,
  BLOG_EDITOR_ERR_TITLE_TOO_LONG,
  BLOG_EXCERPT_MAX_LENGTH,
  BLOG_TITLE_MAX_LENGTH,
  buildBlogPostUpdate,
  hasValidationErrors,
  readEditableBody,
  validateBlogEditorFields,
  writeEditableBody,
} from "./editor-content";

// Scenarios: see tests/features/blog-dashboard-ae0411.feature

const CAROUSEL_CONTENT = {
  markdown: "# Body\n\nLine two",
  translations: { en: "# EN body" },
};

describe("readEditableBody", () => {
  it("reads content.body for hand-authored posts", () => {
    expect(readEditableBody({ body: "Hello", blocks: [] })).toEqual({
      key: "body",
      text: "Hello",
    });
  });

  // Scenario: A carousel post body is read from content.markdown
  it("reads content.markdown for carousel posts", () => {
    expect(readEditableBody(CAROUSEL_CONTENT)).toEqual({
      key: "markdown",
      text: "# Body\n\nLine two",
    });
  });

  it("prefers body when both keys exist", () => {
    expect(readEditableBody({ body: "b", markdown: "m" }).key).toBe("body");
  });

  it("falls back to an empty body for other shapes", () => {
    expect(readEditableBody({ blocks: [] })).toEqual({ key: "body", text: "" });
    expect(readEditableBody(null)).toEqual({ key: "body", text: "" });
    expect(readEditableBody({ body: 3 })).toEqual({ key: "body", text: "" });
  });
});

describe("writeEditableBody", () => {
  it("replaces only the edited key", () => {
    expect(
      writeEditableBody(CAROUSEL_CONTENT, { key: "markdown", text: "new" }),
    ).toEqual({ markdown: "new", translations: { en: "# EN body" } });
  });

  it("creates the key on empty content", () => {
    expect(writeEditableBody(undefined, { key: "body", text: "x" })).toEqual({
      body: "x",
    });
  });
});

describe("buildBlogPostUpdate", () => {
  const original = {
    title: "Title",
    excerpt: "",
    content: CAROUSEL_CONTENT,
  };
  const unchanged = {
    title: "Title",
    excerpt: "",
    bodyText: CAROUSEL_CONTENT.markdown,
  };

  it("returns null when nothing changed", () => {
    expect(buildBlogPostUpdate(original, unchanged)).toBeNull();
  });

  // Scenario: A title-only save does not send content
  it("sends only the title on a title-only change", () => {
    expect(
      buildBlogPostUpdate(original, { ...unchanged, title: "New" }),
    ).toEqual({ title: "New" });
  });

  it("sends only the excerpt on an excerpt-only change", () => {
    expect(
      buildBlogPostUpdate(original, { ...unchanged, excerpt: "Short" }),
    ).toEqual({ excerpt: "Short" });
  });

  // Scenario: A body edit keeps every other content key
  it("sends the full content with the edited body and the other keys", () => {
    expect(
      buildBlogPostUpdate(original, { ...unchanged, bodyText: "Edited" }),
    ).toEqual({
      content: { markdown: "Edited", translations: { en: "# EN body" } },
    });
  });
});

describe("validateBlogEditorFields", () => {
  const ok = { title: "T", excerpt: "", bodyText: "" };

  it("accepts a normal post", () => {
    const result = validateBlogEditorFields(ok);
    expect(result).toEqual({ title: null, excerpt: null });
    expect(hasValidationErrors(result)).toBe(false);
  });

  // Scenario: An empty title cannot be saved
  it("requires a non-blank title", () => {
    expect(validateBlogEditorFields({ ...ok, title: "" }).title).toBe(
      BLOG_EDITOR_ERR_TITLE_REQUIRED,
    );
    expect(validateBlogEditorFields({ ...ok, title: "   " }).title).toBe(
      BLOG_EDITOR_ERR_TITLE_REQUIRED,
    );
  });

  it("caps the title at the backend limit", () => {
    const atLimit = "a".repeat(BLOG_TITLE_MAX_LENGTH);
    expect(
      validateBlogEditorFields({ ...ok, title: atLimit }).title,
    ).toBeNull();
    const result = validateBlogEditorFields({ ...ok, title: `${atLimit}a` });
    expect(result.title).toBe(BLOG_EDITOR_ERR_TITLE_TOO_LONG);
    expect(hasValidationErrors(result)).toBe(true);
  });

  it("caps the excerpt at the backend limit", () => {
    const atLimit = "e".repeat(BLOG_EXCERPT_MAX_LENGTH);
    expect(
      validateBlogEditorFields({ ...ok, excerpt: atLimit }).excerpt,
    ).toBeNull();
    const result = validateBlogEditorFields({ ...ok, excerpt: `${atLimit}e` });
    expect(result.excerpt).toBe(BLOG_EDITOR_ERR_EXCERPT_TOO_LONG);
    expect(hasValidationErrors(result)).toBe(true);
  });
});
