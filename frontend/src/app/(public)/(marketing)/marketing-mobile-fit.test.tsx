import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Translator } from "@/app/(public)/(marketing)/types";
import { AboutBio } from "./marketing-about-bio";
import { MarketingHero } from "./marketing-hero";

const t = ((key: string): string => key) as unknown as Translator;

describe("marketing sections on narrow screens", () => {
  // Scenario: The social links wrap instead of overflowing
  it("lets the social links wrap", () => {
    render(<AboutBio t={t} />);
    const row = screen.getByRole("link", {
      name: /about.socialInstagram/,
    }).parentElement!;
    expect(row.style.flexWrap).toBe("wrap");
  });

  // Scenario: The homepage fits a 375 px screen
  it("clips the hero's decorative glow to the section width", () => {
    const { container } = render(<MarketingHero t={t} tc={t} />);
    expect(container.querySelector("section")).toHaveClass("overflow-x-clip");
  });
});
