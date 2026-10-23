/**
 * Gherkin: tests/features/dashboard-chat.feature
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import type { Message } from "@/schemas/chat";
import { REPLY_POLL_WINDOW_MS } from "../constants";
import { useAwaitingReply } from "./use-awaiting-reply";

const SENT = Date.parse("2026-10-22T12:00:00Z");
const question: Message = {
  id: "m1",
  role: "user",
  content: "QA test",
  sources: [],
  created_at: new Date(SENT).toISOString(),
};

describe("useAwaitingReply", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(SENT + 1000);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  /** Scenario: Polling stops when nothing is awaited */
  it("stops waiting once the window passes, even without a reply", () => {
    const { result } = renderHook(() => useAwaitingReply([question], true));
    expect(result.current).toBe(true);

    act(() => {
      vi.advanceTimersByTime(REPLY_POLL_WINDOW_MS);
    });

    expect(result.current).toBe(false);
  });

  /** Scenario: Polling stops when nothing is awaited */
  it("does not wait while disabled (a turn is on screen)", () => {
    const { result } = renderHook(() => useAwaitingReply([question], false));
    expect(result.current).toBe(false);
  });
});
