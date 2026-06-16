/**
 * Gherkin: tests/features/duplication-gate.feature (AE-0150 shared SSE plumbing)
 * Covers the shared SSE streaming primitives extracted from useSseChat and
 * usePublishChat so the two hooks no longer duplicate them.
 */
import { describe, expect, it, vi } from "vitest";

import type { Message } from "@/schemas/chat";

import {
  appendStreamToken,
  beginStream,
  createOptimisticUserMessage,
  resetStreamRefs,
} from "./sse-chat-stream";

function assistantMessage(id: string, content: string): Message {
  return { id, role: "assistant", content, sources: [], created_at: "t" };
}

function makeRefs() {
  return {
    contentRef: { current: "seeded" },
    msgIdRef: { current: "old-id" as string | null },
  };
}

describe("createOptimisticUserMessage", () => {
  it("builds a user message with the given id prefix and content", () => {
    const message = createOptimisticUserMessage("  hello  ".trim(), "user-");

    expect(message.role).toBe("user");
    expect(message.content).toBe("hello");
    expect(message.sources).toEqual([]);
    expect(message.id.startsWith("user-")).toBe(true);
    expect(typeof message.created_at).toBe("string");
  });

  it("honors a different id prefix (publish chat uses opt-)", () => {
    const message = createOptimisticUserMessage("hi", "opt-");
    expect(message.id.startsWith("opt-")).toBe(true);
  });
});

describe("resetStreamRefs", () => {
  it("clears the content and streaming-message-id refs", () => {
    const refs = makeRefs();
    resetStreamRefs(refs);
    expect(refs.contentRef.current).toBe("");
    expect(refs.msgIdRef.current).toBeNull();
  });
});

describe("beginStream", () => {
  it("resets refs, aborts the prior controller, and returns a fresh one", () => {
    const refs = makeRefs();
    const previous = new AbortController();
    const abortSpy = vi.spyOn(previous, "abort");

    const controller = beginStream(refs, previous);

    expect(abortSpy).toHaveBeenCalledOnce();
    expect(refs.contentRef.current).toBe("");
    expect(refs.msgIdRef.current).toBeNull();
    expect(controller).not.toBe(previous);
    expect(controller).toBeInstanceOf(AbortController);
    expect(controller.signal.aborted).toBe(false);
  });

  it("works when there is no prior controller", () => {
    const refs = makeRefs();
    const controller = beginStream(refs, null);
    expect(controller).toBeInstanceOf(AbortController);
    expect(controller.signal.aborted).toBe(false);
  });
});

describe("appendStreamToken", () => {
  it("creates a new assistant message on the first token", () => {
    const { messages, streamingMsgId } = appendStreamToken({
      messages: [
        { id: "u1", role: "user", content: "hi", sources: [], created_at: "t" },
      ],
      token: "Hel",
      accumulatedContent: "Hel",
      streamingMsgId: null,
      newIdPrefix: "stream-",
    });

    expect(messages).toHaveLength(2);
    expect(messages[1].role).toBe("assistant");
    expect(messages[1].content).toBe("Hel");
    expect(messages[1].id.startsWith("stream-")).toBe(true);
    expect(streamingMsgId).toBe(messages[1].id);
  });

  it("appends subsequent tokens onto the existing streaming message", () => {
    const first = appendStreamToken({
      messages: [assistantMessage("stream-1", "Hel")],
      token: "lo",
      accumulatedContent: "Hello",
      streamingMsgId: "stream-1",
      newIdPrefix: "stream-",
    });

    expect(first.messages).toHaveLength(1);
    expect(first.messages[0].content).toBe("Hello");
    expect(first.streamingMsgId).toBe("stream-1");
  });

  it("preserves the existing streaming id (does not generate a new one)", () => {
    const { streamingMsgId } = appendStreamToken({
      messages: [assistantMessage("stream-1", "Hel")],
      token: "lo",
      accumulatedContent: "Hello",
      streamingMsgId: "stream-1",
      newIdPrefix: "stream-",
    });
    expect(streamingMsgId).toBe("stream-1");
  });
});
