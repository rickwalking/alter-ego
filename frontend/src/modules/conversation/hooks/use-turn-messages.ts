"use client";

import { useCallback, useMemo, useState } from "react";
import { mergeMessages } from "./merge-messages";
import type { TurnMessagesInput, UseSseChatReturn } from "./types";

/**
 * The messages on screen, and a send that remembers where in the history its
 * turn began: only rows saved since then can stand in for the turn's own
 * question and reply, so the same question asked again is never hidden.
 */
export function useTurnMessages({
  historyMessages,
  optimisticMessages,
  isStreaming,
  sendTurn,
  isBusy,
}: TurnMessagesInput): Pick<UseSseChatReturn, "messages" | "sendMessage"> {
  const [turnStart, setTurnStart] = useState(0);
  const sendMessage = useCallback<UseSseChatReturn["sendMessage"]>(
    (content, target) => {
      if (!isBusy()) setTurnStart(historyMessages.length);
      return sendTurn(content, target);
    },
    [isBusy, historyMessages.length, sendTurn],
  );
  const messages = useMemo(
    () =>
      mergeMessages(historyMessages, optimisticMessages, {
        stopped: !isStreaming,
        turnStart,
      }),
    [historyMessages, optimisticMessages, isStreaming, turnStart],
  );
  return { messages, sendMessage };
}
