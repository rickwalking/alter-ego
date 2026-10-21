/**
 * Landing "Latest Posts" cards list carousel projects, so they must
 * open the carousel viewer. Linking to `/blog/<carousel id>` made every visit
 * (and every link prefetch) 404 on `/api/public/blog-posts/<carousel id>`.
 * Gherkin: tests/features/landing-card-language-ae0446.feature
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  FeaturedPostCard,
  SecondaryPostLink,
} from "@/app/(public)/(marketing)/marketing-post-cards";
import type { CarouselListItem } from "@/app/(public)/(marketing)/types";

const POST = {
  id: "787085ba-0000-4000-8000-000000000001",
  title: "Título",
  title_en: "Title",
  subtitle: "Subtítulo",
  subtitle_en: "Subtitle",
  topic: "Tema",
  niche: "IA",
  created_at: "2026-10-20T10:00:00Z",
  design_tokens: null,
} as unknown as CarouselListItem;

const VIEWER_HREF = `/carousels/${POST.id}`;

describe("landing post card links (AE-0446)", () => {
  // Scenario: A landing card opens the carousel it shows
  it("links the featured card to the carousel viewer", () => {
    render(<FeaturedPostCard post={POST} locale="en" />);
    expect(screen.getByRole("link")).toHaveAttribute("href", VIEWER_HREF);
  });

  // Scenario: A landing card opens the carousel it shows
  it("links a secondary card to the carousel viewer", () => {
    render(<SecondaryPostLink post={POST} locale="pt" />);
    expect(screen.getByRole("link")).toHaveAttribute("href", VIEWER_HREF);
  });

  // Scenario: An English title without an English subtitle shows no Portuguese subtitle
  it("never renders the Portuguese subtitle under the English title", () => {
    render(
      <FeaturedPostCard post={{ ...POST, subtitle_en: null }} locale="en" />,
    );
    expect(screen.getByText("Title")).toBeInTheDocument();
    expect(screen.queryByText("Subtítulo")).not.toBeInTheDocument();
  });
});
