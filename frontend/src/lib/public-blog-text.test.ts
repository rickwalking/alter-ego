import { describe, expect, it } from "vitest";
import {
  emphasisHtmlToMarkdown,
  formatPublicDate,
  isPlaceholderTitle,
  resolveDisplayTitle,
  stripEmphasisMarkup,
  toCategoryLabel,
} from "@/lib/public-blog-text";

// Feature: Public blog renders correctly for anonymous visitors (AE-0412)
// tests/features/public-blog-polish-ae0412.feature

describe("stripEmphasisMarkup", () => {
  // Scenario: Emphasis markup in a title is not shown raw
  it("removes emphasis HTML and markdown and collapses whitespace", () => {
    expect(
      stripEmphasisMarkup(
        "Why does everyone use <strong>ChatGPT</strong> and not Claude?",
      ),
    ).toBe("Why does everyone use ChatGPT and not Claude?");
    expect(stripEmphasisMarkup("A **bold** and *em* `code`  title ")).toBe(
      "A bold and em code title",
    );
    expect(stripEmphasisMarkup("<B>x</B> <em>y</em> <i>z</i>")).toBe("x y z");
  });

  it("keeps non-emphasis text such as @handles with underscores", () => {
    expect(stripEmphasisMarkup("@my_handle says hi")).toBe(
      "@my_handle says hi",
    );
  });
});

describe("emphasisHtmlToMarkdown", () => {
  // Scenario: Emphasis markup in the body is rendered as emphasis
  it("converts strong/b to ** and em/i to *", () => {
    expect(
      emphasisHtmlToMarkdown(
        "# Use <strong>ChatGPT</strong>\n\n<b>x</b> and <em>y</em> <i>z</i>",
      ),
    ).toBe("# Use **ChatGPT**\n\n**x** and *y* *z*");
  });

  it("drops unmatched emphasis tags", () => {
    expect(emphasisHtmlToMarkdown("broken <strong>tag")).toBe("broken tag");
  });
});

describe("isPlaceholderTitle / resolveDisplayTitle", () => {
  // Scenario: A placeholder title falls back to a real title
  it.each(["slide", "Slide", "slide_3", "Slide 2", "  ", "intro", "**CTA**"])(
    "treats %j as a placeholder",
    (title) => {
      expect(isPlaceholderTitle(title)).toBe(true);
    },
  );

  it("does not treat a real title as a placeholder", () => {
    expect(isPlaceholderTitle("Slides that convert")).toBe(false);
  });

  it("returns the first real title without markup", () => {
    expect(
      resolveDisplayTitle([
        "slide",
        null,
        undefined,
        "Gemini 4 Argon <strong>chegou</strong>.",
      ]),
    ).toBe("Gemini 4 Argon chegou.");
  });

  // Scenario: Every title candidate is a placeholder
  it("returns an empty string when every candidate is a placeholder", () => {
    expect(resolveDisplayTitle(["slide", "", null])).toBe("");
  });
});

describe("toCategoryLabel", () => {
  // Scenario: A long niche is not used as a category chip
  it("keeps a short niche", () => {
    expect(toCategoryLabel("AI models")).toBe("AI models");
  });

  it.each([
    "Goodhart's Law gaming, context anxiety, anti-gaming gates and more",
    "one two three four five",
    "",
    null,
    undefined,
  ])("drops %j", (niche) => {
    expect(toCategoryLabel(niche)).toBeUndefined();
  });

  it("accepts exactly the word and character limits", () => {
    expect(toCategoryLabel("one two three four")).toBe("one two three four");
    expect(toCategoryLabel("x".repeat(32))).toBe("x".repeat(32));
    expect(toCategoryLabel("x".repeat(33))).toBeUndefined();
  });
});

describe("formatPublicDate", () => {
  // Scenario: Dates follow the visitor's language
  it("formats per locale in UTC", () => {
    expect(formatPublicDate("2026-10-14T23:30:00Z", "pt")).toBe("14/10/2026");
    expect(formatPublicDate("2026-10-14T23:30:00Z", "en")).toBe("Oct 14, 2026");
  });

  // Scenario: Invalid dates are not printed
  it.each(["", "not-a-date", null, undefined])(
    "returns an empty string for %j",
    (value) => {
      expect(formatPublicDate(value, "pt")).toBe("");
    },
  );
});
