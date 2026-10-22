import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const reprocess = vi.hoisted(() => vi.fn());

vi.mock("./use-documents", () => ({
  useReprocessDocument: () => ({ mutateAsync: reprocess }),
}));

import { useDocumentRetries } from "./use-document-retries";

interface Deferred {
  resolve: () => void;
  reject: () => void;
  settled: Promise<unknown>;
}

function deferredCalls(): Map<string, Deferred> {
  const calls = new Map<string, Deferred>();
  reprocess.mockImplementation((id: string) => {
    let resolve = (): void => undefined;
    let reject = (): void => undefined;
    const request = new Promise<void>((ok, fail) => {
      resolve = ok;
      reject = () => fail(new Error("boom"));
    });
    calls.set(id, {
      resolve,
      reject,
      settled: request.catch(() => undefined),
    });
    return request;
  });
  return calls;
}

async function settle(
  calls: Map<string, Deferred>,
  id: string,
  outcome: "resolve" | "reject",
): Promise<void> {
  const call = calls.get(id);
  if (!call) throw new Error(`no request for ${id}`);
  await act(async () => {
    call[outcome]();
    await call.settled;
  });
}

describe("useDocumentRetries", () => {
  beforeEach(() => {
    reprocess.mockReset();
  });

  // Scenario: Retrying two documents keeps each one busy until its own retry ends
  it("keeps the first document retrying while a second retry starts and ends", async () => {
    const calls = deferredCalls();
    const { result } = renderHook(() => useDocumentRetries());

    act(() => result.current.retry("a"));
    act(() => result.current.retry("b"));
    expect([...result.current.retryingIds]).toEqual(["a", "b"]);

    await settle(calls, "b", "resolve");
    expect([...result.current.retryingIds]).toEqual(["a"]);

    await settle(calls, "a", "resolve");
    expect(result.current.retryingIds.size).toBe(0);
    expect(result.current.retryFailedIds.size).toBe(0);
  });

  // Scenario: A failed retry says so on its document
  it("marks only the document whose retry failed, and clears it on the next retry", async () => {
    const calls = deferredCalls();
    const { result } = renderHook(() => useDocumentRetries());

    act(() => result.current.retry("a"));
    act(() => result.current.retry("b"));
    await settle(calls, "a", "reject");
    await waitFor(() =>
      expect([...result.current.retryFailedIds]).toEqual(["a"]),
    );
    expect([...result.current.retryingIds]).toEqual(["b"]);

    act(() => result.current.retry("a"));
    expect(result.current.retryFailedIds.size).toBe(0);
    expect(result.current.retryingIds.has("a")).toBe(true);
  });
});
