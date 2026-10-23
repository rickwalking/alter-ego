import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { useCopySave } from "./use-copy-save";

const PROJECT_ID = "proj-1";

function wrapper() {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client }, children);
  };
}

function okResponse(lockVersion: number): Response {
  return new Response(
    JSON.stringify({
      project_id: PROJECT_ID,
      caption: "Saved",
      linkedin_post_pt: null,
      linkedin_post_en: null,
      lock_version: lockVersion,
    }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
}

function conflict(detail: string): Response {
  return new Response(JSON.stringify({ detail }), {
    status: 409,
    headers: { "Content-Type": "application/json" },
  });
}

function sentIfMatch(
  fetchMock: ReturnType<typeof vi.fn>,
  call: number,
): string {
  const init = fetchMock.mock.calls[call]![1] as RequestInit;
  return (init.headers as Record<string, string>)["If-Match"]!;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useCopySave (AE-0492)", () => {
  /** Scenario: Saving the edited caption sends it with the loaded lock version */
  it("sends the texts to the copy route with the loaded lock version", async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse(4));
    vi.stubGlobal("fetch", fetchMock);
    const refreshAll = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(
      () => useCopySave(PROJECT_ID, 3, refreshAll),
      { wrapper: wrapper() },
    );
    await act(async () => {
      await result.current!({ caption: "Saved" });
    });
    const [url, init] = fetchMock.mock.calls[0]! as [string, RequestInit];
    expect(url).toBe(`/api/carousels/${PROJECT_ID}/copy`);
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(JSON.stringify({ caption: "Saved" }));
    expect(sentIfMatch(fetchMock, 0)).toBe("3");
    expect(refreshAll).toHaveBeenCalledTimes(1);
  });

  /** Scenario: The next save uses the lock version returned by the last save */
  it("sends the lock version the last save returned before the refresh lands", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(okResponse(4))
      .mockResolvedValueOnce(okResponse(5));
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(
      () => useCopySave(PROJECT_ID, 3, vi.fn().mockResolvedValue(undefined)),
      { wrapper: wrapper() },
    );
    await act(async () => {
      await result.current!({ caption: "One" });
    });
    await act(async () => {
      await result.current!({ caption: "Two" });
    });
    expect(sentIfMatch(fetchMock, 1)).toBe("4");
  });

  /** Scenario: A refused save explains why */
  it("rejects with the API error so the panel can explain it", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(conflict("caption_published")),
    );
    const refreshAll = vi.fn();
    const { result } = renderHook(
      () => useCopySave(PROJECT_ID, 3, refreshAll),
      { wrapper: wrapper() },
    );
    await expect(result.current!({ caption: "x" })).rejects.toMatchObject({
      status: 409,
      detail: "caption_published",
    });
    expect(refreshAll).not.toHaveBeenCalled();
  });

  /** Scenario: A save from a stale page refetches the current lock version */
  it("refetches the page on a version conflict so the next save uses the new lock version", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(conflict("version_conflict"))
      .mockResolvedValueOnce(okResponse(6));
    vi.stubGlobal("fetch", fetchMock);
    let loadedLockVersion = 3;
    const refreshAll = vi.fn(() => {
      loadedLockVersion = 5;
      return Promise.resolve();
    });
    const { result, rerender } = renderHook(
      () => useCopySave(PROJECT_ID, loadedLockVersion, refreshAll),
      { wrapper: wrapper() },
    );
    await act(async () => {
      await expect(result.current!({ caption: "Draft" })).rejects.toMatchObject(
        { status: 409, detail: "version_conflict" },
      );
    });
    expect(refreshAll).toHaveBeenCalledTimes(1);
    rerender();
    await act(async () => {
      await result.current!({ caption: "Draft" });
    });
    expect(sentIfMatch(fetchMock, 0)).toBe("3");
    expect(sentIfMatch(fetchMock, 1)).toBe("5");
  });

  /** Scenario: Saving the edited caption sends it with the loaded lock version */
  it("offers no save before the workflow lock version is loaded", () => {
    const { result } = renderHook(
      () => useCopySave(PROJECT_ID, undefined, vi.fn()),
      { wrapper: wrapper() },
    );
    expect(result.current).toBeUndefined();
  });

  /** Scenario: A save refreshes the workflow state and the project */
  it("resolves only once the page refetch is done", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(okResponse(4)));
    let finishRefresh: () => void = () => undefined;
    const refreshAll = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          finishRefresh = resolve;
        }),
    );
    const { result } = renderHook(
      () => useCopySave(PROJECT_ID, 3, refreshAll),
      { wrapper: wrapper() },
    );
    let done = false;
    let pending: Promise<void> = Promise.resolve();
    act(() => {
      pending = result.current!({ caption: "Saved" }).then(() => {
        done = true;
      });
    });
    await waitFor(() => expect(refreshAll).toHaveBeenCalledTimes(1));
    expect(done).toBe(false);
    await act(async () => {
      finishRefresh();
      await pending;
    });
    expect(done).toBe(true);
  });

  /** Scenario: A save refreshes the workflow state and the project */
  it("still counts the save as done when the refetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(okResponse(4)));
    const refreshAll = vi.fn().mockRejectedValue(new Error("offline"));
    const { result } = renderHook(
      () => useCopySave(PROJECT_ID, 3, refreshAll),
      { wrapper: wrapper() },
    );
    await act(async () => {
      await expect(
        result.current!({ caption: "Saved" }),
      ).resolves.toBeUndefined();
    });
  });
});
