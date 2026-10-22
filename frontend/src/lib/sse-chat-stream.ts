import type { RefObject } from "react";

import type { Message } from "@/schemas/chat";

/**
 * Shared SSE chat streaming primitives.
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
  /** The id of the assistant message this stream writes into. */
  streamingMsgId: string;
}

/** A fresh assistant message holding the first streamed token. */
function streamingAssistantMessage(id: string, content: string): Message {
  return {
    id,
    role: ASSISTANT_ROLE,
    content,
    sources: [],
    created_at: new Date().toISOString(),
  };
}

/**
 * Fold a streamed token into the optimistic message list. Shared by the
 * conversation and publishing chat hooks so the SSE token-accumulation
 * algorithm lives in one place.
 *
 * Pure: it depends only on its input, never on a ref read at update time, so
 * React may batch, defer or replay the state updater and every token still
 * lands exactly once, in order, in the one message with ``streamingMsgId``.
 */
export function appendStreamToken({
  messages,
  token,
  streamingMsgId,
}: AppendStreamTokenInput): Message[] {
  const index = messages.findIndex((message) => message.id === streamingMsgId);
  if (index === -1) {
    return [...messages, streamingAssistantMessage(streamingMsgId, token)];
  }
  return messages.map((message, position) =>
    position === index
      ? { ...message, content: message.content + token }
      : message,
  );
}

/** The per-stream ref a chat hook resets when a stream begins. */
export interface StreamAccumulationRefs {
  msgIdRef: RefObject<string | null>;
}

let streamSequence = 0;

/** A unique id for the assistant message of a new stream. */
export function newStreamMessageId(prefix: string): string {
  streamSequence += 1;
  return `${prefix}${Date.now()}-${streamSequence}`;
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

/** Clear the streaming message id. */
export function resetStreamRefs(refs: StreamAccumulationRefs): void {
  refs.msgIdRef.current = null;
}

/**
 * Begin a new stream: give it a fresh assistant message id, abort the previous
 * in-flight request, and return a fresh `AbortController`. The caller stores it
 * on its own `abortRef` (keeping the ref assignment local to the hook, which
 * the react-hooks lint rule requires for the unmount-cleanup path).
 */
export function beginStream(
  refs: StreamAccumulationRefs,
  previousController: AbortController | null,
  streamIdPrefix: string,
): AbortController {
  refs.msgIdRef.current = newStreamMessageId(streamIdPrefix);
  previousController?.abort();
  return new AbortController();
}
