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

export { CHAT_MESSAGE_MAX_LENGTH } from "@/constants/chat";

/** Share of the limit at which the composer starts showing the counter. */
export const CHAT_LENGTH_COUNTER_RATIO = 0.8;

/** What went wrong with a chat turn, in terms the visitor can act on. */
export const CHAT_ERROR_KIND = {
  OFFLINE: "offline",
  TOO_LONG: "tooLong",
  LIMIT: "limit",
  NOT_FOUND: "notFound",
  SESSION_EXPIRED: "sessionExpired",
  GENERIC: "generic",
} as const;

export type ChatErrorKind =
  (typeof CHAT_ERROR_KIND)[keyof typeof CHAT_ERROR_KIND];

/** Where a chat turn failed, which decides whether a retry is safe. */
export const CHAT_FAILURE_STAGE = {
  CREATING: "creating",
  REQUESTING: "requesting",
  STREAMING: "streaming",
} as const;

export type ChatFailureStage =
  (typeof CHAT_FAILURE_STAGE)[keyof typeof CHAT_FAILURE_STAGE];
