import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { blogPost, v2Document } from "../editor.test-utils";
import { blogPostKeys } from "../blog-post-requests";
import { useBlogPostEditor } from "./use-blog-post-editor";

// Scenarios: tests/features/blog_generate_ae0425.feature
// ("Generation progress is polled and shown") — review fix 2: while the run
// writes the post, each newer server version replaces the read-only session.

vi.mock("@/lib/authenticated-fetch", () => ({ authenticatedFetch: vi.fn() }));

import { authenticatedFetch } from "@/lib/authenticated-fetch";

const mockFetch = vi.mocked(authenticatedFetch);

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

const EMPTY = { ...v2Document(), sections: [] };

beforeEach(() => {
  mockFetch.mockReset();
});

describe("useBlogPostEditor while generating (AE-0425)", () => {
  it("adopts the generated sections when the run writes them", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = ({ children }: { children: ReactNode }): ReactNode =>
      createElement(QueryClientProvider, { client }, children);
    const running = blogPost({
      content: EMPTY,
      lock_version: 1,
      ai_generation_metadata: { generation: { status: "in_progress" } },
    });
    mockFetch.mockResolvedValueOnce(jsonResponse(running));
    const hook = renderHook(() => useBlogPostEditor("p-1"), { wrapper });
    await waitFor(() => expect(hook.result.current.draft).not.toBeNull());
    expect(hook.result.current.draft?.document.sections).toHaveLength(0);

    const done = blogPost({
      lock_version: 3,
      ai_generation_metadata: { generation: { status: "complete" } },
    });
    client.setQueryData(blogPostKeys.detail("p-1"), done);
    await waitFor(() =>
      expect(hook.result.current.draft?.document.sections).toHaveLength(3),
    );
    expect(hook.result.current.post?.lock_version).toBe(3);
  });

  it("keeps the owner's session once the post is no longer generating", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = ({ children }: { children: ReactNode }): ReactNode =>
      createElement(QueryClientProvider, { client }, children);
    mockFetch.mockResolvedValueOnce(
      jsonResponse(blogPost({ lock_version: 3 })),
    );
    const hook = renderHook(() => useBlogPostEditor("p-1"), { wrapper });
    await waitFor(() => expect(hook.result.current.draft).not.toBeNull());
    client.setQueryData(
      blogPostKeys.detail("p-1"),
      blogPost({ lock_version: 4, content: EMPTY }),
    );
    await waitFor(() => expect(hook.result.current.post).not.toBeNull());
    expect(hook.result.current.draft?.document.sections).toHaveLength(3);
  });
});
