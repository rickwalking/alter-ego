/**
 * Scenarios: tests/features/blog-dashboard-ae0411.feature (List).
 */
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DashboardBlogPost } from "@/modules/editorial-operations";
import { BlogPostsList } from "@/app/dashboard/blog-posts/blog-posts-grid";
import { BlogPostsFilters } from "@/app/dashboard/blog-posts/blog-posts-filters";
import type { BlogPostActionHandlers } from "@/app/dashboard/blog-posts/types";

const NOOP_ACTIONS: BlogPostActionHandlers = {
  onDelete: () => undefined,
  onHide: () => undefined,
};

function makePost(overrides: Partial<DashboardBlogPost>): DashboardBlogPost {
  return {
    id: "post-1",
    title: "Post title",
    excerpt: "Excerpt",
    date: "2026-07-01T00:00:00Z",
    views: 0,
    comments: 0,
    status: "published",
    origin: "standalone",
    lockVersion: 1,
    isPublic: true,
    ...overrides,
  };
}

function noop(): void {
  return undefined;
}

describe("BlogPostsList (AE-0411)", () => {
  // Scenario: Every post is listed, with at most one featured card
  it("renders every post and features only the first live one", () => {
    const posts = ["a", "b", "c"].map((id) =>
      makePost({ id, title: `Post ${id}` }),
    );
    render(
      <BlogPostsList posts={posts} hasNoPosts={false} actions={NOOP_ACTIONS} />,
    );
    for (const id of ["a", "b", "c"]) {
      expect(screen.getByText(`Post ${id}`)).toBeInTheDocument();
    }
    expect(screen.getAllByText("Featured")).toHaveLength(1);
    const featuredCard = screen.getByText("Featured").closest("div.grid");
    expect(
      within(featuredCard as HTMLElement).getByText("Post a"),
    ).toBeInTheDocument();
  });

  // Scenario: A carousel post waiting for its carousel release is not shown as live
  it("shows a not-live badge and never features a post that is not public", () => {
    const waiting = makePost({
      id: "w",
      title: "Waiting",
      origin: "carousel",
      isPublic: false,
    });
    render(
      <BlogPostsList
        posts={[waiting]}
        hasNoPosts={false}
        actions={NOOP_ACTIONS}
      />,
    );
    expect(screen.getByText("Waiting")).toBeInTheDocument();
    expect(screen.getByText("Awaiting carousel release")).toBeInTheDocument();
    expect(screen.queryByText("Published")).toBeNull();
    expect(screen.queryByText("Featured")).toBeNull();
    expect(
      screen.getByText(/readers only see it once its carousel is published/),
    ).toBeInTheDocument();
  });

  it("features a later live post when the newest one is not live", () => {
    const posts = [
      makePost({ id: "w", title: "Waiting", isPublic: false }),
      makePost({ id: "l", title: "Live" }),
    ];
    render(
      <BlogPostsList posts={posts} hasNoPosts={false} actions={NOOP_ACTIONS} />,
    );
    expect(screen.getAllByText("Featured")).toHaveLength(1);
    expect(screen.getByText("Waiting")).toBeInTheDocument();
  });

  // Scenario: An empty search shows an empty state
  it("shows the no-results state when filters match nothing", () => {
    render(
      <BlogPostsList posts={[]} hasNoPosts={false} actions={NOOP_ACTIONS} />,
    );
    expect(screen.getByText("No posts match your filters")).toBeInTheDocument();
  });

  // Scenario: No posts at all shows the empty state
  it("shows the empty state when there are no posts", () => {
    render(<BlogPostsList posts={[]} hasNoPosts actions={NOOP_ACTIONS} />);
    expect(screen.getByText(/No blog posts yet/)).toBeInTheDocument();
  });
});

describe("BlogPostsFilters counter (AE-0411)", () => {
  // Scenario: The counter shows the real number of posts
  it("shows the real count", () => {
    render(
      <BlogPostsFilters
        statusFilter=""
        onStatusFilterChange={noop}
        shownCount={2}
        totalCount={2}
      />,
    );
    expect(screen.getByText("2 posts")).toBeInTheDocument();
    expect(screen.queryByText("24 posts")).toBeNull();
  });

  it("uses the singular for one post", () => {
    render(
      <BlogPostsFilters
        statusFilter=""
        onStatusFilterChange={noop}
        shownCount={1}
        totalCount={1}
      />,
    );
    expect(screen.getByText("1 post")).toBeInTheDocument();
  });

  it("shows shown-of-total when filters hide posts", () => {
    render(
      <BlogPostsFilters
        statusFilter="draft"
        onStatusFilterChange={noop}
        shownCount={1}
        totalCount={5}
      />,
    );
    expect(screen.getByText("1 of 5 posts")).toBeInTheDocument();
  });

  it("no longer offers a category filter", () => {
    render(
      <BlogPostsFilters
        statusFilter=""
        onStatusFilterChange={noop}
        shownCount={0}
        totalCount={0}
      />,
    );
    expect(screen.getAllByRole("combobox")).toHaveLength(1);
    expect(screen.queryByText("All Categories")).toBeNull();
  });
});
