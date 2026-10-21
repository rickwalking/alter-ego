import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import en from "@/i18n/locales/en.json";
import { MarketingStats } from "@/app/(public)/(marketing)/marketing-stats";
import type { Translator } from "@/app/(public)/(marketing)/types";

function translator(key: string): string {
  const value = key
    .split(".")
    .reduce<unknown>(
      (current, segment) =>
        current && typeof current === "object"
          ? (current as Record<string, unknown>)[segment]
          : undefined,
      en.home,
    );
  return typeof value === "string" ? value : key;
}

const t = translator as unknown as Translator;

// Scenario: Published-carousel stat comes from the public carousel total
describe("MarketingStats", () => {
  it("renders the derived public carousel total, not a hardcoded guess", () => {
    render(<MarketingStats t={t} carouselTotal={15} />);

    expect(screen.getByTestId("stats-carousels")).toHaveTextContent("15");
    expect(screen.getByText("Published Carousels")).toBeInTheDocument();
    expect(screen.queryByText("50+")).not.toBeInTheDocument();
  });

  // Scenario: The stats block only shows true and meaningful claims
  it("keeps the years claim and drops the infinite-topics claim", () => {
    render(<MarketingStats t={t} carouselTotal={15} />);

    expect(screen.getByText("8+")).toBeInTheDocument();
    expect(screen.getByText("Years Engineering")).toBeInTheDocument();
    expect(screen.queryByText("∞")).not.toBeInTheDocument();
    expect(screen.queryByText("Topics Explored")).not.toBeInTheDocument();
  });

  it("renders zero honestly when there are no public carousels", () => {
    render(<MarketingStats t={t} carouselTotal={0} />);

    expect(screen.getByTestId("stats-carousels")).toHaveTextContent("0");
  });
});
