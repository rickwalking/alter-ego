/** AE-0446: SSE chat event dispatch helpers. */
import { describe, expect, it, vi } from "vitest";
import { dispatchSseEvent, sseContentText } from "./sse-event-data";

describe("dispatchSseEvent (AE-0446)", () => {
  it("calls the handler for the event type with its data", () => {
    const token = vi.fn();
    dispatchSseEvent({ token })({ event: "token", data: { content: "a" } });
    expect(token).toHaveBeenCalledWith({ content: "a" });
  });

  it("ignores events without a type or without a handler", () => {
    const token = vi.fn();
    const dispatch = dispatchSseEvent({ token });
    dispatch({ data: { content: "a" } });
    dispatch({ event: "complete", data: {} });
    expect(token).not.toHaveBeenCalled();
  });
});

describe("sseContentText (AE-0446)", () => {
  it("returns string content, else the fallback", () => {
    expect(sseContentText({ content: "hi" }, "x")).toBe("hi");
    expect(sseContentText({ content: 42 }, "x")).toBe("x");
    expect(sseContentText({}, "")).toBe("");
  });
});
