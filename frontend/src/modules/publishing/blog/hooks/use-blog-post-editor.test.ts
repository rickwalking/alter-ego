import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useBlogPostEditor } from "./use-blog-post-editor";

// Scenarios: see tests/features/blog-dashboard-ae0411.feature (Editor)

vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";

const mockFetch = vi.mocked(authenticatedFetch);

const CAROUSEL_POST = {
  id: "p-9",
  title: "Carousel title",
  slug: "carousel-x",
  status: "published",
  excerpt: null,
  content: { markdown: "# Long body", translations: { en: "# EN" } },
  lock_version: 4,
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function wrapper({ children }: { children: ReactNode }): ReactNode {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return createElement(QueryClientProvider, { client }, children);
}

async function renderLoaded() {
  mockFetch.mockResolvedValueOnce(jsonResponse(CAROUSEL_POST));
  const hook = renderHook(() => useBlogPostEditor("p-9"), { wrapper });
  await waitFor(() => expect(hook.result.current.post).toBeDefined());
  await waitFor(() => expect(hook.result.current.bodyText).toBe("# Long body"));
  return hook;
}

function lastPutBody(): Record<string, unknown> {
  const [, init] = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
  return JSON.parse(String(init?.body)) as Record<string, unknown>;
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe("useBlogPostEditor load (AE-0411)", () => {
  // Scenario: The editor loads the full post through the detail endpoint
  it("fetches the detail endpoint and fills the fields from content.markdown", async () => {
    const { result } = await renderLoaded();
    expect(String(mockFetch.mock.calls[0][0])).toBe("/api/blog-posts/p-9");
    expect(result.current.title).toBe("Carousel title");
    expect(result.current.excerpt).toBe("");
  });

  it("reports a missing post as undefined without a load error", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "nf" }, 404));
    const { result } = renderHook(() => useBlogPostEditor("p-0"), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.post).toBeUndefined();
    expect(result.current.loadFailed).toBe(false);
  });

  it("flags a failed load", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({}, 500));
    const { result } = renderHook(() => useBlogPostEditor("p-1"), { wrapper });
    await waitFor(() => expect(result.current.loadFailed).toBe(true));
  });
});

describe("useBlogPostEditor save (AE-0411)", () => {
  // Scenario: A title-only save does not send content
  it("sends only the title with the loaded If-Match version", async () => {
    const { result } = await renderLoaded();
    act(() => result.current.setTitle("New title"));
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ ...CAROUSEL_POST, title: "New title", lock_version: 5 }),
    );
    let saved = false;
    await act(async () => {
      saved = await result.current.handleSave();
    });
    expect(saved).toBe(true);
    const [url, init] = mockFetch.mock.calls[1];
    expect(String(url)).toBe("/api/blog-posts/p-9");
    expect(init?.method).toBe("PUT");
    expect((init?.headers as Record<string, string>)["If-Match"]).toBe("4");
    expect(lastPutBody()).toEqual({ title: "New title" });
  });

  // Scenario: A body edit keeps every other content key
  it("keeps translations when the markdown body is edited", async () => {
    const { result } = await renderLoaded();
    act(() => result.current.setBodyText("# Edited"));
    mockFetch.mockResolvedValueOnce(jsonResponse(CAROUSEL_POST));
    await act(async () => {
      await result.current.handleSave();
    });
    expect(lastPutBody()).toEqual({
      content: { markdown: "# Edited", translations: { en: "# EN" } },
    });
  });

  it("sends nothing when nothing changed", async () => {
    const { result } = await renderLoaded();
    let saved = false;
    await act(async () => {
      saved = await result.current.handleSave();
    });
    expect(saved).toBe(true);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  // Scenario: An empty title cannot be saved
  it("blocks an empty title client-side without a request", async () => {
    const { result } = await renderLoaded();
    act(() => result.current.setTitle(""));
    expect(result.current.validation.title).toBe("titleRequired");
    let saved = true;
    await act(async () => {
      saved = await result.current.handleSave();
    });
    expect(saved).toBe(false);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  // Scenario: A server rejection is shown and the user stays on the editor
  it.each([
    [422, "validation_failed"],
    [409, "version_conflict"],
    [500, "failed"],
  ])("maps a %i save to %s and resolves false", async (status, code) => {
    const { result } = await renderLoaded();
    act(() => result.current.setTitle("Changed"));
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "x" }, status));
    let saved = true;
    await act(async () => {
      saved = await result.current.handleSave();
    });
    expect(saved).toBe(false);
    expect(result.current.saveError).toBe(code);
    expect(result.current.saving).toBe(false);
  });

  it("maps a network failure to a generic error instead of rejecting", async () => {
    const { result } = await renderLoaded();
    act(() => result.current.setTitle("Changed"));
    mockFetch.mockRejectedValueOnce(new TypeError("network"));
    let saved = true;
    await act(async () => {
      saved = await result.current.handleSave();
    });
    expect(saved).toBe(false);
    expect(result.current.saveError).toBe("failed");
  });
});

describe("useBlogPostEditor restore (AE-0411)", () => {
  // Scenario: Restoring a version reads either content shape
  it("restores a markdown snapshot into the body", async () => {
    const { result } = await renderLoaded();
    act(() =>
      result.current.handleRestore({
        version_number: 2,
        title: "Old title",
        snapshot: { markdown: "# Old body" },
      }),
    );
    expect(result.current.title).toBe("Old title");
    expect(result.current.excerpt).toBe("");
    expect(result.current.bodyText).toBe("# Old body");
  });
});
