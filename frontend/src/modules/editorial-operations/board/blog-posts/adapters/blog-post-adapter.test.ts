import { describe, expect, it } from "vitest";
import type { BlogPost } from "@/modules/publishing";
import { mapBlogPostToDashboard } from "./blog-post-adapter";

function makePost(status: string): BlogPost {
  return {
    id: "post-1",
    title: "Title",
    slug: "title",
    status,
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
    updated_at: "2026-07-01T00:00:00Z",
    lock_version: 1,
  };
}

describe("mapBlogPostToDashboard", () => {
  it("maps workflow status into the status slot", () => {
    const dashboard = mapBlogPostToDashboard(makePost("draft"));
    expect(dashboard.status).toBe("draft");
  });

  it("narrows an unknown backend status to null instead of leaking it", () => {
    const dashboard = mapBlogPostToDashboard(makePost("scheduled"));
    expect(dashboard.status).toBeNull();
  });

  // Scenario: A carousel post waiting for its carousel release is not shown as live
  /** Liveness comes from the API, never from the status. */
  it("maps is_public into isPublic and defaults a missing flag to false", () => {
    const live = { ...makePost("published"), is_public: true };
    const waiting = { ...makePost("published"), is_public: false };
    expect(mapBlogPostToDashboard(live).isPublic).toBe(true);
    expect(mapBlogPostToDashboard(waiting).isPublic).toBe(false);
    expect(mapBlogPostToDashboard(makePost("published")).isPublic).toBe(false);
  });
});
