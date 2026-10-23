"use client";

import { useEffect, useState } from "react";
import type { Message } from "@/schemas/chat";
import { REPLY_POLL_INTERVAL_MS } from "../constants";
import { isAwaitingReply } from "../reply-wait";

/**
 * Whether a reply is still awaited, re-checked on a clock while it is: once
 * the waiting window passes the "typing" state ends even if no reply ever
 * arrives (nothing else would re-render the view then).
 */
export function useAwaitingReply(
  history: readonly Message[],
  enabled: boolean,
): boolean {
  const [now, setNow] = useState(() => Date.now());
  const awaiting = enabled && isAwaitingReply(history, now);
  useEffect(() => {
    if (!awaiting) return;
    const timer = setInterval(() => {
      setNow(Date.now());
    }, REPLY_POLL_INTERVAL_MS);
    return () => {
      clearInterval(timer);
    };
  }, [awaiting]);
  return awaiting;
}
