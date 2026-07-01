import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BLOG_POST_STATUSES } from "@/modules/publishing";
import type { DashboardBlogPost } from "@/modules/editorial-operations";
import { filterBlogPosts } from "@/modules/editorial-operations";
import {
  FeaturedBlogPost,
  RegularBlogPosts,
} from "@/app/dashboard/blog-posts/blog-posts-grid";
import type { BlogPostActionHandlers } from "@/app/dashboard/blog-posts/types";

const NOOP_ACTIONS: BlogPostActionHandlers = {
  onDelete: () => undefined,
  onHide: () => undefined,
};

// Scenarios: see tests/features/blog-posts-listing-status-badge.feature
// ("Listing renders posts of every workflow status without crashing")

function makeDashboardPost(
  overrides: Partial<DashboardBlogPost>,
): DashboardBlogPost {
  return {
    id: "post-1",
    title: "Post title",
    excerpt: "Excerpt",
    date: "2026-07-01T00:00:00Z",
    views: 10,
    comments: 2,
    status: "draft",
    category: "",
    origin: "standalone",
    lockVersion: 1,
    featured: false,
    ...overrides,
  };
}

describe("blog posts grid (AE-0295)", () => {
  it("renders one card per post for every workflow status without throwing", () => {
    const posts = BLOG_POST_STATUSES.map((status, index) =>
      makeDashboardPost({
        id: `post-${index}`,
        title: `Post ${status}`,
        status,
      }),
    );
    expect(() =>
      render(<RegularBlogPosts posts={posts} actions={NOOP_ACTIONS} />),
    ).not.toThrow();
    for (const status of BLOG_POST_STATUSES) {
      expect(screen.getByText(`Post ${status}`)).toBeInTheDocument();
    }
  });

  it("renders a card with an unknown (null) status using the neutral badge", () => {
    const posts = [makeDashboardPost({ status: null, title: "Drifted post" })];
    expect(() =>
      render(<RegularBlogPosts posts={posts} actions={NOOP_ACTIONS} />),
    ).not.toThrow();
    expect(screen.getByText("Drifted post")).toBeInTheDocument();
    expect(screen.getByText("Unknown")).toBeInTheDocument();
  });

  it("renders the featured card with its real status and the featured tag", () => {
    render(
      <FeaturedBlogPost
        post={makeDashboardPost({ status: "published", featured: true })}
        actions={NOOP_ACTIONS}
      />,
    );
    expect(screen.getByText("Published")).toBeInTheDocument();
    expect(screen.getByText("Featured")).toBeInTheDocument();
  });
});

describe("filterBlogPosts status filter (AE-0295)", () => {
  it("filters by workflow status, not by category", () => {
    const posts = [
      makeDashboardPost({ id: "a", status: "draft" }),
      makeDashboardPost({ id: "b", status: "published" }),
    ];
    const filtered = filterBlogPosts(posts, {
      search: "",
      statusFilter: "draft",
      categoryFilter: "",
    });
    expect(filtered.map((p) => p.id)).toEqual(["a"]);
  });

  it("keeps unknown-status posts visible when no status filter is active", () => {
    const posts = [makeDashboardPost({ status: null })];
    expect(
      filterBlogPosts(posts, {
        search: "",
        statusFilter: "",
        categoryFilter: "",
      }),
    ).toHaveLength(1);
  });
});
