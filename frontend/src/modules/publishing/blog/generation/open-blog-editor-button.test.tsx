import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

/** Gherkin: tests/features/final-review-copy-edit-ae0505.feature. */

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));
vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { OpenBlogEditorButton } from "./open-blog-editor-button";

const mockFetch = vi.mocked(authenticatedFetch);
const OPEN = "Open in the blog editor";
const CONFIRM = "Open or generate the post";

function openAndConfirm(): void {
  fireEvent.click(screen.getByRole("button", { name: OPEN }));
  fireEvent.click(screen.getByRole("button", { name: CONFIRM }));
}

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), { status });
}

beforeEach(() => {
  mockFetch.mockReset();
  push.mockReset();
});

describe("OpenBlogEditorButton (AE-0505)", () => {
  /** Scenario: The blog body is edited in the blog editor */
  it("opens the draft written for a carousel without a post", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ id: "new-2", generation: { attempt: 1 } }, 202),
    );
    render(<OpenBlogEditorButton projectId="proj-1" />);
    openAndConfirm();
    expect(screen.getByRole("button", { name: "Opening…" })).toBeDisabled();
    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/dashboard/blog-posts/new-2/edit"),
    );
  });

  /** Scenario: The blog preview or the blog editor cannot be opened */
  it("says so when the editor cannot be opened, and can retry", async () => {
    mockFetch.mockResolvedValue(jsonResponse({}, 500));
    render(<OpenBlogEditorButton projectId="proj-1" />);
    openAndConfirm();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not open the blog editor. Try again.",
    );
    expect(screen.getByRole("button", { name: OPEN })).toBeEnabled();
    expect(push).not.toHaveBeenCalled();
  });

  /** Scenario: The blog editor waits for unsaved caption or LinkedIn edits */
  it("waits while the page has unsaved edits", () => {
    render(<OpenBlogEditorButton projectId="proj-1" blocked />);
    expect(screen.getByRole("button", { name: OPEN })).toBeDisabled();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  /** Scenario: The blog body is edited in the blog editor */
  it("asks first and opens nothing when cancelled", () => {
    render(<OpenBlogEditorButton projectId="proj-1" />);
    fireEvent.click(screen.getByRole("button", { name: OPEN }));
    expect(
      screen.getByText(/a draft is generated with AI from the carousel/),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(mockFetch).not.toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
    expect(
      screen.queryByRole("button", { name: CONFIRM }),
    ).not.toBeInTheDocument();
  });
});
