/**
 * Shared SSE chat streaming hook used by useSseChat and usePublishChat.
 * Verifies the user-turn start, token folding, ref reset, and unmount abort.
 */
import { StrictMode, createElement } from "react";
import type { ReactNode } from "react";
import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useChatStream } from "./use-chat-stream";

describe("useChatStream", () => {
  it("startUserTurn appends an optimistic user message and starts streaming", () => {
    const { result } = renderHook(() => useChatStream("user-", "stream-"));

    let signal: AbortSignal | undefined;
    act(() => {
      signal = result.current.startUserTurn("hello");
    });

    expect(result.current.isStreaming).toBe(true);
    expect(result.current.optimisticMessages).toHaveLength(1);
    expect(result.current.optimisticMessages[0]).toMatchObject({
      role: "user",
      content: "hello",
    });
    expect(result.current.optimisticMessages[0]!.id.startsWith("user-")).toBe(
      true,
    );
    expect(signal?.aborted).toBe(false);
  });

  it("appendToken creates then extends the streaming assistant message", () => {
    const { result } = renderHook(() => useChatStream("user-", "stream-"));

    act(() => {
      result.current.startUserTurn("hi");
    });
    act(() => {
      result.current.appendToken("Hel");
    });
    act(() => {
      result.current.appendToken("lo");
    });

    const messages = result.current.optimisticMessages;
    const assistant = messages[messages.length - 1];
    expect(assistant!.role).toBe("assistant");
    expect(assistant!.content).toBe("Hello");
    expect(assistant!.id.startsWith("stream-")).toBe(true);
  });

  function assistantTexts(
    messages: { role: string; content: string }[],
  ): string[] {
    return messages
      .filter((message) => message.role === "assistant")
      .map((message) => message.content);
  }

  function strictWrapper({ children }: { children: ReactNode }) {
    return createElement(StrictMode, null, children);
  }

  // Scenario: Tokens that arrive in one batch render once, in order
  it("folds tokens batched in one update without duplicating text", () => {
    const { result } = renderHook(() => useChatStream("user-", "stream-"), {
      wrapper: strictWrapper,
    });
    act(() => {
      result.current.startUserTurn("oi");
    });
    act(() => {
      result.current.appendToken("Tudo");
      result.current.appendToken(" ótimo");
      result.current.appendToken("!");
    });
    act(() => {
      result.current.appendToken(" Eu");
    });

    expect(assistantTexts(result.current.optimisticMessages)).toEqual([
      "Tudo ótimo! Eu",
    ]);
  });

  // Scenario: The first token and a reply that ends in the same batch are kept in one bubble
  it("keeps the first token and one bubble when the stream ends in the same batch", () => {
    const { result } = renderHook(() => useChatStream("user-", "stream-"));
    act(() => {
      result.current.startUserTurn("code please");
    });
    act(() => {
      result.current.appendToken("```");
      result.current.appendToken("python");
      result.current.resetStreamingRefs();
    });

    expect(assistantTexts(result.current.optimisticMessages)).toEqual([
      "```python",
    ]);
  });

  // Scenario: Tokens that arrive in one batch render once, in order
  it("starts a separate bubble for the next turn", () => {
    const { result } = renderHook(() => useChatStream("user-", "stream-"));
    act(() => {
      result.current.startUserTurn("one");
      result.current.appendToken("first");
      result.current.resetStreamingRefs();
    });
    act(() => {
      result.current.startUserTurn("two");
      result.current.appendToken("second");
    });

    expect(assistantTexts(result.current.optimisticMessages)).toEqual([
      "first",
      "second",
    ]);
  });

  it("startUserTurn aborts the previous in-flight stream", () => {
    const { result } = renderHook(() => useChatStream("user-", "stream-"));

    let firstSignal: AbortSignal | undefined;
    act(() => {
      firstSignal = result.current.startUserTurn("first");
    });
    act(() => {
      result.current.startUserTurn("second");
    });

    expect(firstSignal?.aborted).toBe(true);
  });

  it("aborts the in-flight stream on unmount", () => {
    const { result, unmount } = renderHook(() =>
      useChatStream("user-", "stream-"),
    );

    let signal: AbortSignal | undefined;
    act(() => {
      signal = result.current.startUserTurn("hi");
    });
    expect(signal?.aborted).toBe(false);

    unmount();
    expect(signal?.aborted).toBe(true);
  });
});
