/** Gherkin: frontend/tests/features/content-review-insight-card-ae0407.feature */
import { describe, expect, it } from "vitest";
import {
  formatQuoteHandle,
  isPresentationInsightQuotePayload,
  parsePresentationInsightQuote,
} from "./presentation-insight-quote";

const CARD = {
  quote: "Ship small",
  attribution: "Taylor H",
  name: "Taylor H",
  handle: "taylorhbuilds",
  quote_id: "q1",
};

describe("formatQuoteHandle", () => {
  // Scenario: The quote card renders in both locale columns
  it("adds the @ prefix to a bare handle", () => {
    expect(formatQuoteHandle("taylorhbuilds")).toBe("@taylorhbuilds");
  });

  // Scenario: A handle that already starts with @ is not doubled
  it("does not double an existing @ prefix", () => {
    expect(formatQuoteHandle("@taylorhbuilds")).toBe("@taylorhbuilds");
    expect(formatQuoteHandle(" @@taylorhbuilds ")).toBe("@taylorhbuilds");
  });
});

describe("parsePresentationInsightQuote", () => {
  // Scenario: The quote card renders in both locale columns
  it("returns the display card for a valid payload", () => {
    expect(parsePresentationInsightQuote(CARD)).toEqual({
      quote: "Ship small",
      name: "Taylor H",
      handle: "@taylorhbuilds",
    });
  });

  // Scenario: A url in the payload is never shown
  it("drops a url field", () => {
    const parsed = parsePresentationInsightQuote({
      ...CARD,
      url: "https://x.com/taylorhbuilds/status/1",
    });
    expect(parsed).not.toHaveProperty("url");
    expect(JSON.stringify(parsed)).not.toContain("https://");
  });

  // Scenario: The name falls back to the attribution
  it("falls back to the attribution when the name is missing", () => {
    const withoutName = { quote: "Q", handle: "h", attribution: "Taylor H" };
    expect(parsePresentationInsightQuote(withoutName)?.name).toBe("Taylor H");
    expect(
      parsePresentationInsightQuote({ ...CARD, name: " ", attribution: "A" })
        ?.name,
    ).toBe("A");
  });

  // Scenario: A malformed insight keeps the JSON fallback
  it.each([
    ["null", null],
    ["a string", "Ship small"],
    ["an array", [CARD]],
    ["no quote", { ...CARD, quote: undefined }],
    ["a blank quote", { ...CARD, quote: "  " }],
    ["no handle", { ...CARD, handle: undefined }],
    ["a numeric handle", { ...CARD, handle: 42 }],
    ["no name nor attribution", { quote: "Q", handle: "h" }],
  ])("returns null for %s", (_label, value) => {
    expect(isPresentationInsightQuotePayload(value)).toBe(false);
    expect(parsePresentationInsightQuote(value)).toBeNull();
  });
});
