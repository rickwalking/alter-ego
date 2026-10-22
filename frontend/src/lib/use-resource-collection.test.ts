/**
 * The shared REST collection hook behind usePersonas / useRubrics.
 */
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  ResourceRequestError,
  useCreateAction,
  useResourceCollection,
} from "./use-resource-collection";

const authenticatedFetch = vi.fn<(...args: unknown[]) => Promise<Response>>();
vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: (...args: unknown[]) => authenticatedFetch(...args),
}));

interface Item {
  id: string;
  name: string;
}

const CONFIG = { path: "personas", noun: "persona" };

function ok(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200 });
}

function failed(): Response {
  return new Response("", { status: 500 });
}

function renderCollection() {
  return renderHook(() =>
    useResourceCollection<Item, { name: string }, { name: string }>(CONFIG),
  );
}

describe("useResourceCollection (AE-0446)", () => {
  beforeEach(() => authenticatedFetch.mockReset());

  it("loads the collection once on mount", async () => {
    authenticatedFetch.mockResolvedValue(
      ok({ items: [{ id: "a", name: "A" }] }),
    );
    const { result } = renderCollection();
    await waitFor(() => expect(result.current.items).toHaveLength(1));
    expect(authenticatedFetch).toHaveBeenCalledTimes(1);
    expect(String(authenticatedFetch.mock.calls[0]![0])).toMatch(/\/personas$/);
  });

  it("reports a failed load with the resource name", async () => {
    authenticatedFetch.mockResolvedValue(failed());
    const { result } = renderCollection();
    await waitFor(() =>
      expect(result.current.error).toBe("Failed to fetch personas"),
    );
    expect(result.current.loading).toBe(false);
  });

  it("prepends a created item, replaces an updated one and drops a deleted one", async () => {
    authenticatedFetch.mockResolvedValueOnce(
      ok({ items: [{ id: "a", name: "A" }] }),
    );
    const { result } = renderCollection();
    await waitFor(() => expect(result.current.items).toHaveLength(1));

    authenticatedFetch.mockResolvedValueOnce(ok({ id: "b", name: "B" }));
    await act(() => result.current.create({ name: "B" }));
    expect(result.current.items.map((i) => i.id)).toEqual(["b", "a"]);

    authenticatedFetch.mockResolvedValueOnce(ok({ id: "a", name: "A2" }));
    await act(() => result.current.update("a", { name: "A2" }));
    expect(result.current.items[1]).toEqual({ id: "a", name: "A2" });

    authenticatedFetch.mockResolvedValueOnce(
      new Response(null, { status: 204 }),
    );
    await act(() => result.current.delete("b"));
    expect(result.current.items.map((i) => i.id)).toEqual(["a"]);
  });

  it("throws the resource's failure message on a failed mutation", async () => {
    authenticatedFetch.mockResolvedValueOnce(ok({ items: [] }));
    const { result } = renderCollection();
    await waitFor(() => expect(result.current.loading).toBe(false));
    authenticatedFetch.mockResolvedValueOnce(failed());
    await expect(result.current.create({ name: "x" })).rejects.toThrow(
      "Failed to create persona",
    );
    authenticatedFetch.mockResolvedValueOnce(failed());
    await expect(result.current.delete("x")).rejects.toThrow(
      "Failed to delete persona",
    );
  });

  it("carries the API's string detail on a failed mutation", async () => {
    // Scenario: A failed request keeps the API's own message
    authenticatedFetch.mockResolvedValueOnce(ok({ items: [] }));
    const { result } = renderCollection();
    await waitFor(() => expect(result.current.loading).toBe(false));
    authenticatedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Name taken" }), { status: 400 }),
    );
    const error = await result.current
      .update("a", { name: "x" })
      .catch((err: unknown) => err);
    expect(error).toBeInstanceOf(ResourceRequestError);
    expect(error).toMatchObject({
      message: "Failed to update persona",
      detail: "Name taken",
    });
    authenticatedFetch.mockResolvedValueOnce(failed());
    const plain = await result.current.delete("a").catch((err: unknown) => err);
    expect(plain).toMatchObject({ detail: undefined });
  });

  it("clears an earlier load error when a reload succeeds", async () => {
    // Scenario: A successful reload clears an earlier load error
    authenticatedFetch.mockResolvedValueOnce(failed());
    const { result } = renderCollection();
    await waitFor(() => expect(result.current.error).not.toBeNull());

    authenticatedFetch.mockResolvedValueOnce(
      ok({ items: [{ id: "a", name: "A" }] }),
    );
    await act(() => result.current.refetch());

    expect(result.current.error).toBeNull();
    expect(result.current.items).toHaveLength(1);
  });
});

describe("useCreateAction", () => {
  it("shows a failed create and does not reload", async () => {
    // Scenario: A failed create is shown on the personas and rubrics pages
    const create = vi.fn(() =>
      Promise.reject(new Error("Failed to create persona")),
    );
    const refetch = vi.fn(() => Promise.resolve());
    const { result } = renderHook(() => useCreateAction(create, refetch));

    await act(() => result.current.createAndRefresh({ name: "x" }));

    expect(result.current.createError).toBe("Failed to create persona");
    expect(refetch).not.toHaveBeenCalled();
  });

  it("reloads after a successful create and clears the earlier error", async () => {
    // Scenario: A failed create is shown on the personas and rubrics pages
    const create = vi
      .fn<(data: { name: string }) => Promise<unknown>>()
      .mockRejectedValueOnce(new Error("Failed to create persona"))
      .mockResolvedValueOnce({ id: "b" });
    const refetch = vi.fn(() => Promise.resolve());
    const { result } = renderHook(() => useCreateAction(create, refetch));

    await act(() => result.current.createAndRefresh({ name: "x" }));
    await act(() => result.current.createAndRefresh({ name: "y" }));

    expect(result.current.createError).toBeNull();
    expect(refetch).toHaveBeenCalledTimes(1);
  });
});
