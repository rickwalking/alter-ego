/** Outcome of one ``useSseChat().sendMessage`` call. */
export const CHAT_SEND_RESULT = {
  /** The reply streamed to the end. */
  SENT: "sent",
  /** Creating the conversation or streaming failed; the error is shown. */
  FAILED: "failed",
  /** Nothing was sent: empty text, no conversation, a turn already in flight, or aborted. */
  IGNORED: "ignored",
} as const;

export type ChatSendResult =
  (typeof CHAT_SEND_RESULT)[keyof typeof CHAT_SEND_RESULT];

export const CHAT_UNKNOWN_ERROR = "Unknown error";
