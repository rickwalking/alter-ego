/** Per-document state of the Knowledge Base scope changes. */
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const changeScope = vi.hoisted(() => vi.fn());

vi.mock("./use-documents", () => ({
  useChangeDocumentScope: () => ({ mutateAsync: changeScope }),
}));

import { useDocumentScopeChange } from "./use-document-scope-change";

interface Deferred {
  resolve: () => void;
  reject: () => void;
  settled: Promise<unknown>;
}

function deferredCalls(): Map<string, Deferred> {
  const calls = new Map<string, Deferred>();
  changeScope.mockImplementation(({ id }: { id: string }) => {
    let resolve = (): void => undefined;
    let reject = (): void => undefined;
    const request = new Promise<void>((ok, fail) => {
      resolve = ok;
      reject = () => fail(new Error("boom"));
    });
    calls.set(id, { resolve, reject, settled: request.catch(() => undefined) });
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

describe("useDocumentScopeChange", () => {
  beforeEach(() => {
    changeScope.mockReset();
  });

  /** Scenario: Switching two documents keeps each one busy until its own change ends */
  it("keeps the first document changing while a second change starts and ends", async () => {
    const calls = deferredCalls();
    const { result } = renderHook(() => useDocumentScopeChange());

    act(() => result.current.changeScope("a", "public"));
    act(() => result.current.changeScope("b", "personal"));
    expect([...result.current.changingScopeIds]).toEqual(["a", "b"]);
    expect(changeScope).toHaveBeenNthCalledWith(1, {
      id: "a",
      scope: "public",
    });
    expect(changeScope).toHaveBeenNthCalledWith(2, {
      id: "b",
      scope: "personal",
    });

    await settle(calls, "b", "resolve");
    expect([...result.current.changingScopeIds]).toEqual(["a"]);

    await settle(calls, "a", "resolve");
    expect(result.current.changingScopeIds.size).toBe(0);
    expect(result.current.scopeChangeFailedIds.size).toBe(0);
  });

  /** Scenario: A failed scope change says so on its document only */
  it("marks only the document whose change failed, and clears it on the next try", async () => {
    const calls = deferredCalls();
    const { result } = renderHook(() => useDocumentScopeChange());

    act(() => result.current.changeScope("a", "public"));
    act(() => result.current.changeScope("b", "public"));
    await settle(calls, "a", "reject");
    await waitFor(() =>
      expect([...result.current.scopeChangeFailedIds]).toEqual(["a"]),
    );
    expect([...result.current.changingScopeIds]).toEqual(["b"]);

    act(() => result.current.changeScope("a", "public"));
    expect(result.current.scopeChangeFailedIds.size).toBe(0);
    expect([...result.current.changingScopeIds]).toEqual(["b", "a"]);
  });
});
