import { fireEvent, render, screen } from "@testing-library/react";
import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { DashboardBlogPost } from "@/modules/editorial-operations";
import {
  BlogPostCardActions,
  DeleteConfirmModal,
} from "@/app/dashboard/blog-posts/blog-posts-actions";
import { useBlogPostActions } from "@/app/dashboard/blog-posts/use-blog-post-actions";
import type { BlogPostActionHandlers } from "@/app/dashboard/blog-posts/types";

// Scenarios: see tests/features/blog-posts-management.feature

function makePost(overrides: Partial<DashboardBlogPost>): DashboardBlogPost {
  return {
    id: "post-1",
    title: "Post title",
    excerpt: "Excerpt",
    date: "2026-07-01T00:00:00Z",
    views: 0,
    comments: 0,
    status: "draft",
    category: "",
    origin: "standalone",
    lockVersion: 1,
    featured: false,
    ...overrides,
  };
}

interface MockHandlers extends BlogPostActionHandlers {
  onDelete: ReturnType<typeof vi.fn<(post: DashboardBlogPost) => void>>;
  onHide: ReturnType<typeof vi.fn<(post: DashboardBlogPost) => void>>;
}

function handlers(): MockHandlers {
  return {
    onDelete: vi.fn<(post: DashboardBlogPost) => void>(),
    onHide: vi.fn<(post: DashboardBlogPost) => void>(),
  };
}

describe("BlogPostCardActions (AE-0296)", () => {
  it("always offers Edit as a link to the edit page", () => {
    render(<BlogPostCardActions post={makePost({})} actions={handlers()} />);
    const editLink = screen.getByRole("link");
    expect(editLink).toHaveAttribute(
      "href",
      "/dashboard/blog-posts/post-1/edit",
    );
    expect(screen.getByText("Edit")).toBeInTheDocument();
  });

  it("offers Hide only for published posts", () => {
    const { rerender } = render(
      <BlogPostCardActions post={makePost({})} actions={handlers()} />,
    );
    expect(screen.queryByText("Hide (revert to draft)")).toBeNull();

    rerender(
      <BlogPostCardActions
        post={makePost({ status: "published" })}
        actions={handlers()}
      />,
    );
    expect(screen.getByText("Hide (revert to draft)")).toBeInTheDocument();
  });

  it("hides Delete for carousel-origin posts but keeps Hide", () => {
    render(
      <BlogPostCardActions
        post={makePost({ origin: "carousel", status: "published" })}
        actions={handlers()}
      />,
    );
    expect(screen.queryByText("Delete")).toBeNull();
    expect(screen.getByText("Hide (revert to draft)")).toBeInTheDocument();
  });

  it("routes Delete and Hide clicks to the handlers", () => {
    const h = handlers();
    render(
      <BlogPostCardActions
        post={makePost({ status: "published" })}
        actions={h}
      />,
    );
    fireEvent.click(screen.getByText("Delete"));
    expect(h.onDelete).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByText("Hide (revert to draft)"));
    expect(h.onHide).toHaveBeenCalledOnce();
  });
});

describe("useBlogPostActions delete confirmation (AE-0296)", () => {
  it("cancelling the dialog sends no delete request", async () => {
    const deletePost = vi.fn();
    const unpublish = vi.fn();
    const { result } = renderHook(() =>
      useBlogPostActions({ deletePost, unpublish }),
    );

    act(() => result.current.actions.onDelete(makePost({})));
    expect(result.current.deleteTarget).not.toBeNull();

    act(() => result.current.cancelDelete());
    expect(result.current.deleteTarget).toBeNull();
    expect(deletePost).not.toHaveBeenCalled();
  });

  it("confirming calls deletePost with id and lock version", async () => {
    const deletePost = vi.fn().mockResolvedValue(true);
    const unpublish = vi.fn();
    const { result } = renderHook(() =>
      useBlogPostActions({ deletePost, unpublish }),
    );

    act(() => result.current.actions.onDelete(makePost({ lockVersion: 7 })));
    await act(async () => {
      await result.current.confirmDelete();
    });
    expect(deletePost).toHaveBeenCalledWith("post-1", 7);
    expect(result.current.deleteTarget).toBeNull();
  });

  it("surfaces a localized error when the mutation is rejected", async () => {
    const { BlogPostMutationError } = await import("@/modules/publishing");
    const deletePost = vi
      .fn()
      .mockRejectedValue(new BlogPostMutationError("version_conflict"));
    const unpublish = vi.fn();
    const { result } = renderHook(() =>
      useBlogPostActions({ deletePost, unpublish }),
    );

    act(() => result.current.actions.onDelete(makePost({})));
    await act(async () => {
      await result.current.confirmDelete();
    });
    expect(result.current.actionError).toContain("changed in another session");
  });
});

describe("DeleteConfirmModal (AE-0296)", () => {
  it("renders nothing without a target post", () => {
    const { container } = render(
      <DeleteConfirmModal
        post={null}
        onConfirm={() => undefined}
        onCancel={() => undefined}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the confirmation copy and fires confirm/cancel", () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <DeleteConfirmModal
        post={makePost({})}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );
    expect(
      screen.getByText("Are you sure you want to delete this blog post?"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByText("Cancel"));
    expect(onCancel).toHaveBeenCalledOnce();
    fireEvent.click(screen.getAllByText("Delete").at(-1) as HTMLElement);
    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
