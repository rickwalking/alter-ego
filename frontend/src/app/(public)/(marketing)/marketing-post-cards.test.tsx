/**
 * Landing "Latest Posts" cards render a published blog post card view-model.
 * Gherkin: tests/features/landing-latest-posts-published-only-ae0449.feature
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  FeaturedPostCard,
  SecondaryPostLink,
} from "@/app/(public)/(marketing)/marketing-post-cards";
import type { NeonBlogPostCardProps } from "@/schemas/neon-blog-post-card";

const CARD: NeonBlogPostCardProps = {
  id: "aa11bb22-0000-4000-8000-000000000005",
  title: "Title",
  subtitle: "Subtitle",
  niche: "IA",
  imageUrl: "https://cdn.example/cover.jpg",
  createdAt: "2026-10-20T10:00:00Z",
  href: "/blog/aa11bb22-0000-4000-8000-000000000005",
};

describe("landing post cards", () => {
  // Scenario: Only published posts are listed and they open the public blog post
  it("links the featured card to the public blog post", () => {
    render(<FeaturedPostCard card={CARD} locale="en" />);
    expect(screen.getByRole("link")).toHaveAttribute("href", CARD.href);
    expect(screen.getByText("Subtitle")).toBeInTheDocument();
    expect(screen.getByText("IA")).toBeInTheDocument();
  });

  // Scenario: Only published posts are listed and they open the public blog post
  it("links a secondary card to the public blog post", () => {
    render(<SecondaryPostLink card={CARD} locale="pt" />);
    expect(screen.getByRole("link")).toHaveAttribute("href", CARD.href);
    expect(screen.getByText("20/10/2026")).toBeInTheDocument();
  });

  it("falls back to a generic category without a niche", () => {
    render(
      <SecondaryPostLink card={{ ...CARD, niche: undefined }} locale="en" />,
    );
    expect(screen.getByText("Post")).toBeInTheDocument();
  });
});
