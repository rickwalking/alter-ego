/** Forbidden termination, late-response and recoverable queue polling races. */
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  QUEUE_API,
  WORKFLOW_BOARD_POLL_INTERVAL_MS,
} from "@/constants/workflow";
import en from "@/i18n/locales/en.json";
import type { QueueBoard } from "@/schemas/generation-queue";

vi.mock("@/lib/authenticated-fetch", () => ({ authenticatedFetch: vi.fn() }));

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { useGenerationQueue } from "./use-generation-queue";

const mockFetch = vi.mocked(authenticatedFetch);
const BOARD: QueueBoard = {
  active: [],
  dead: [],
  backlog: [],
  average_drive_minutes: 12,
};

function board(minutes: number): QueueBoard {
  return { ...BOARD, average_drive_minutes: minutes };
}

function reply(status: number, body: unknown = BOARD): Response {
  return new Response(JSON.stringify(body), { status });
}

function deferred(): {
  promise: Promise<Response>;
  resolve: (response: Response) => void;
} {
  let resolve!: (response: Response) => void;
  const promise = new Promise<Response>((resolvePromise): void => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

async function flushRequests(): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
}

function focusBoard(): void {
  act(() => {
    window.dispatchEvent(new Event("focus"));
  });
}

describe("useGenerationQueue polling recovery", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  /** Scenario: Forbidden polling terminates permanently */
  it("stops interval and focus polling after an initial 403", async () => {
    mockFetch.mockResolvedValue(reply(403, { detail: "forbidden" }));
    const { result } = renderHook(() => useGenerationQueue());
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));
    await flushRequests();
    expect(result.current.board).toBeNull();
    expect(result.current.error).toBeNull();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(WORKFLOW_BOARD_POLL_INTERVAL_MS);
      window.dispatchEvent(new Event("focus"));
    });
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledWith(QUEUE_API.BOARD);
  });

  /** Scenario: Forbidden polling terminates permanently */
  it("clears a loaded board and stops after a later 403", async () => {
    mockFetch.mockResolvedValueOnce(reply(200));
    const { result } = renderHook(() => useGenerationQueue());
    await waitFor(() => expect(result.current.board).toEqual(BOARD));
    mockFetch.mockResolvedValueOnce(reply(403, { detail: "forbidden" }));
    focusBoard();
    await waitFor(() => expect(result.current.board).toBeNull());
    expect(result.current.error).toBeNull();
    expect(mockFetch).toHaveBeenCalledTimes(2);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(WORKFLOW_BOARD_POLL_INTERVAL_MS);
      window.dispatchEvent(new Event("focus"));
    });
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  /** Scenario: Forbidden polling terminates permanently */
  it("does not let an older late 200 resurrect a forbidden board", async () => {
    const older = deferred();
    const forbidden = deferred();
    mockFetch
      .mockReturnValueOnce(older.promise)
      .mockReturnValueOnce(forbidden.promise);
    const { result } = renderHook(() => useGenerationQueue());
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));
    focusBoard();
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));

    await act(async () => {
      forbidden.resolve(reply(403, { detail: "forbidden" }));
      await vi.advanceTimersByTimeAsync(0);
    });
    await act(async () => {
      older.resolve(reply(200, board(99)));
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.board).toBeNull();
    expect(result.current.error).toBeNull();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(WORKFLOW_BOARD_POLL_INTERVAL_MS);
      window.dispatchEvent(new Event("focus"));
    });
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(result.current.board).toBeNull();
  });

  /** Scenario: A failed refresh recovers on a later poll */
  it("keeps the last board after 500 and recovers on later polls", async () => {
    mockFetch.mockResolvedValueOnce(reply(200, board(12)));
    const { result } = renderHook(() => useGenerationQueue());
    await waitFor(() => expect(result.current.board).toEqual(board(12)));

    mockFetch.mockResolvedValueOnce(reply(500, {}));
    focusBoard();
    await waitFor(() =>
      expect(result.current.error).toBe(en.workflow.queue.loadFailed),
    );
    expect(result.current.board).toEqual(board(12));

    mockFetch.mockResolvedValueOnce(reply(200, board(30)));
    focusBoard();
    await waitFor(() => expect(result.current.board).toEqual(board(30)));
    expect(result.current.error).toBeNull();

    mockFetch.mockResolvedValueOnce(reply(200, board(40)));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(WORKFLOW_BOARD_POLL_INTERVAL_MS);
    });
    await waitFor(() => expect(result.current.board).toEqual(board(40)));
    expect(mockFetch).toHaveBeenCalledTimes(4);
  });
});
