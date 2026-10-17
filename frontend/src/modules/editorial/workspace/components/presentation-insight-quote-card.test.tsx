// AE-0407 — Gherkin: frontend/tests/features/content-review-insight-card-ae0407.feature
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PresentationInsightQuoteCard } from "./presentation-insight-quote-card";

const INSIGHT = {
  quote: "Ship small",
  name: "Taylor H",
  handle: "@taylorhbuilds",
};

describe("PresentationInsightQuoteCard", () => {
  // Scenario: The quote card renders in both locale columns
  it("shows the quote, the name and the @handle · X source", () => {
    const { container } = render(
      <PresentationInsightQuoteCard insight={INSIGHT} />,
    );
    expect(container.querySelector("blockquote")).toHaveTextContent(
      "Ship small",
    );
    expect(screen.getByText("Taylor H")).toBeInTheDocument();
    expect(screen.getByText("@taylorhbuilds · X")).toBeInTheDocument();
  });

  // Scenario: The quote card is an accessible figure
  it("is a figure named after the author with a figcaption", () => {
    const { container } = render(
      <PresentationInsightQuoteCard insight={INSIGHT} />,
    );
    const figure = screen.getByRole("figure", { name: "Quote from Taylor H" });
    const caption = container.querySelector("figcaption");
    expect(caption).toHaveTextContent("Taylor H @taylorhbuilds · X");
    expect(figure).toContainElement(caption);
    expect(container.querySelector("a")).toBeNull();
  });
});
