/** Loading the generation queue panel and posting its buttons. */
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { QUEUE_ACTION, QUEUE_API } from "@/constants/workflow";
import en from "@/i18n/locales/en.json";

vi.mock("@/lib/authenticated-fetch", () => ({ authenticatedFetch: vi.fn() }));

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useGenerationQueue } from "./use-generation-queue";

const mockFetch = vi.mocked(authenticatedFetch);
const labels = en.workflow.queue;
const BOARD = {
  active: [],
  dead: [],
  backlog: [],
  average_drive_minutes: 12,
};

function reply(status: number, body: unknown = BOARD): Response {
  return new Response(JSON.stringify(body), { status });
}

describe("useGenerationQueue", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  /** Scenario: The panel shows the running and queued carousels in order */
  it("loads and validates the board", async () => {
    mockFetch.mockResolvedValue(reply(200));
    const { result } = renderHook(() => useGenerationQueue());
    await waitFor(() => expect(result.current.board).toEqual(BOARD));
    expect(mockFetch).toHaveBeenCalledWith(QUEUE_API.BOARD);
    expect(result.current.error).toBeNull();
  });

  /** Scenario: The panel is hidden from editors */
  it("hides the panel on 403 without an error", async () => {
    mockFetch.mockResolvedValue(reply(403, { detail: "forbidden" }));
    const { result } = renderHook(() => useGenerationQueue());
    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    await waitFor(() => expect(result.current.error).toBeNull());
    expect(result.current.board).toBeNull();
    expect(result.current.error).toBeNull();
  });

  /** Scenario: A failed refresh keeps the last panel */
  it("keeps the last board when a refresh fails", async () => {
    mockFetch.mockResolvedValueOnce(reply(200));
    const { result } = renderHook(() => useGenerationQueue());
    await waitFor(() => expect(result.current.board).toEqual(BOARD));
    mockFetch.mockResolvedValueOnce(reply(500, {}));
    act(() => {
      window.dispatchEvent(new Event("focus"));
    });
    await waitFor(() => expect(result.current.error).toBe(labels.loadFailed));
    expect(result.current.board).toEqual(BOARD);
  });

  /** Scenario: A waiting theme offers "Gerar agora" */
  it("posts a button and reloads the board", async () => {
    mockFetch.mockResolvedValue(reply(200));
    const { result } = renderHook(() => useGenerationQueue());
    await waitFor(() => expect(result.current.board).not.toBeNull());
    mockFetch.mockClear();
    mockFetch.mockResolvedValueOnce(reply(200, { outcome: "done" }));
    mockFetch.mockResolvedValueOnce(reply(200));
    await act(async () => {
      await result.current.act(QUEUE_ACTION.GENERATE_NOW, "cand-1");
    });
    expect(mockFetch.mock.calls[0]?.[0]).toBe(QUEUE_API.GENERATE_NOW("cand-1"));
    expect(mockFetch.mock.calls[0]?.[1]).toMatchObject({ method: "POST" });
    expect(mockFetch.mock.calls[1]?.[0]).toBe(QUEUE_API.BOARD);
    expect(result.current.actionError).toBeNull();
    expect(result.current.pending).toBeNull();
  });

  /** Scenario: A button someone else already used reloads without an error */
  it("treats 409 as already resolved", async () => {
    mockFetch.mockResolvedValue(reply(200));
    const { result } = renderHook(() => useGenerationQueue());
    await waitFor(() => expect(result.current.board).not.toBeNull());
    mockFetch.mockResolvedValueOnce(reply(409, { detail: "already_resolved" }));
    await act(async () => {
      await result.current.act(QUEUE_ACTION.RETRY, "gen-1");
    });
    expect(result.current.actionError).toBeNull();
  });

  /** Scenario: A failed button shows an error */
  it("says when the run can no longer take the button", async () => {
    mockFetch.mockResolvedValue(reply(200));
    const { result } = renderHook(() => useGenerationQueue());
    await waitFor(() => expect(result.current.board).not.toBeNull());
    mockFetch.mockResolvedValueOnce(reply(409, { detail: "not_allowed" }));
    await act(async () => {
      await result.current.act(QUEUE_ACTION.CANCEL, "gen-9");
    });
    expect(result.current.actionError).toBe(labels.notAllowed);
  });

  /** Scenario: A failed button shows an error */
  it("reports a failed button", async () => {
    mockFetch.mockResolvedValue(reply(200));
    const { result } = renderHook(() => useGenerationQueue());
    await waitFor(() => expect(result.current.board).not.toBeNull());
    mockFetch.mockResolvedValueOnce(reply(500, {}));
    await act(async () => {
      await result.current.act(QUEUE_ACTION.CANCEL, "gen-2");
    });
    expect(mockFetch).toHaveBeenCalledWith(
      QUEUE_API.CANCEL("gen-2"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(result.current.actionError).toBe(labels.actionFailed);
    mockFetch.mockRejectedValueOnce(new Error("offline"));
    await act(async () => {
      await result.current.act(QUEUE_ACTION.DISCARD, "gen-3");
    });
    expect(result.current.actionError).toBe(labels.actionFailed);
  });
});
