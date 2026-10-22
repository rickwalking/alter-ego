import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import en from "@/i18n/locales/en.json";
import { MarketingFeatures } from "@/app/(public)/(marketing)/marketing-features";
import type { Translator } from "@/app/(public)/(marketing)/types";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    className,
    "aria-label": ariaLabel,
    "data-testid": testId,
  }: {
    children: React.ReactNode;
    href: string;
    className?: string;
    "aria-label"?: string;
    "data-testid"?: string;
  }) => (
    <a
      href={href}
      className={className}
      aria-label={ariaLabel}
      data-testid={testId}
    >
      {children}
    </a>
  ),
}));

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

// Scenario: Every capability card links to its public route
describe("MarketingFeatures", () => {
  it("turns every capability card into a link to its public route", () => {
    render(<MarketingFeatures t={t} />);

    expect(screen.getByRole("link", { name: /^Blog Posts/ })).toHaveAttribute(
      "href",
      "/blog",
    );
    expect(
      screen.getByRole("link", { name: /^Visual Carousels/ }),
    ).toHaveAttribute("href", "/carousels");
    expect(
      screen.getByRole("link", { name: /Chat with My Alter-Ego/ }),
    ).toHaveAttribute("href", "/chat");
  });

  // Scenario: A capability card is one whole-card link
  it("wraps the whole card content in the link", () => {
    render(<MarketingFeatures t={t} />);

    const link = screen.getByRole("link", { name: /^Blog Posts/ });
    expect(within(link).getByText("Blog Posts")).toBeInTheDocument();
    expect(
      within(link).getByText(/Read long-form articles/),
    ).toBeInTheDocument();
  });

  // Scenario: Capability cards are keyboard accessible
  it("gives every card a visible focus ring", () => {
    render(<MarketingFeatures t={t} />);

    const links = [
      screen.getByRole("link", { name: /^Blog Posts/ }),
      screen.getByRole("link", { name: /^Visual Carousels/ }),
      screen.getByRole("link", { name: /Chat with My Alter-Ego/ }),
    ];
    for (const link of links) {
      expect(link.className).toContain("focus-visible:ring-2");
    }
  });
});

describe("MarketingFeatures accessible names", () => {
  // Scenario: Links are named by their visible text
  it("names each card by its visible text instead of a shorter aria-label", () => {
    render(<MarketingFeatures t={t} />);
    for (const link of screen.getAllByRole("link")) {
      expect(link).not.toHaveAttribute("aria-label");
      expect(link).not.toHaveAttribute("aria-labelledby");
    }
    expect(
      screen.getByRole("link", { name: /^Blog Posts Read long-form articles/ }),
    ).toHaveAttribute("href", "/blog");
  });
});
