import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const authenticatedFetch = vi.fn<(...args: unknown[]) => Promise<unknown>>();
vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: (...args: unknown[]): Promise<unknown> =>
    authenticatedFetch(...args),
}));

import { useWorkflowPostAction } from "./use-workflow-post-action";

const MESSAGES = { success: "done", failed: "nope" };

describe("useWorkflowPostAction", () => {
  beforeEach(() => {
    authenticatedFetch.mockReset();
  });

  it("posts JSON, reports success and calls onDone", async () => {
    // Scenario: successful post
    authenticatedFetch.mockResolvedValue({ ok: true });
    const onDone = vi.fn();
    const { result } = renderHook(() =>
      useWorkflowPostAction(MESSAGES, onDone),
    );
    await act(() => result.current.post("/x", { a: 1 }));
    expect(authenticatedFetch).toHaveBeenCalledWith("/x", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ a: 1 }),
    });
    expect(result.current.message).toBe("done");
    expect(result.current.submitting).toBe(false);
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it("reports the failed message on a non-ok response", async () => {
    // Scenario: server rejects
    authenticatedFetch.mockResolvedValue({ ok: false });
    const onDone = vi.fn();
    const { result } = renderHook(() =>
      useWorkflowPostAction(MESSAGES, onDone),
    );
    await act(() => result.current.post("/x", {}));
    expect(result.current.message).toBe("nope");
    expect(onDone).not.toHaveBeenCalled();
  });

  it("surfaces a thrown error message", async () => {
    // Scenario: network error
    authenticatedFetch.mockImplementation(() =>
      Promise.reject(new Error("offline")),
    );
    const { result } = renderHook(() => useWorkflowPostAction(MESSAGES));
    await act(() => result.current.post("/x", {}));
    expect(result.current.message).toBe("offline");
  });
});
