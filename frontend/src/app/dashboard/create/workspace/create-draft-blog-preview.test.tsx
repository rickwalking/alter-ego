import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CreateDraftBlogPreview } from "./create-draft-blog-preview";

vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";

const mockFetch = vi.mocked(authenticatedFetch);

function respond(status: number, body: unknown = {}): void {
  mockFetch.mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response);
}

beforeEach(() => {
  mockFetch.mockReset();
});

// Feature: Create-flow UI fixes (AE-0415)
describe("CreateDraftBlogPreview", () => {
  // Scenario: The brief preview of a fresh project is an empty state
  it("shows the empty state, not an error, when nothing was generated (404)", async () => {
    respond(404, { detail: "not found" });
    render(<CreateDraftBlogPreview projectId="p1" />);
    fireEvent.click(screen.getByRole("button", { name: "Load preview" }));

    expect(
      await screen.findByText("No draft content yet."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Could not load draft blog preview."),
    ).not.toBeInTheDocument();
  });

  it("shows the markdown when the preview exists", async () => {
    respond(200, { markdown: "# Draft" });
    render(<CreateDraftBlogPreview projectId="p1" />);
    fireEvent.click(screen.getByRole("button", { name: "Load preview" }));

    expect(await screen.findByText("# Draft")).toBeInTheDocument();
  });

  it("still reports a real failure", async () => {
    respond(500);
    render(<CreateDraftBlogPreview projectId="p1" />);
    fireEvent.click(screen.getByRole("button", { name: "Load preview" }));

    expect(
      await screen.findByText("Could not load draft blog preview."),
    ).toBeInTheDocument();
  });
});
