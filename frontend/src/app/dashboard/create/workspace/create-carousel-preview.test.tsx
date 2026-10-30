import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import { CarouselPreview } from "./create-carousel-preview";

const blogHref = vi.hoisted(() => ({ value: null as string | null }));
vi.mock("@/modules/publishing", () => ({
  useCarouselPublicPostHref: () => ({ href: blogHref.value, refetch: vi.fn() }),
}));

function project(templateVersion: string | null): CarouselProjectResponse {
  return {
    id: "p1",
    topic: "Topic",
    audience: "Audience",
    niche: "Niche",
    language: "pt-BR",
    title: "Title",
    subtitle: null,
    theme: "auto",
    status: "completed",
    primary_color: null,
    accent_color: null,
    background_color: null,
    blog_markdown: null,
    caption: null,
    template_version: templateVersion,
    created_at: "2026-10-16T00:00:00Z",
    updated_at: "2026-10-16T00:00:00Z",
  };
}

/** Scenario: The template version is not doubled */
describe("CarouselPreview template version (AE-0415, B33)", () => {
  it("shows a stored 'v2' as 'v2', not 'vv2'", () => {
    render(<CarouselPreview project={project("v2")} />);
    expect(screen.getByText("v2")).toBeInTheDocument();
    expect(screen.queryByText("vv2")).not.toBeInTheDocument();
  });

  it("prefixes a bare version number", () => {
    render(<CarouselPreview project={project("3")} />);
    expect(screen.getByText("v3")).toBeInTheDocument();
  });

  it("shows no version chip without a version", () => {
    render(<CarouselPreview project={project(null)} />);
    expect(screen.queryByText(/^v\d/)).not.toBeInTheDocument();
  });
});

describe("CarouselPreview View Blog link", () => {
  /** Scenario: The workspace links the carousel's published blog post */
  it("links the carousel's published blog post", () => {
    blogHref.value = "/blog/b1";
    render(<CarouselPreview project={project(null)} />);
    expect(
      screen.getByRole("link", { name: "View Blog Post" }),
    ).toHaveAttribute("href", "/blog/b1");
  });

  /** Scenario: The workspace hides View Blog Post when the carousel has no published post */
  it("hides the link when there is no published post", () => {
    blogHref.value = null;
    render(<CarouselPreview project={project(null)} />);
    expect(
      screen.queryByRole("link", { name: "View Blog Post" }),
    ).not.toBeInTheDocument();
  });
});

describe("CarouselPreview display title", () => {
  /** Scenario: The workspace preview uses the same display title */
  it("prefers the stripped title for the preview heading", () => {
    render(
      <CarouselPreview
        project={{ ...project(null), title: "**Bold** Moves" }}
      />,
    );
    expect(
      screen.getByRole("heading", { name: "Bold Moves" }),
    ).toBeInTheDocument();
  });

  /** Scenario: The workspace preview uses the same display title */
  it("falls back to the topic when the title is blank", () => {
    render(<CarouselPreview project={{ ...project(null), title: "   " }} />);
    expect(screen.getByRole("heading", { name: "Topic" })).toBeInTheDocument();
  });
});
