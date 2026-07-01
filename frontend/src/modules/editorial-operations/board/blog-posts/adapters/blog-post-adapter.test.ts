import { describe, expect, it } from "vitest";
import type { BlogPost } from "@/modules/publishing";
import { mapBlogPostToDashboard } from "./blog-post-adapter";

// Scenarios: see tests/features/blog-posts-listing-status-badge.feature

function makePost(status: string): BlogPost {
  return {
    id: "post-1",
    title: "Title",
    slug: "title",
    status,
    content: {},
    excerpt: "Excerpt",
    editor_comments: [],
    version_history: [],
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
    updated_at: "2026-07-01T00:00:00Z",
    lock_version: 1,
  };
}

describe("mapBlogPostToDashboard", () => {
  it("maps workflow status into the status slot, never into category", () => {
    const dashboard = mapBlogPostToDashboard(makePost("draft"));
    expect(dashboard.status).toBe("draft");
    expect(dashboard.category).toBe("");
  });

  it("narrows an unknown backend status to null instead of leaking it", () => {
    const dashboard = mapBlogPostToDashboard(makePost("scheduled"));
    expect(dashboard.status).toBeNull();
  });

  it("marks published posts as featured", () => {
    expect(mapBlogPostToDashboard(makePost("published")).featured).toBe(true);
    expect(mapBlogPostToDashboard(makePost("draft")).featured).toBe(false);
  });
});
