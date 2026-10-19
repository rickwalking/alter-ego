import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { blogPost, jsonResponse } from "../editor.test-utils";
import { useBlogPostEditor } from "./use-blog-post-editor";
import { useBlogReviewActions } from "./use-blog-review-actions";

// Scenarios: tests/features/blog_editor_ae0424.feature (publish, review +
// scheduled publish, self-review on/off)

vi.mock("@/lib/authenticated-fetch", () => ({ authenticatedFetch: vi.fn() }));

import { authenticatedFetch } from "@/lib/authenticated-fetch";

const mockFetch = vi.mocked(authenticatedFetch);
type Route = (url: string, init?: RequestInit) => Response | undefined;
let route: Route;

function wrapper({ children }: { children: ReactNode }): ReactNode {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return createElement(QueryClientProvider, { client }, children);
}

function respond(selfReview: boolean, extra: Route): void {
  route = (url, init) => {
    const answer = extra(url, init);
    if (answer) {
      return answer;
    }
    if (url === "/api/blog-editor/settings") {
      return jsonResponse({ allow_self_review: selfReview });
    }
    return jsonResponse(blogPost());
  };
}

async function renderReview(
  selfReview = false,
  extra: Route = () => undefined,
) {
  respond(selfReview, extra);
  const hook = renderHook(
    () => {
      const editor = useBlogPostEditor("p-1");
      return { editor, review: useBlogReviewActions(editor) };
    },
    { wrapper },
  );
  await waitFor(() => expect(hook.result.current.editor.draft).not.toBeNull());
  await waitFor(() =>
    expect(hook.result.current.review.allowSelfReview).toBe(selfReview),
  );
  return hook;
}

function urls(): string[] {
  return mockFetch.mock.calls.map(([url]) => String(url));
}

beforeEach(() => {
  mockFetch.mockReset();
  mockFetch.mockImplementation((url, init) =>
    Promise.resolve(route(String(url), init) as Response),
  );
});

describe("review controls", () => {
  // Scenario: Submit for review moves the post to under review
  it("submits to a reviewer and takes the new status", async () => {
    const { result } = await renderReview(false, (url) =>
      url.includes("submit-review")
        ? jsonResponse(blogPost({ status: "under_review" }))
        : undefined,
    );
    await act(async () => {
      await result.current.review.submitForReview("rev-1");
    });
    expect(urls()).toContain(
      "/api/blog-posts/p-1/submit-review?reviewer_id=rev-1",
    );
    expect(result.current.editor.post?.status).toBe("under_review");
  });

  // Scenario: Approve / Reject returns the post to draft with a reason
  it("approves and rejects", async () => {
    const { result } = await renderReview();
    await act(async () => {
      await result.current.review.approve();
      await result.current.review.reject("Falta fonte");
    });
    expect(urls()).toContain("/api/blog-posts/p-1/approve");
    expect(urls()).toContain("/api/blog-posts/p-1/reject?reason=Falta+fonte");
  });

  // Scenario: Publishing a draft is blocked by the status guard
  it("shows the status-guard error and reloads the post", async () => {
    const { result } = await renderReview(false, (url) =>
      url.endsWith("/publish")
        ? jsonResponse({ detail: "invalid_status" }, 400)
        : undefined,
    );
    await act(async () => {
      await result.current.review.publish();
    });
    expect(result.current.editor.error).toEqual({
      kind: "status_guard",
      detail: "invalid_status",
    });
    expect(result.current.editor.post?.status).toBe("draft");
    expect(result.current.review.pending).toBe(false);
  });

  // Scenario: Publish now auto-approves when self-review is enabled
  it("runs submit -> approve -> publish for Publish now", async () => {
    const { result } = await renderReview(true, (url) =>
      url.endsWith("/publish")
        ? jsonResponse(blogPost({ status: "published" }))
        : undefined,
    );
    await act(async () => {
      await result.current.review.publishNow();
    });
    const flow = urls().filter((url) =>
      /submit-review|approve|publish$/.test(url),
    );
    expect(flow).toEqual([
      "/api/blog-posts/p-1/submit-review",
      "/api/blog-posts/p-1/approve",
      "/api/blog-posts/p-1/publish",
    ]);
    expect(result.current.editor.post?.status).toBe("published");
  });

  // Scenario: Scheduling / Cancelling a schedule / Unpublish
  it("schedules, cancels and unpublishes with If-Match", async () => {
    const { result } = await renderReview();
    await act(async () => {
      await result.current.review.schedule("2026-10-25T10:00:00.000Z");
      await result.current.review.cancelSchedule();
      await result.current.review.unpublish();
    });
    const calls = mockFetch.mock.calls.filter(([url]) =>
      /schedule|unpublish/.test(String(url)),
    );
    expect(calls.map(([, init]) => init?.method)).toEqual([
      "POST",
      "DELETE",
      "POST",
    ]);
    expect(
      calls.every(
        ([, init]) => new Headers(init?.headers).get("If-Match") === "2",
      ),
    ).toBe(true);
  });

  it("does nothing while there are unsaved edits", async () => {
    const { result } = await renderReview();
    act(() =>
      result.current.editor.updateDraft((d) => ({ ...d, title: "Novo" })),
    );
    const before = mockFetch.mock.calls.length;
    await act(async () => {
      await result.current.review.approve();
    });
    expect(mockFetch.mock.calls.length).toBe(before);
  });

  it("maps an unexpected failure to failed", async () => {
    const { result } = await renderReview(false, (url) => {
      if (url.endsWith("/approve")) {
        throw new Error("offline");
      }
      return undefined;
    });
    await act(async () => {
      await result.current.review.approve();
    });
    expect(result.current.editor.error?.kind).toBe("failed");
  });
});
