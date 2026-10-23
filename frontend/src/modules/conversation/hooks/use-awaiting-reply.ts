"use client";

import { useEffect, useState } from "react";
import type { Message } from "@/schemas/chat";
import { turnStillOpen } from "./merge-messages";
import type { ChatStreamState } from "./types";
import { REPLY_POLL_INTERVAL_MS } from "../constants";
import { isAwaitingReply } from "../reply-wait";

const USER_ROLE: Message["role"] = "user";

/**
 * Whether a reply is still awaited, re-checked on a clock while the history
 * ends with a question: once the waiting window passes the "typing" state ends
 * even if no reply ever arrives (nothing else would re-render the view then).
 * The clock is read again as soon as the last message changes, so a question
 * sent long after the last wait is judged by the current time.
 */
export function useAwaitingReply(
  history: readonly Message[],
  enabled: boolean,
): boolean {
  const [now, setNow] = useState(() => Date.now());
  const last = history.at(-1);
  const lastId = last?.id ?? "";
  const asked = enabled && last?.role === USER_ROLE;
  useEffect(() => {
    if (!asked) return;
    const tick = (): void => {
      setNow(Date.now());
    };
    const first = setTimeout(tick, 0);
    const timer = setInterval(tick, REPLY_POLL_INTERVAL_MS);
    return () => {
      clearTimeout(first);
      clearInterval(timer);
    };
  }, [asked, lastId]);
  return asked && isAwaitingReply(history, now);
}

/**
 * Whether a reply is still being written somewhere: after a refresh (the
 * history ends with a recent question) or after a stop, until the reply the
 * server saves for the stopped turn is in the history.
 */
export function useReplyPending(
  historyMessages: Message[],
  stream: Pick<ChatStreamState, "optimisticMessages" | "isStreaming">,
  stoppedWithHistory: boolean,
): boolean {
  const { optimisticMessages, isStreaming } = stream;
  const stoppedTurn = stoppedWithHistory && !isStreaming;
  const afterRefresh = useAwaitingReply(
    historyMessages,
    !isStreaming && (optimisticMessages.length === 0 || stoppedTurn),
  );
  return (
    afterRefresh ||
    (stoppedTurn && turnStillOpen(historyMessages, optimisticMessages))
  );
}
