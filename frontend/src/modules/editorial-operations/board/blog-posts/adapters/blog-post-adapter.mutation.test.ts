import { describe, expect, it } from "vitest";
import type { BlogPost } from "@/modules/publishing";
import { mapBlogPostToDashboard } from "./blog-post-adapter";

const UPDATED_AT = "2026-07-02T00:00:00Z";
const PUBLISHED_AT = "2026-07-03T00:00:00Z";

function makePost(overrides: Partial<BlogPost> = {}): BlogPost {
  return {
    id: "post-1",
    title: "Title",
    slug: "title",
    status: "published",
    content: {},
    excerpt: "Excerpt",
    editor_comments: [],
    sources: [],
    citations: [],
    ai_suggestions: [],
    ai_generation_metadata: {},
    keywords: [],
    view_count: 3,
    like_count: 0,
    comment_count: 1,
    share_count: 0,
    created_at: "2026-07-01T00:00:00Z",
    updated_at: UPDATED_AT,
    lock_version: 7,
    ...overrides,
  };
}

describe("mapBlogPostToDashboard field mapping", () => {
  // Scenario: Listing renders posts of every workflow status without crashing
  it("maps every dashboard field from the post", () => {
    const post = makePost({
      published_at: PUBLISHED_AT,
      origin: "carousel",
      is_public: true,
    });
    expect(mapBlogPostToDashboard(post)).toEqual({
      id: "post-1",
      title: "Title",
      excerpt: "Excerpt",
      date: PUBLISHED_AT,
      views: 3,
      comments: 1,
      origin: "carousel",
      lockVersion: 7,
      status: "published",
      isPublic: true,
    });
  });

  it("falls back to an empty excerpt, the update date and a standalone origin", () => {
    const dashboard = mapBlogPostToDashboard(
      makePost({ excerpt: null, published_at: null, origin: null }),
    );
    expect(dashboard.excerpt).toBe("");
    expect(dashboard.date).toBe(UPDATED_AT);
    expect(dashboard.origin).toBe("standalone");
  });
});
