import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import { CarouselPreview } from "./create-carousel-preview";

function project(templateVersion: string | null): CarouselProjectResponse {
  return {
    id: "p1",
    topic: "Topic",
    audience: "Audience",
    niche: "Niche",
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

// Feature: Create-flow UI fixes (AE-0415)
// Scenario: The template version is not doubled
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
