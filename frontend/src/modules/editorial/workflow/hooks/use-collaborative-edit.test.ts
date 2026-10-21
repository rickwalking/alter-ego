/**
 * AE-0446: collaborative lock lifecycle, pinned while the hook was split.
 */
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useCollaborativeEdit } from "./use-collaborative-edit";

const authenticatedFetch = vi.fn();
vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: (...args: unknown[]) => authenticatedFetch(...args),
}));
vi.mock("@/modules/identity", () => ({
  useAuth: () => ({ user: { id: "me" } }),
}));

const MY_LOCK = { content_id: "c1", user_id: "me", content_type: "blog" };
const OTHER_LOCK = {
  content_id: "c1",
  locked_by: "other",
  content_type: "blog",
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

function methods(): string[] {
  return authenticatedFetch.mock.calls.map(
    ([, init]) => (init as RequestInit | undefined)?.method ?? "GET",
  );
}

describe("useCollaborativeEdit (AE-0446)", () => {
  beforeEach(() => authenticatedFetch.mockReset());

  it("takes the lock on mount and releases it on unmount", async () => {
    authenticatedFetch.mockResolvedValue(json(MY_LOCK));
    const { result, unmount } = renderHook(() =>
      useCollaborativeEdit("c1", "blog"),
    );
    await waitFor(() => expect(result.current.activeLock).toEqual(MY_LOCK));
    expect(result.current.isLockedByOther).toBe(false);

    unmount();
    expect(methods()).toEqual(["POST", "DELETE"]);
  });

  it("reads the current holder when the lock is taken", async () => {
    authenticatedFetch
      .mockResolvedValueOnce(json({ detail: "locked" }, 409))
      .mockResolvedValueOnce(json(OTHER_LOCK));
    const { result } = renderHook(() => useCollaborativeEdit("c1", "blog"));
    await waitFor(() => expect(result.current.isLockedByOther).toBe(true));
    expect(methods().slice(0, 2)).toEqual(["POST", "GET"]);
  });

  it("acquireLock reports whether the lock was taken", async () => {
    authenticatedFetch.mockResolvedValueOnce(json(MY_LOCK));
    const { result } = renderHook(() => useCollaborativeEdit("c1", "blog"));
    await waitFor(() => expect(result.current.activeLock).not.toBeNull());

    authenticatedFetch.mockResolvedValueOnce(json({}, 500));
    let acquired = true;
    await act(async () => {
      acquired = await result.current.acquireLock();
    });
    expect(acquired).toBe(false);
  });
});
