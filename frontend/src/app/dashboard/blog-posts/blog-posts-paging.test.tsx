import { act, render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { formatBlogPostDate } from "@/modules/editorial-operations";
import { BlogPostsPager } from "@/app/dashboard/blog-posts/blog-posts-pager";
import {
  BLOG_POSTS_PAGE_SIZE,
  BLOG_POSTS_SEARCH_DEBOUNCE_MS,
  blogPostsPageCount,
  blogPostsPageFilters,
} from "@/app/dashboard/blog-posts/blog-posts-paging";
import { useBlogPostsPaging } from "@/app/dashboard/blog-posts/use-blog-posts-paging";

// Scenarios: see tests/features/qa-followups-ae0416.feature (blog list paging)

describe("blog list page filters (AE-0416)", () => {
  // Scenario: The first page asks the API for one page of posts
  it("asks for the first page without empty filters", () => {
    expect(blogPostsPageFilters({ page: 0, status: "", search: "  " })).toEqual(
      { limit: BLOG_POSTS_PAGE_SIZE, offset: 0 },
    );
    expect(BLOG_POSTS_PAGE_SIZE).toBe(24);
  });

  // Scenario: The next page asks for the next offset
  it("moves the offset by one page and keeps the filters", () => {
    expect(
      blogPostsPageFilters({ page: 2, status: "draft", search: " agents " }),
    ).toEqual({ limit: 24, offset: 48, status: "draft", search: "agents" });
  });

  it("counts at least one page", () => {
    expect(blogPostsPageCount(0)).toBe(1);
    expect(blogPostsPageCount(24)).toBe(1);
    expect(blogPostsPageCount(25)).toBe(2);
    expect(blogPostsPageCount(50)).toBe(3);
  });
});

describe("useBlogPostsPaging (AE-0416)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  // Scenario: Status and search filter every post, not just the loaded page
  it("sends the page, then resets to page 1 on a new status", () => {
    const setFilters = vi.fn();
    const { result } = renderHook(() => useBlogPostsPaging(setFilters));
    act(() => result.current.goToPage(1));
    expect(setFilters).toHaveBeenLastCalledWith({ limit: 24, offset: 24 });
    expect(result.current.page).toBe(1);
    act(() => result.current.changeStatus("draft"));
    expect(setFilters).toHaveBeenLastCalledWith({
      limit: 24,
      offset: 0,
      status: "draft",
    });
    expect(result.current.page).toBe(0);
    expect(result.current.statusFilter).toBe("draft");
  });

  it("searches after a pause in typing, keeping the latest status", () => {
    const setFilters = vi.fn();
    const { result } = renderHook(() => useBlogPostsPaging(setFilters));
    act(() => result.current.goToPage(2));
    act(() => result.current.changeSearch("ag"));
    act(() => result.current.changeSearch("agents"));
    expect(result.current.searchInput).toBe("agents");
    act(() => result.current.changeStatus("published"));
    setFilters.mockClear();
    act(() => {
      vi.advanceTimersByTime(BLOG_POSTS_SEARCH_DEBOUNCE_MS);
    });
    expect(setFilters).toHaveBeenCalledTimes(1);
    expect(setFilters).toHaveBeenCalledWith({
      limit: 24,
      offset: 0,
      status: "published",
      search: "agents",
    });
  });

  it("drops a pending search when it unmounts", () => {
    const setFilters = vi.fn();
    const { result, unmount } = renderHook(() =>
      useBlogPostsPaging(setFilters),
    );
    act(() => result.current.changeSearch("agents"));
    unmount();
    vi.advanceTimersByTime(BLOG_POSTS_SEARCH_DEBOUNCE_MS);
    expect(setFilters).not.toHaveBeenCalled();
  });
});

describe("BlogPostsPager (AE-0416)", () => {
  // Scenario: The pager is hidden when everything fits on one page
  it("renders nothing for a single page", () => {
    const { container } = render(
      <BlogPostsPager page={0} pageCount={1} onPageChange={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  // Scenario: The previous button is disabled on the first page
  it("disables Previous on the first page and moves forward", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    render(
      <BlogPostsPager page={0} pageCount={3} onPageChange={onPageChange} />,
    );
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(onPageChange).toHaveBeenCalledWith(1);
  });

  it("disables Next on the last page and moves back", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    render(
      <BlogPostsPager page={2} pageCount={3} onPageChange={onPageChange} />,
    );
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    expect(
      screen.getByRole("navigation", { name: "Blog post pages" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(onPageChange).toHaveBeenCalledWith(1);
  });
});

describe("formatBlogPostDate (AE-0416)", () => {
  it("formats the date in the dashboard language", () => {
    const date = "2026-10-17T12:00:00Z";
    expect(formatBlogPostDate(date, "en")).toBe("Oct 17, 2026");
    // AE-0417: one dashboard/public date format (AE-0412): pt "17/10/2026".
    expect(formatBlogPostDate(date, "pt")).toBe("17/10/2026");
  });
});
