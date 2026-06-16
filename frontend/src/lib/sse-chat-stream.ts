import type { MutableRefObject } from "react";

import type { Message } from "@/schemas/chat";

/**
 * Shared SSE chat streaming primitives (AE-0150).
 *
 * Both `useSseChat` (conversation) and `usePublishChat` (publishing) optimistic
 * a user message and (re)start a streaming request the same way. This module
 * holds that shared logic so the two hooks do not duplicate it. The per-hook
 * event handling (sources, tool results, finalize/error) intentionally stays in
 * each hook — only the common "append user message + begin stream" plumbing is
 * shared here.
 */

const USER_ROLE: Message["role"] = "user";
const ASSISTANT_ROLE: Message["role"] = "assistant";

export interface AppendStreamTokenInput {
  messages: Message[];
  /** The newly received token. */
  token: string;
  /** Running accumulated content (`contentRef.current` after appending token). */
  accumulatedContent: string;
  /** Current streaming assistant message id, or null before the first token. */
  streamingMsgId: string | null;
  /** Prefix for the generated streaming message id (e.g. "stream-"). */
  newIdPrefix: string;
}

export interface AppendStreamTokenOutput {
  messages: Message[];
  /** The streaming assistant message id (existing or newly generated). */
  streamingMsgId: string;
}

/**
 * Fold a streamed token into the optimistic message list (AE-0150). Shared by
 * the conversation and publishing chat hooks so the SSE token-accumulation
 * algorithm lives in one place. Pure: callers persist the returned
 * `streamingMsgId` onto their own ref.
 */
export function appendStreamToken({
  messages,
  token,
  accumulatedContent,
  streamingMsgId,
  newIdPrefix,
}: AppendStreamTokenInput): AppendStreamTokenOutput {
  const last = messages[messages.length - 1];
  if (last?.role === ASSISTANT_ROLE && last.id === streamingMsgId) {
    // Accumulate onto the existing streaming assistant message, keying off the
    // message id (the ref may have been cleared by a COMPLETE event due to
    // React batching).
    return {
      messages: [
        ...messages.slice(0, -1),
        { ...last, content: last.content + token },
      ],
      streamingMsgId,
    };
  }
  const id = streamingMsgId || `${newIdPrefix}${Date.now()}`;
  const newMsg: Message = {
    id,
    role: ASSISTANT_ROLE,
    content: accumulatedContent,
    sources: [],
    created_at: new Date().toISOString(),
  };
  return { messages: [...messages, newMsg], streamingMsgId: id };
}

/** The per-stream accumulation refs a chat hook clears when a stream begins. */
export interface StreamAccumulationRefs {
  contentRef: MutableRefObject<string>;
  msgIdRef: MutableRefObject<string | null>;
}

/** Build the optimistic user message appended before a stream starts. */
export function createOptimisticUserMessage(
  content: string,
  idPrefix: string,
): Message {
  return {
    id: `${idPrefix}${Date.now()}`,
    role: USER_ROLE,
    content,
    sources: [],
    created_at: new Date().toISOString(),
  };
}

/** Clear the per-stream accumulation refs (content + streaming message id). */
export function resetStreamRefs(refs: StreamAccumulationRefs): void {
  refs.contentRef.current = "";
  refs.msgIdRef.current = null;
}

/**
 * Begin a new stream: reset the accumulation refs, abort the previous in-flight
 * request, and return a fresh `AbortController`. The caller stores it on its own
 * `abortRef` (keeping the ref assignment local to the hook, which the
 * react-hooks lint rule requires for the unmount-cleanup path).
 */
export function beginStream(
  refs: StreamAccumulationRefs,
  previousController: AbortController | null,
): AbortController {
  resetStreamRefs(refs);
  previousController?.abort();
  return new AbortController();
}
