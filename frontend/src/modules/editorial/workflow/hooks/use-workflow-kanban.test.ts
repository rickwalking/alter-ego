import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useWorkflowKanban } from "./use-workflow-kanban";
import type { WorkflowKanban } from "./types";

const translate = (key: string): string => key;
vi.mock("next-intl", () => ({
  useTranslations: () => translate,
}));

const authenticatedFetch = vi.fn<(...args: unknown[]) => Promise<Response>>();
vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: (...args: unknown[]) => authenticatedFetch(...args),
}));

function board(title: string): WorkflowKanban {
  return {
    columns: [
      {
        phase: "research",
        cards: [{ project_id: "p-1", title, status: "in_progress" }],
      },
    ],
  } as unknown as WorkflowKanban;
}

function ok(body: WorkflowKanban): Response {
  return new Response(JSON.stringify(body), { status: 200 });
}

function failed(): Response {
  return new Response("", { status: 500 });
}

function deferred(): {
  promise: Promise<Response>;
  resolve: (response: Response) => void;
} {
  let resolve!: (response: Response) => void;
  const promise = new Promise<Response>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function firstTitle(value: WorkflowKanban | null): unknown {
  return (
    value as unknown as { columns: { cards: { title: string }[] }[] } | null
  )?.columns[0]?.cards[0]?.title;
}

describe("useWorkflowKanban refresh", () => {
  beforeEach(() => authenticatedFetch.mockReset());

  it("keeps the error shown while a retry after a failure is in flight", async () => {
    // Scenario: Repeated failed refreshes keep the error shown
    authenticatedFetch.mockResolvedValueOnce(failed());
    const { result } = renderHook(() => useWorkflowKanban());
    await waitFor(() => expect(result.current.error).toBe("loadBoardFailed"));

    const retry = deferred();
    authenticatedFetch.mockReturnValueOnce(retry.promise);
    let pending: Promise<void> = Promise.resolve();
    act(() => {
      pending = result.current.refetch();
    });
    expect(result.current.error).toBe("loadBoardFailed");

    await act(async () => {
      retry.resolve(failed());
      await pending;
    });
    expect(result.current.error).toBe("loadBoardFailed");

    authenticatedFetch.mockResolvedValueOnce(ok(board("Recovered")));
    await act(() => result.current.refetch());
    expect(result.current.error).toBeNull();
    expect(firstTitle(result.current.board)).toBe("Recovered");
  });

  it("ignores an older refresh that answers after a newer one", async () => {
    // Scenario: An older refresh answering late does not replace newer data
    authenticatedFetch.mockResolvedValueOnce(ok(board("Initial")));
    const { result } = renderHook(() => useWorkflowKanban());
    await waitFor(() =>
      expect(firstTitle(result.current.board)).toBe("Initial"),
    );

    const older = deferred();
    const newer = deferred();
    authenticatedFetch
      .mockReturnValueOnce(older.promise)
      .mockReturnValueOnce(newer.promise);
    let olderDone: Promise<void> = Promise.resolve();
    let newerDone: Promise<void> = Promise.resolve();
    act(() => {
      olderDone = result.current.refetch();
      newerDone = result.current.refetch();
    });

    await act(async () => {
      newer.resolve(ok(board("Newer")));
      await newerDone;
    });
    await act(async () => {
      older.resolve(ok(board("Older")));
      await olderDone;
    });

    expect(firstTitle(result.current.board)).toBe("Newer");
  });
});
