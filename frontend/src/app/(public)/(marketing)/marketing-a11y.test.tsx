import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Translator } from "@/app/(public)/(marketing)/types";
import { PublicHeaderBrand } from "@/components/layout/public-header";
import { MarketingHero } from "./marketing-hero";
import { FeaturedPostCard } from "./marketing-post-cards";

const HERO_TEXT: Record<string, string> = {
  "hero.titleLine1": "Chat with my",
  "hero.titleHighlight": "Alter-Ego",
};
const t = ((key: string): string =>
  HERO_TEXT[key] ?? key) as unknown as Translator;

describe("public pages accessible names", () => {
  // Scenario: Links are named by their visible text
  it("names the header home link by its visible brand text", () => {
    render(<PublicHeaderBrand />);
    const link = screen.getByRole("link", { name: "Pedro Marins" });
    expect(link).not.toHaveAttribute("aria-label");
    expect(link).toHaveTextContent("Pedro Marins");
  });

  // Scenario: The homepage heading is announced once
  it("announces the hero heading once and hides the glitch copy", () => {
    const { container } = render(<MarketingHero t={t} tc={t} />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Chat with my Alter-Ego" }),
    ).toBeInTheDocument();
    expect(container.querySelector(".hero-glitch")).toHaveAttribute(
      "aria-hidden",
      "true",
    );
  });

  // Scenario: Decorative placeholder text stays out of link names
  it("keeps the image placeholder out of the post link name", () => {
    render(
      <FeaturedPostCard
        locale="en"
        card={{
          id: "p1",
          title: "Unpopular opinion",
          href: "/blog/p1",
          createdAt: "2026-10-20T00:00:00Z",
        }}
      />,
    );
    expect(screen.getByText("▸ carousel_preview.jpg")).toHaveAttribute(
      "aria-hidden",
      "true",
    );
  });
});
