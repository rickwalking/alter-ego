/**
 * Scenarios: tests/features/blog_generate_ae0425.feature ("Start a standalone
 * blog from a topic", "Generation copy is localized").
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));
vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { GenerateBlogPostAction } from "@/app/dashboard/blog-posts/generate-blog-post-modal";

const mockFetch = vi.mocked(authenticatedFetch);

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function openModal(): void {
  render(<GenerateBlogPostAction />);
  fireEvent.click(screen.getByRole("button", { name: "Generate with AI" }));
}

beforeEach(() => {
  mockFetch.mockReset();
  push.mockReset();
});

describe("GenerateBlogPostAction (AE-0425)", () => {
  it("generates a draft from a topic and opens its editor", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ id: "gen-1", generation: { attempt: 1 } }, 202),
    );
    openModal();
    const submit = screen.getByRole("button", { name: "Generate draft" });
    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Topic"), {
      target: { value: "  Por que eu parei de usar copilots  " },
    });
    expect(submit).not.toBeDisabled();
    fireEvent.click(submit);
    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/dashboard/blog-posts/gen-1/edit"),
    );
    expect(mockFetch.mock.calls[0]?.[0]).toBe("/api/blog-posts/generate");
    expect(mockFetch.mock.calls[0]?.[1]?.body).toBe(
      JSON.stringify({ topic: "Por que eu parei de usar copilots" }),
    );
  });

  it("keeps the modal open with an error when the start fails", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "x" }, 429));
    openModal();
    fireEvent.change(screen.getByLabelText("Topic"), {
      target: { value: "Tema" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Generate draft" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not start the generation",
    );
    expect(push).not.toHaveBeenCalled();
  });

  it("closes on cancel", () => {
    openModal();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByLabelText("Topic")).not.toBeInTheDocument();
  });
});
