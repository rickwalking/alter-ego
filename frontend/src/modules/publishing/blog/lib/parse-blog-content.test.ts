import { describe, expect, it } from "vitest";

import {
  ERR_BLOG_DOCUMENT_NOT_V2,
  ERR_INVALID_BLOG_DOCUMENT,
  InvalidBlogDocumentError,
  parseBlogContent,
  resolveBlogLanguage,
  tryParseBlogContent,
} from "@/modules/publishing/blog/lib/parse-blog-content";

/** Gherkin: frontend/tests/features/blog_sections_ae0423.feature. */

const SECTION = {
  id: "sec_1",
  heading: "O que aconteceu",
  body_md: "Corpo",
  image: { url: "https://cdn.example/a.jpg", alt: "Diagrama do fluxo" },
};

const DOCUMENT = {
  schema: "blog.v2",
  cover: { url: "https://cdn.example/c.jpg", alt: "Capa" },
  sections: [SECTION, { ...SECTION, id: "sec_2", image: null }],
  translations: {
    en: {
      schema: "blog.v2",
      cover: null,
      sections: [{ ...SECTION, id: "sec_3", heading: "What happened" }],
    },
  },
};

function codeOf(content: unknown): string | undefined {
  try {
    parseBlogContent(content);
    return undefined;
  } catch (error) {
    return error instanceof InvalidBlogDocumentError ? error.code : "other";
  }
}

describe("parseBlogContent", () => {
  it("parses a v2 document to cover + ordered sections", () => {
    const document = parseBlogContent(DOCUMENT);
    expect(document.cover?.alt).toBe("Capa");
    expect(document.sections.map((s) => s.id)).toEqual(["sec_1", "sec_2"]);
    expect(document.sections[0]!.image?.alt).toBe("Diagrama do fluxo");
    expect(document.sections[1]!.image).toBeNull();
  });

  // Scenario: A non-v2 content blob is rejected by the parse helper
  it.each([
    [{ markdown: "# Title\n\n## A\n\nBody" }],
    ["# flat markdown"],
    [[]],
    [null],
    [{ schema: "blog.v1", sections: [] }],
  ])("rejects non-v2 content %#", (content) => {
    expect(codeOf(content)).toBe(ERR_BLOG_DOCUMENT_NOT_V2);
  });

  it("rejects a v2 document with an empty image alt", () => {
    const broken = {
      ...DOCUMENT,
      sections: [{ ...SECTION, image: { url: "https://x/y.jpg", alt: " " } }],
    };
    expect(codeOf(broken)).toBe(ERR_INVALID_BLOG_DOCUMENT);
  });

  it("defaults missing translations to an empty map", () => {
    const withoutTranslations = Object.fromEntries(
      Object.entries(DOCUMENT).filter(([key]) => key !== "translations"),
    );
    expect(parseBlogContent(withoutTranslations).translations).toEqual({});
  });

  it("tryParseBlogContent returns null instead of throwing", () => {
    expect(tryParseBlogContent({ markdown: "x" })).toBeNull();
    expect(tryParseBlogContent(DOCUMENT)?.sections).toHaveLength(2);
  });
});

describe("resolveBlogLanguage", () => {
  // Scenario: An English translation renders under the en locale
  it("returns the translation when present", () => {
    const en = resolveBlogLanguage(parseBlogContent(DOCUMENT), "en");
    expect(en.sections[0]!.heading).toBe("What happened");
    expect(en.cover).toBeNull();
  });

  it("falls back to PT when the translation is absent", () => {
    const document = parseBlogContent(DOCUMENT);
    expect(resolveBlogLanguage(document, "es")).toBe(document);
    expect(resolveBlogLanguage(document, "pt")).toBe(document);
  });

  // Scenario: A blank translation falls back to PT
  it("falls back to PT when the translation has no non-empty section", () => {
    const document = parseBlogContent({
      ...DOCUMENT,
      translations: {
        en: {
          schema: "blog.v2",
          cover: null,
          sections: [
            { id: "sec_9", heading: null, body_md: "  ", image: null },
          ],
        },
      },
    });
    expect(resolveBlogLanguage(document, "en")).toBe(document);
  });
});
