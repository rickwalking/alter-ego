/**
 * Scenarios: tests/features/blog-dashboard-ae0411.feature ("Creating a post
 * that fails shows an error", "Dashboard copy is localized").
 */
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  BLOG_POST_ERR_SLUG_CONFLICT,
  BlogPostMutationError,
} from "@/modules/publishing";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

import { useNewBlogPost } from "@/app/dashboard/blog-posts/use-new-blog-post";

beforeEach(() => {
  push.mockReset();
});

async function submitWith(
  create: Parameters<typeof useNewBlogPost>[0],
  title: string,
): Promise<{ current: ReturnType<typeof useNewBlogPost> }> {
  const { result } = renderHook(() => useNewBlogPost(create));
  act(() => result.current.show());
  act(() => result.current.setTitle(title));
  await act(async () => {
    await result.current.submit();
  });
  return result;
}

describe("useNewBlogPost (AE-0411, AE-0474)", () => {
  // Scenario: Submitting the form creates the draft and opens the editor
  it("creates the draft with the typed title and opens the editor", async () => {
    const create = vi.fn().mockResolvedValue({ id: "new-1" });
    const result = await submitWith(create, "  Meu post  ");
    expect(create).toHaveBeenCalledWith({
      title: "Meu post",
      content: { body: "" },
      excerpt: "",
    });
    expect(push).toHaveBeenCalledWith("/dashboard/blog-posts/new-1/edit");
    expect(result.current.createError).toBeNull();
  });

  // Scenario: The form cannot be submitted without a title
  it("creates nothing for a blank title", async () => {
    const create = vi.fn();
    const result = await submitWith(create, "   ");
    expect(create).not.toHaveBeenCalled();
    expect(result.current.canSubmit).toBe(false);
  });

  // Scenario: Creating a post that fails shows an error
  it("shows a create error and re-enables the form on failure", async () => {
    const create = vi.fn().mockRejectedValue(new Error("boom"));
    const result = await submitWith(create, "Post");
    expect(result.current.creating).toBe(false);
    expect(result.current.open).toBe(true);
    expect(result.current.createError).toBe(
      "Could not create the post. Try again.",
    );
    expect(push).not.toHaveBeenCalled();
  });

  // Scenario: Dashboard copy is localized
  it("explains a slug conflict", async () => {
    const create = vi
      .fn()
      .mockRejectedValue(
        new BlogPostMutationError(BLOG_POST_ERR_SLUG_CONFLICT),
      );
    const result = await submitWith(create, "Post");
    expect(result.current.createError).toMatch(/already uses this slug/);
  });

  // Scenario: Clicking New Post opens a form and creates nothing
  it("opens the form without creating anything", () => {
    const create = vi.fn();
    const { result } = renderHook(() => useNewBlogPost(create));
    act(() => result.current.show());
    expect(result.current.open).toBe(true);
    expect(create).not.toHaveBeenCalled();
  });
});
