/**
 * Gherkin: tests/features/dashboard-chat.feature
 */
import { describe, expect, it } from "vitest";

import type { Message } from "@/schemas/chat";
import { REPLY_POLL_INTERVAL_MS, REPLY_POLL_WINDOW_MS } from "./constants";
import { isAwaitingReply, replyPollInterval } from "./reply-wait";

const NOW = Date.parse("2026-10-22T12:00:00Z");

function message(role: Message["role"], agoMs: number): Message {
  return {
    id: `${role}-${String(agoMs)}`,
    role,
    content: "x",
    sources: [],
    created_at: new Date(NOW - agoMs).toISOString(),
  };
}

describe("reply wait", () => {
  /** Scenario: A reply that was still streaming appears after a refresh */
  it("awaits a reply to a recent unanswered user message", () => {
    expect(isAwaitingReply([message("user", 5_000)], NOW)).toBe(true);
  });

  /** Scenario: Polling stops when nothing is awaited */
  it.each([
    ["no history", undefined],
    [
      "an answered conversation",
      [message("user", 9_000), message("assistant", 5_000)],
    ],
    ["a stale question", [message("user", REPLY_POLL_WINDOW_MS + 1)]],
  ])("does not wait for %s", (_label, history) => {
    expect(isAwaitingReply(history, NOW)).toBe(false);
  });

  /** Scenario: Polling stops when nothing is awaited */
  it("ignores clock skew beyond the window and caps the number of re-reads", () => {
    expect(
      isAwaitingReply([message("user", -REPLY_POLL_WINDOW_MS - 1)], NOW),
    ).toBe(false);
    const justNow = NOW - Date.now();
    expect(replyPollInterval([message("user", justNow)], 90)).toBe(false);
  });

  /** Scenario: A reply that was still streaming appears after a refresh */
  it("polls every 2 seconds only while waiting", () => {
    const justNow = NOW - Date.now();
    expect(replyPollInterval([message("user", justNow)])).toBe(
      REPLY_POLL_INTERVAL_MS,
    );
    expect(replyPollInterval([message("assistant", justNow)])).toBe(false);
  });
});
