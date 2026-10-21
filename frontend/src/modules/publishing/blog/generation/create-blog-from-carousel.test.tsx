import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

/** Gherkin: tests/features/blog_generate_ae0425.feature. */

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));
vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { CreateBlogFromCarousel } from "./create-blog-from-carousel";

const mockFetch = vi.mocked(authenticatedFetch);

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  mockFetch.mockReset();
  push.mockReset();
});

describe("CreateBlogFromCarousel (AE-0425)", () => {
  it("creates a draft from the carousel and opens its editor", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(
        { id: "new-1", generation: { attempt: 1, warnings: [] } },
        202,
      ),
    );
    render(<CreateBlogFromCarousel projectId="proj-1" isPublic />);
    expect(
      screen.queryByTestId("carousel-private-warning"),
    ).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", {
        name: "Create blog post from this carousel",
      }),
    );
    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/dashboard/blog-posts/new-1/edit"),
    );
    expect(mockFetch.mock.calls[0]?.[1]?.body).toBe(
      JSON.stringify({ project_id: "proj-1" }),
    );
  });

  it("links to the existing post instead of creating a duplicate", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(
        { code: "blog_post_exists_for_project", post_id: "old-7" },
        409,
      ),
    );
    render(<CreateBlogFromCarousel projectId="proj-1" isPublic />);
    fireEvent.click(screen.getByRole("button"));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "This carousel already has a blog post",
    );
    expect(
      screen.getByRole("link", { name: "Open the existing post" }),
    ).toHaveAttribute("href", "/dashboard/blog-posts/old-7/edit");
    expect(push).not.toHaveBeenCalled();
  });

  it("warns up front when the carousel is private", () => {
    render(<CreateBlogFromCarousel projectId="proj-1" isPublic={false} />);
    expect(screen.getByTestId("carousel-private-warning")).toHaveTextContent(
      "This carousel is private",
    );
  });

  it("shows a failure and re-enables the button", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "x" }, 500));
    render(<CreateBlogFromCarousel projectId="proj-1" isPublic />);
    fireEvent.click(screen.getByRole("button"));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not create the blog post",
    );
    expect(screen.getByRole("button")).not.toBeDisabled();
  });
});
