/**
 * Gherkin: tests/features/duplication-gate.feature (shared SSE plumbing)
 * Covers the shared SSE streaming primitives extracted from useSseChat and
 * usePublishChat so the two hooks no longer duplicate them.
 */
import { describe, expect, it, vi } from "vitest";

import type { Message } from "@/schemas/chat";

import {
  appendStreamToken,
  beginStream,
  createOptimisticUserMessage,
  newStreamMessageId,
  resetStreamRefs,
} from "./sse-chat-stream";

function assistantMessage(id: string, content: string): Message {
  return { id, role: "assistant", content, sources: [], created_at: "t" };
}

function makeRefs() {
  return {
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
  it("clears the streaming-message-id ref", () => {
    const refs = makeRefs();
    resetStreamRefs(refs);
    expect(refs.msgIdRef.current).toBeNull();
  });
});

describe("beginStream", () => {
  it("assigns a new stream id, aborts the prior controller, and returns a fresh one", () => {
    const refs = makeRefs();
    const previous = new AbortController();
    const abortSpy = vi.spyOn(previous, "abort");

    const controller = beginStream(refs, previous, "stream-");

    expect(abortSpy).toHaveBeenCalledOnce();
    expect(refs.msgIdRef.current).not.toBe("old-id");
    expect(refs.msgIdRef.current?.startsWith("stream-")).toBe(true);
    expect(controller).not.toBe(previous);
    expect(controller).toBeInstanceOf(AbortController);
    expect(controller.signal.aborted).toBe(false);
  });

  it("works when there is no prior controller", () => {
    const refs = makeRefs();
    const controller = beginStream(refs, null, "stream-");
    expect(controller).toBeInstanceOf(AbortController);
    expect(controller.signal.aborted).toBe(false);
  });
});

describe("newStreamMessageId", () => {
  it("never repeats, even within the same millisecond", () => {
    const ids = new Set(
      Array.from({ length: 5 }, () => newStreamMessageId("s-")),
    );
    expect(ids.size).toBe(5);
    for (const id of ids) {
      expect(id.startsWith("s-")).toBe(true);
    }
  });
});

describe("appendStreamToken", () => {
  const user: Message = {
    id: "u1",
    role: "user",
    content: "hi",
    sources: [],
    created_at: "t",
  };

  it("creates the assistant message from the first token alone", () => {
    const messages = appendStreamToken({
      messages: [user],
      token: "Hel",
      streamingMsgId: "stream-1",
    });

    expect(messages).toHaveLength(2);
    expect(messages[1]).toMatchObject({
      id: "stream-1",
      role: "assistant",
      content: "Hel",
    });
  });

  it("appends subsequent tokens onto the message with the stream id", () => {
    const messages = appendStreamToken({
      messages: [assistantMessage("stream-1", "Hel")],
      token: "lo",
      streamingMsgId: "stream-1",
    });

    expect(messages).toEqual([assistantMessage("stream-1", "Hello")]);
  });

  it("finds the streaming message even when it is not the last one", () => {
    const messages = appendStreamToken({
      messages: [assistantMessage("stream-1", "Hel"), user],
      token: "lo",
      streamingMsgId: "stream-1",
    });

    expect(messages.map((message) => message.content)).toEqual(["Hello", "hi"]);
  });

  it("does not mutate its input", () => {
    const input = [assistantMessage("stream-1", "Hel")];
    appendStreamToken({
      messages: input,
      token: "lo",
      streamingMsgId: "stream-1",
    });
    expect(input[0]!.content).toBe("Hel");
  });
});
