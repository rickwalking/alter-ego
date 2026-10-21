/**
 * AE-0446: landing "Latest Posts" card copy stays in one language.
 * Gherkin: tests/features/landing-card-language-ae0446.feature
 */
import { describe, expect, it } from "vitest";
import {
  cardLocale,
  localizedSubtitle,
  localizedTitle,
} from "@/app/(public)/(marketing)/marketing-helpers";
import type { CarouselListItem } from "@/app/(public)/(marketing)/types";

function post(overrides: Partial<CarouselListItem>): CarouselListItem {
  return {
    title: "Título",
    title_en: "Title",
    subtitle: "Subtítulo",
    subtitle_en: "Subtitle",
    topic: "Tema de origem",
    ...overrides,
  } as CarouselListItem;
}

describe("landing card copy (AE-0446)", () => {
  // Scenario: An English title without an English subtitle shows no Portuguese subtitle
  it("shows an English title with no subtitle rather than a Portuguese one", () => {
    const item = post({ subtitle_en: null });
    expect(localizedTitle(item, "en")).toBe("Title");
    expect(localizedSubtitle(item, "en")).toBe("");
  });

  // Scenario: A Portuguese visitor sees the Portuguese copy
  it("keeps the topic fallback for a Portuguese card without a subtitle", () => {
    const item = post({ subtitle: null });
    expect(localizedTitle(item, "pt")).toBe("Título");
    expect(localizedSubtitle(item, "pt")).toBe("Tema de origem");
  });

  // Scenario: A card without a Portuguese title falls back to English as a whole
  it("renders the English copy as a whole when the Portuguese title is missing", () => {
    const item = post({ title: null });
    expect(localizedTitle(item, "pt")).toBe("Title");
    expect(localizedSubtitle(item, "pt")).toBe("Subtitle");
  });

  it("falls back to the topic when no title exists in any language", () => {
    const item = post({ title: null, title_en: null, topic: "Só o tema" });
    expect(localizedTitle(item, "en")).toBe("Só o tema");
  });

  it("maps an unsupported locale to the default locale", () => {
    expect(cardLocale("fr")).toBe("en");
    expect(cardLocale("en")).toBe("en");
  });
});
