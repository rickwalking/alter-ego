import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { useCopyHistory } from "./use-copy-history";

/** Gherkin: tests/features/copy-version-history-ae0506.feature. */

const PROJECT_ID = "proj-1";

function wrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client }, children);
  };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const LIST = {
  project_id: PROJECT_ID,
  versions: [
    {
      version_number: 1,
      field: "caption",
      text: "Legenda gerada",
      author_id: null,
      author_name: null,
      created_at: "2026-10-22T12:00:00Z",
    },
  ],
};

const RESTORED = {
  project_id: PROJECT_ID,
  caption: "Legenda gerada",
  linkedin_post_pt: null,
  linkedin_post_en: null,
  lock_version: 6,
};

function mockFetch(restore: Response): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn((url: string) =>
    Promise.resolve(url.endsWith("/restore") ? restore : json(LIST)),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useCopyHistory (AE-0506)", () => {
  /** Scenario: Restoring a version sends it with the current lock version */
  it("restores with the loaded lock version and refreshes the page", async () => {
    const fetchMock = mockFetch(json(RESTORED));
    const refreshAll = vi.fn(() => Promise.resolve());
    const { result } = renderHook(
      () => useCopyHistory(PROJECT_ID, 5, refreshAll),
      { wrapper: wrapper() },
    );
    await waitFor(() => expect(result.current.versions).toHaveLength(1));
    await act(async () => {
      await result.current.restore?.(1);
    });
    const restoreCall = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith("/copy/versions/1/restore"),
    );
    expect(restoreCall).toBeDefined();
    const init = restoreCall?.[1] as RequestInit;
    expect(new Headers(init.headers).get("If-Match")).toBe("5");
    expect(refreshAll).toHaveBeenCalledTimes(1);
    expect(result.current.status).toEqual({ kind: "idle" });
  });

  /** Scenario: A refused restore explains why */
  it("explains a stale restore and refreshes for the next try", async () => {
    mockFetch(json({ detail: "version_conflict" }, 409));
    const refreshAll = vi.fn(() => Promise.resolve());
    const { result } = renderHook(
      () => useCopyHistory(PROJECT_ID, 5, refreshAll),
      { wrapper: wrapper() },
    );
    await act(async () => {
      await result.current.restore?.(1);
    });
    expect(result.current.status).toEqual({
      kind: "error",
      errorKey: "copy.errors.stale",
    });
    expect(refreshAll).toHaveBeenCalledTimes(1);
  });

  /** Scenario: A refused restore explains why */
  it("keeps the page as is when the caption is already published", async () => {
    mockFetch(json({ detail: "caption_published" }, 409));
    const refreshAll = vi.fn(() => Promise.resolve());
    const { result } = renderHook(
      () => useCopyHistory(PROJECT_ID, 5, refreshAll),
      { wrapper: wrapper() },
    );
    await act(async () => {
      await result.current.restore?.(1);
    });
    expect(result.current.status).toEqual({
      kind: "error",
      errorKey: "copy.errors.captionPublished",
    });
    expect(refreshAll).not.toHaveBeenCalled();
  });

  /** Scenario: Restoring a version sends it with the current lock version */
  it("offers no restore without a loaded lock version", () => {
    mockFetch(json(RESTORED));
    const { result } = renderHook(
      () => useCopyHistory(PROJECT_ID, undefined, vi.fn()),
      { wrapper: wrapper() },
    );
    expect(result.current.restore).toBeUndefined();
  });

  /** Scenario: Restoring a version sends it with the current lock version */
  it("stays restoring until the page refetch is done", async () => {
    mockFetch(json(RESTORED));
    let finishRefresh: () => void = () => undefined;
    const refreshAll = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          finishRefresh = resolve;
        }),
    );
    const { result } = renderHook(
      () => useCopyHistory(PROJECT_ID, 5, refreshAll),
      { wrapper: wrapper() },
    );
    let pending: Promise<void> | undefined;
    act(() => {
      pending = result.current.restore?.(1);
    });
    await waitFor(() => expect(refreshAll).toHaveBeenCalledTimes(1));
    expect(result.current.status).toEqual({
      kind: "restoring",
      versionNumber: 1,
    });
    await act(async () => {
      finishRefresh();
      await pending;
    });
    expect(result.current.status).toEqual({ kind: "idle" });
  });
});
