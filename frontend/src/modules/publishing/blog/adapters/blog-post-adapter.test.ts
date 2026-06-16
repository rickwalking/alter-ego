import { describe, it, expect } from "vitest";
import { mapProjectToBlogPostCard } from "@/modules/publishing/blog/adapters/blog-post-adapter";
import type { CarouselProjectResponse } from "@/schemas/carousel";

describe("mapProjectToBlogPostCard", () => {
  const baseProject: CarouselProjectResponse = {
    id: "550e8400-e29b-41d4-a716-446655440000",
    topic: "AI Topic",
    audience: "devs",
    niche: "AI",
    title: "Portuguese Title",
    subtitle: "Subtitle PT",
    title_en: "English Title",
    subtitle_en: "Subtitle EN",
    theme: "tech",
    status: "completed",
    blog_markdown: null,
    caption: null,
    design_tokens: { images: { hero: "/hero.jpg" } },
    created_at: "2026-05-27T10:00:00Z",
    updated_at: "2026-05-27T12:00:00Z",
  };

  it("uses English title when locale is en", () => {
    const result = mapProjectToBlogPostCard(baseProject, "en");
    expect(result.title).toBe("English Title");
    expect(result.subtitle).toContain("Subtitle EN");
  });

  it("uses Portuguese title when locale is pt", () => {
    const result = mapProjectToBlogPostCard(baseProject, "pt");
    expect(result.title).toBe("Portuguese Title");
  });

  it("builds href from project id", () => {
    const result = mapProjectToBlogPostCard(baseProject, "en");
    expect(result.href).toBe(`/blog/${baseProject.id}`);
  });

  it("rewrites preview hero URLs to public image routes", () => {
    const project: CarouselProjectResponse = {
      ...baseProject,
      design_tokens: {
        images: {
          hero: "/api/carousels/proj-1/preview/images/hero.jpg?lang=pt",
        },
      },
    };
    const result = mapProjectToBlogPostCard(project, "en");
    expect(result.imageUrl).toBe("/api/carousels/proj-1/images/hero.jpg");
  });
});
