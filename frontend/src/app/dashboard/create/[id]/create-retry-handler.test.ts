import { describe, expect, it, vi } from "vitest";
import { createRetryWorkflowHandler } from "./create-retry-handler";

// Feature: Workflow Error Feedback & Retry (AE-0009)
//   Retry restarts the workflow; failure must re-enable the button and keep the
//   error card by resetting `retrying` to false without navigating.
describe("createRetryWorkflowHandler", () => {
  const project = { topic: "AI", audience: "Devs", niche: "Security" };
  const sources = [{ title: "Doc", content: "text", source_type: "document" }];

  // Scenario: Retry FAILURE resets retrying and keeps the error card (F-3)
  //   Given a failed workflow
  //   When the user retries and start() rejects
  //   Then retrying is set true then back to false (button re-enables)
  //   And navigation does NOT happen (the error card stays)
  it("resets retrying to false and does not navigate when start rejects", async () => {
    const setRetrying = vi.fn();
    const start = vi.fn(async () => {
      throw new Error("network down");
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
    // Button disabled while in-flight, then re-enabled on failure.
    expect(setRetrying).toHaveBeenNthCalledWith(1, true);
    expect(setRetrying).toHaveBeenNthCalledWith(2, false);
    expect(setRetrying).toHaveBeenCalledTimes(2);
    // Error card stays: no navigation on failure.
    expect(navigateOnSuccess).not.toHaveBeenCalled();
  });

  // Scenario: Retry SUCCESS resets retrying and navigates
  it("resets retrying and navigates when start resolves", async () => {
    const setRetrying = vi.fn();
    const start = vi.fn(async () => null);
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
    const start = vi.fn(async () => null);
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
    const start = vi.fn(async () => null);
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
