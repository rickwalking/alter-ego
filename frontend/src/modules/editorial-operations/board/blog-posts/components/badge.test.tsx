import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BLOG_POST_BADGE_COLORS, BLOG_POST_BADGE_FALLBACK } from "../constants";
import { BlogPostBadge } from "./badge";

describe("BlogPostBadge", () => {
  it("renders a mapped palette color", () => {
    render(<BlogPostBadge color="cyan">Featured</BlogPostBadge>);
    const badge = screen.getByText("Featured");
    expect(badge).toHaveStyle({
      backgroundColor: BLOG_POST_BADGE_COLORS.cyan!.bg,
    });
  });

  /** Regression: an unknown key used to destructure ``undefined`` and crash the whole listing. */
  it("does not throw for an unmapped color key and renders the neutral fallback", () => {
    expect(() =>
      render(<BlogPostBadge color="draft">Draft</BlogPostBadge>),
    ).not.toThrow();
    const badge = screen.getByText("Draft");
    expect(badge).toHaveStyle({
      backgroundColor: BLOG_POST_BADGE_FALLBACK.bg,
      color: BLOG_POST_BADGE_FALLBACK.text,
    });
  });
});
