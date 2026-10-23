import type { Message } from "@/schemas/chat";
import { REPLY_POLL_INTERVAL_MS, REPLY_POLL_WINDOW_MS } from "./constants";

const USER_ROLE: Message["role"] = "user";

/**
 * Whether the server is most likely still writing a reply: the history ends
 * with the user's message, sent less than ``REPLY_POLL_WINDOW_MS`` ago (for
 * example after a refresh mid-stream; the server keeps going and saves it).
 * A message stamped in the "future" by a skewed clock counts only within the
 * same window, so skew can never make the wait endless.
 */
export function isAwaitingReply(
  history: readonly Message[] | undefined,
  now: number = Date.now(),
): boolean {
  const last = history?.at(-1);
  if (last?.role !== USER_ROLE) return false;
  const sentAt = Date.parse(last.created_at);
  if (!Number.isFinite(sentAt)) return false;
  return Math.abs(now - sentAt) < REPLY_POLL_WINDOW_MS;
}

/**
 * ``refetchInterval`` for the history: poll only while a reply is awaited.
 * The waiting window bounds it, so no separate re-read cap is needed.
 */
export function replyPollInterval(
  history: readonly Message[] | undefined,
): number | false {
  return isAwaitingReply(history) ? REPLY_POLL_INTERVAL_MS : false;
}
