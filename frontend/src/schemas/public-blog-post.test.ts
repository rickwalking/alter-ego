import { describe, expect, it } from "vitest";
import { carouselProjectListResponseSchema } from "./carousel";
import {
  publicBlogPostListResponseSchema,
  publicBlogPostResponseSchema,
} from "./public-blog-post";

// Scenarios: see tests/features/public-blog-detail.feature

const VALID_SUMMARY = {
  id: "e7e871c7-9f5f-4b70-b226-a2d2adeb06fa",
  slug: "a-post",
  title: "A post",
  excerpt: "Excerpt",
  featured_image_url: null,
  published_at: "2026-07-01T00:00:00Z",
  meta_title: null,
  meta_description: null,
  keywords: ["ai"],
  canonical_url: null,
  origin: "standalone",
  project_id: null,
};

// Editorial/AI internals that must never surface on any public feed.
const BLOG_INTERNAL_KEYS = [
  "author_id",
  "reviewer_id",
  "editor_comments",
  "version_history",
  "ai_suggestions",
  "ai_generation_metadata",
];

describe("public blog post schemas (AE-0297)", () => {
  it("parses a valid lean detail payload", () => {
    const parsed = publicBlogPostResponseSchema.parse({
      ...VALID_SUMMARY,
      content: { markdown: "# Body" },
    });
    expect(parsed.title).toBe("A post");
    expect(parsed.content).toEqual({ markdown: "# Body" });
  });

  it("rejects a payload missing required fields", () => {
    const result = publicBlogPostResponseSchema.safeParse({ id: "x" });
    expect(result.success).toBe(false);
  });

  it("parses the list envelope", () => {
    const parsed = publicBlogPostListResponseSchema.parse({
      items: [VALID_SUMMARY],
      total: 1,
      limit: 20,
      offset: 0,
    });
    expect(parsed.items).toHaveLength(1);
  });

  it("does not model any internal editorial field", () => {
    const keys = Object.keys(publicBlogPostResponseSchema.shape);
    for (const internal of BLOG_INTERNAL_KEYS) {
      expect(keys).not.toContain(internal);
    }
    expect(keys).not.toContain("status");
    expect(keys).not.toContain("lock_version");
  });

  it("fallback carousel feed schema models none of the blog internals", () => {
    // The fail-open listing fallback renders the carousel feed through its own
    // schema; assert that schema cannot carry blog editorial internals.
    const itemShape = carouselProjectListResponseSchema.shape.items.element;
    const keys = Object.keys(itemShape.shape);
    for (const internal of BLOG_INTERNAL_KEYS) {
      expect(keys).not.toContain(internal);
    }
  });
});
