import { describe, expect, it, vi } from "vitest";
import { createRetryWorkflowHandler } from "./create-retry-handler";

/**
 * Retry restarts the workflow; a failure re-enables the button and keeps the
 * error card by resetting `retrying` to false without navigating.
 */
describe("createRetryWorkflowHandler", () => {
  const project = { topic: "AI", audience: "Devs", niche: "Security" };
  const sources = [{ title: "Doc", content: "text", source_type: "document" }];

  /**
   * Given a failed workflow
   * When the user retries and start() rejects
   * Then retrying is set true then back to false (button re-enables)
   * And navigation does NOT happen (the error card stays)
   */
  // Scenario: Retry FAILURE resets retrying and keeps the error card (F-3)
  it("resets retrying to false and does not navigate when start rejects", async () => {
    const setRetrying = vi.fn();
    const start = vi.fn(() => {
      return Promise.reject(new Error("network down"));
    });
    const navigateOnSuccess = vi.fn();

    const handler = createRetryWorkflowHandler({
      project,
      retrying: false,
      setRetrying,
      start,
      sources,
      navigateOnSuccess,
    });

    await handler();

    expect(start).toHaveBeenCalledTimes(1);
    expect(setRetrying).toHaveBeenNthCalledWith(1, true);
    expect(setRetrying).toHaveBeenNthCalledWith(2, false);
    expect(setRetrying).toHaveBeenCalledTimes(2);
    expect(navigateOnSuccess).not.toHaveBeenCalled();
  });

  // Scenario: Retry SUCCESS resets retrying and navigates
  it("resets retrying and navigates when start resolves", async () => {
    const setRetrying = vi.fn();
    const start = vi.fn(() => Promise.resolve(null));
    const navigateOnSuccess = vi.fn();

    const handler = createRetryWorkflowHandler({
      project,
      retrying: false,
      setRetrying,
      start,
      sources,
      navigateOnSuccess,
    });

    await handler();

    expect(start).toHaveBeenCalledWith({
      topic: "AI",
      audience: "Devs",
      brief: "Security",
      sources,
    });
    expect(setRetrying).toHaveBeenNthCalledWith(1, true);
    expect(setRetrying).toHaveBeenNthCalledWith(2, false);
    expect(navigateOnSuccess).toHaveBeenCalledTimes(1);
  });

  // Scenario: Guard - no project or already retrying short-circuits.
  it("does nothing when project is missing", async () => {
    const setRetrying = vi.fn();
    const start = vi.fn(() => Promise.resolve(null));
    const handler = createRetryWorkflowHandler({
      project: null,
      retrying: false,
      setRetrying,
      start,
      sources,
      navigateOnSuccess: vi.fn(),
    });

    await handler();

    expect(start).not.toHaveBeenCalled();
    expect(setRetrying).not.toHaveBeenCalled();
  });

  it("does nothing when a retry is already in flight", async () => {
    const setRetrying = vi.fn();
    const start = vi.fn(() => Promise.resolve(null));
    const handler = createRetryWorkflowHandler({
      project,
      retrying: true,
      setRetrying,
      start,
      sources,
      navigateOnSuccess: vi.fn(),
    });

    await handler();

    expect(start).not.toHaveBeenCalled();
    expect(setRetrying).not.toHaveBeenCalled();
  });
});
