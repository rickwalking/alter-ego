/**
 * AE-0446: a card shows its title and subtitle in ONE language.
 * Gherkin: tests/features/landing-card-language-ae0446.feature
 */
import { describe, expect, it } from "vitest";
import {
  localizedCarouselCopy,
  type CarouselCopyFields,
} from "@/lib/public-carousels";

const BILINGUAL: CarouselCopyFields = {
  title: "Título em português",
  title_en: "English title",
  subtitle: "Subtítulo em português",
  subtitle_en: "English subtitle",
  topic: "Tema",
};

describe("localizedCarouselCopy (AE-0446)", () => {
  // Scenario: An English visitor sees the English title and English subtitle
  it("gives an English visitor the English title and subtitle", () => {
    expect(localizedCarouselCopy(BILINGUAL, "en")).toEqual({
      language: "en",
      title: "English title",
      subtitle: "English subtitle",
    });
  });

  // Scenario: An English title without an English subtitle shows no Portuguese subtitle
  it("never puts a Portuguese subtitle under an English title", () => {
    const copy = localizedCarouselCopy(
      { ...BILINGUAL, subtitle_en: null },
      "en",
    );
    expect(copy).toEqual({
      language: "en",
      title: "English title",
      subtitle: null,
    });
  });

  // Scenario: A Portuguese visitor sees the Portuguese copy
  it("gives a Portuguese visitor the Portuguese title and subtitle", () => {
    expect(localizedCarouselCopy(BILINGUAL, "pt")).toEqual({
      language: "pt",
      title: "Título em português",
      subtitle: "Subtítulo em português",
    });
  });

  // Scenario: A card without a Portuguese title falls back to English as a whole
  it("falls back to English as a whole when the Portuguese title is missing", () => {
    const copy = localizedCarouselCopy(
      { ...BILINGUAL, title: null, subtitle: "Subtítulo órfão" },
      "pt",
    );
    expect(copy).toEqual({
      language: "en",
      title: "English title",
      subtitle: "English subtitle",
    });
  });

  // Scenario: A card without an English title stays Portuguese for an English visitor
  it("stays Portuguese for an English visitor when there is no English title", () => {
    const copy = localizedCarouselCopy(
      { ...BILINGUAL, title_en: null, subtitle_en: "Orphan subtitle" },
      "en",
    );
    expect(copy).toEqual({
      language: "pt",
      title: "Título em português",
      subtitle: "Subtítulo em português",
    });
  });

  it("uses the topic as the Portuguese title when no title exists", () => {
    const copy = localizedCarouselCopy(
      { title: null, subtitle: null, topic: "Tema" },
      "en",
    );
    expect(copy).toEqual({ language: "pt", title: "Tema", subtitle: null });
  });
});
