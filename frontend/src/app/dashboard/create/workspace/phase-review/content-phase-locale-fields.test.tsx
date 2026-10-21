/**
 * Gherkin: frontend/tests/features/content-review-insight-card-ae0407.feature.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { LocalizedSlideReview } from "@/modules/publishing";
import { ContentLocaleFields } from "./content-phase-locale-fields";

const URL = "https://x.com/taylorhbuilds/status/1";
const CARD_PT = {
  quote: "Entregue pequeno",
  attribution: "Taylor H",
  name: "Taylor H",
  handle: "taylorhbuilds",
  quote_id: "q1",
  url: URL,
};
const CARD_EN = { ...CARD_PT, quote: "Ship small", handle: "@taylorhbuilds" };

function slideWith(
  insightPt: unknown,
  insightEn: unknown,
): LocalizedSlideReview {
  return {
    slide_index: 3,
    slide_type: "content",
    presentation_pt: { heading: "Título", body: "Corpo", insight: insightPt },
    presentation_en: { heading: "Title", body: "Body", insight: insightEn },
  };
}

function renderColumn(
  slide: LocalizedSlideReview,
  localeKey: "presentation_pt" | "presentation_en",
): ReturnType<typeof render> {
  return render(
    <ContentLocaleFields
      slide={slide}
      localeKey={localeKey}
      localeLabel={localeKey === "presentation_pt" ? "PT" : "EN"}
      fieldErrors={new Map()}
    />,
  );
}

describe("ContentLocaleFields — pov_news quote card", () => {
  // Scenario: The quote card renders in both locale columns
  // Scenario: A url in the payload is never shown
  it.each([
    ["presentation_pt", "Entregue pequeno"],
    ["presentation_en", "Ship small"],
  ] as const)("renders the %s card without raw JSON", (localeKey, quote) => {
    const { container } = renderColumn(slideWith(CARD_PT, CARD_EN), localeKey);
    expect(screen.getByText("Quote card")).toBeInTheDocument();
    expect(container.querySelector("blockquote")).toHaveTextContent(quote);
    expect(screen.getByText("Taylor H")).toBeInTheDocument();
    expect(screen.getByText("@taylorhbuilds · X")).toBeInTheDocument();
    expect(screen.queryByText(/Structured field/)).toBeNull();
    expect(container.querySelector("pre")).toBeNull();
    expect(container).not.toHaveTextContent(URL);
  });

  // Scenario: A handle that already starts with @ is not doubled
  it("does not double an @ handle", () => {
    const { container } = renderColumn(
      slideWith(CARD_PT, CARD_EN),
      "presentation_en",
    );
    expect(container).not.toHaveTextContent("@@");
  });

  // Scenario: The quote card is an accessible figure
  it("exposes the card as a named figure", () => {
    renderColumn(slideWith(CARD_PT, CARD_EN), "presentation_pt");
    expect(
      screen.getByRole("figure", { name: "Quote from Taylor H" }),
    ).toBeInTheDocument();
  });

  // Scenario: A malformed insight keeps the JSON fallback
  it("falls back to the JSON block for a malformed insight", () => {
    const malformed = { quote: "Ship small", name: "Taylor H" };
    const { container } = renderColumn(
      slideWith(malformed, malformed),
      "presentation_en",
    );
    expect(screen.getByText("Structured field: insight")).toBeInTheDocument();
    expect(container.querySelector("pre")).toHaveTextContent('"quote"');
    expect(screen.queryByRole("figure")).toBeNull();
    expect(screen.queryByText("Quote card")).toBeNull();
  });

  // Scenario: A malformed insight keeps the JSON fallback (other extras)
  it("keeps the generic label for other structured extras", () => {
    const slide = slideWith(undefined, undefined);
    slide.presentation_en.stats = { quote: "Q", name: "N", handle: "h" };
    renderColumn(slide, "presentation_en");
    expect(screen.getByText("Structured field: stats")).toBeInTheDocument();
    expect(screen.queryByRole("figure")).toBeNull();
  });
});
