import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

/** Gherkin: tests/features/blog_generate_ae0425.feature. */

vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { BlogGenerationStatus } from "./blog-generation-status";
import { generationPollInterval } from "./use-blog-generation";
import type { BlogPost } from "../types";

const mockFetch = vi.mocked(authenticatedFetch);

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function post(
  generation: Record<string, unknown>,
  projectId: string | null = null,
): BlogPost {
  return {
    id: "post-1",
    project_id: projectId,
    title: "T",
    ai_generation_metadata: { generation },
  } as unknown as BlogPost;
}

function renderStatus(unsavedChanges = false): ReactElement {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const element = (
    <QueryClientProvider client={client}>
      <BlogGenerationStatus postId="post-1" unsavedChanges={unsavedChanges} />
    </QueryClientProvider>
  );
  render(element);
  return element;
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe("BlogGenerationStatus (AE-0425)", () => {
  it("shows progress with the image slots while running", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(post({ status: "in_progress", image_slots: 10 })),
    );
    renderStatus();
    expect(
      await screen.findByText(/Writing this post in your voice/),
    ).toBeInTheDocument();
  });

  it("explains a partial run", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(
        post({
          status: "partial",
          image_slots: 10,
          image_count: 9,
          errors: [{ code: "image_failed", slot: "sec_3" }],
        }),
      ),
    );
    renderStatus();
    expect(await screen.findByRole("status")).toHaveTextContent(
      "9 of 10 images",
    );
  });

  it("offers to generate only the missing images of a partial run", async () => {
    mockFetch
      .mockResolvedValueOnce(
        jsonResponse(
          post({ status: "partial", image_slots: 10, image_count: 9 }),
        ),
      )
      .mockResolvedValueOnce(
        jsonResponse({ id: "post-1", generation: { attempt: 2 } }, 202),
      )
      .mockResolvedValue(jsonResponse(post({ status: "in_progress" })));
    renderStatus();
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Generate the missing images",
      }),
    );
    await waitFor(() =>
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/blog-posts/post-1/generation/retry",
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("offers a retry on a failed run and retries the same post", async () => {
    mockFetch
      .mockResolvedValueOnce(
        jsonResponse(post({ status: "failed", recoverable: true, errors: [] })),
      )
      .mockResolvedValueOnce(
        jsonResponse({ id: "post-1", generation: { attempt: 2 } }, 202),
      )
      .mockResolvedValue(jsonResponse(post({ status: "in_progress" })));
    renderStatus();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The generation failed. Your draft was kept.",
    );
    fireEvent.click(screen.getByRole("button", { name: "Retry generation" }));
    await waitFor(() =>
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/blog-posts/post-1/generation/retry",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    expect(
      await screen.findByText(/Writing this post in your voice/),
    ).toBeInTheDocument();
  });

  it("explains an interrupted run", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(
        post({
          status: "failed",
          recoverable: true,
          errors: [{ code: "generation_interrupted" }],
        }),
      ),
    );
    renderStatus();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "interrupted by a restart",
    );
  });

  it("reports a retry that could not start", async () => {
    mockFetch
      .mockResolvedValueOnce(
        jsonResponse(post({ status: "failed", recoverable: true })),
      )
      .mockResolvedValue(jsonResponse({ detail: "x" }, 409));
    renderStatus();
    fireEvent.click(
      await screen.findByRole("button", { name: "Retry generation" }),
    );
    expect(
      await screen.findByText(
        "The retry could not start. Try again in a minute.",
      ),
    ).toBeInTheDocument();
  });

  it("hides the retry when the failure is not recoverable", async () => {
    mockFetch.mockResolvedValue(jsonResponse(post({ status: "failed" })));
    renderStatus();
    await screen.findByRole("alert");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("warns that a private carousel's post will 404 and links to its visibility", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(
        post({ status: "complete", warnings: ["carousel_private"] }, "proj-9"),
      ),
    );
    renderStatus();
    const warning = await screen.findByTestId("carousel-private-warning");
    expect(warning).toHaveTextContent("returns 404 on the public site");
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "/dashboard/create/proj-9/publish",
    );
  });

  it("renders nothing for a post that was never generated", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ id: "post-1", ai_generation_metadata: {} }),
    );
    const { container } = render(
      <QueryClientProvider client={new QueryClient()}>
        <BlogGenerationStatus postId="post-1" />
      </QueryClientProvider>,
    );
    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("polls only while the run is in progress", () => {
    expect(generationPollInterval(post({ status: "in_progress" }))).toBe(5000);
    expect(generationPollInterval(post({ status: "complete" }))).toBe(false);
    expect(generationPollInterval(undefined)).toBe(false);
  });

  /** A retry would replace unsaved editor edits, so it stays disabled until they are saved; only the status GET is sent. */
  it.each([
    ["failed", "Retry generation"],
    ["partial", "Generate the missing images"],
  ])(
    "disables the %s retry while the editor has unsaved edits",
    async (status, label) => {
      mockFetch.mockResolvedValue(
        jsonResponse(post({ status, recoverable: true, image_slots: 2 })),
      );
      renderStatus(true);
      const button = await screen.findByRole("button", { name: label });
      expect(button).toBeDisabled();
      expect(screen.getByTestId("retry-save-first")).toHaveTextContent(
        "Save (or discard) your unsaved changes before retrying",
      );
      fireEvent.click(button);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    },
  );

  it("enables the retry again once the edits are saved", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(post({ status: "failed", recoverable: true })),
    );
    renderStatus(false);
    expect(
      await screen.findByRole("button", { name: "Retry generation" }),
    ).not.toBeDisabled();
    expect(screen.queryByTestId("retry-save-first")).not.toBeInTheDocument();
  });
});
