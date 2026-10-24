import { HTTP_STATUS } from "@/constants/api";
import { ApiError } from "@/lib/api-client";
import { SseHttpError } from "@/lib/sse-http-error";
import {
  CHAT_ERROR_KIND,
  CHAT_FAILURE_STAGE,
  CHAT_TURN_IN_FLIGHT_CODE,
  type ChatErrorKind,
  type ChatFailureStage,
} from "./constants";

const STREAM_KIND_BY_STATUS: Readonly<Record<number, ChatErrorKind>> = {
  [HTTP_STATUS.UNPROCESSABLE_ENTITY]: CHAT_ERROR_KIND.TOO_LONG,
  [HTTP_STATUS.TOO_MANY_REQUESTS]: CHAT_ERROR_KIND.LIMIT,
  [HTTP_STATUS.NOT_FOUND]: CHAT_ERROR_KIND.NOT_FOUND,
  [HTTP_STATUS.UNAUTHORIZED]: CHAT_ERROR_KIND.SESSION_EXPIRED,
  [HTTP_STATUS.CONFLICT]: CHAT_ERROR_KIND.BUSY,
};

/** Failures a retry can fix: nothing was saved, or the previous reply is done. */
const RETRYABLE_KINDS: ReadonlySet<ChatErrorKind> = new Set([
  CHAT_ERROR_KIND.GENERIC,
  CHAT_ERROR_KIND.BUSY,
]);

const CREATE_KIND_BY_STATUS: Readonly<Record<number, ChatErrorKind>> = {
  [HTTP_STATUS.TOO_MANY_REQUESTS]: CHAT_ERROR_KIND.LIMIT,
  [HTTP_STATUS.UNAUTHORIZED]: CHAT_ERROR_KIND.SESSION_EXPIRED,
};

/** A chat failure the UI can explain, and whether retrying can help. */
export interface ChatFailure {
  kind: ChatErrorKind;
  /** True only when nothing was saved yet (no answer stream had started). */
  retryable: boolean;
}

function browserOffline(): boolean {
  return typeof navigator !== "undefined" && !navigator.onLine;
}

function failedBeforeResponse(stage: ChatFailureStage): boolean {
  return stage !== CHAT_FAILURE_STAGE.STREAMING;
}

function kindForStatus(status: number, stage: ChatFailureStage): ChatErrorKind {
  const table =
    stage === CHAT_FAILURE_STAGE.CREATING
      ? CREATE_KIND_BY_STATUS
      : STREAM_KIND_BY_STATUS;
  return table[status] ?? CHAT_ERROR_KIND.GENERIC;
}

/**
 * Map a failed chat request to what the visitor can do about it. Technical
 * detail (status text, exception messages) stays out of the UI.
 *
 * ``stage`` says where it failed: creating the conversation, requesting the
 * stream (no response yet: the server saved nothing), or while streaming
 * (the server already saved the question and closes the turn itself, so a
 * retry would only store it twice). A ``TypeError`` is "offline" only when
 * the browser is offline or fetch failed before any response; anywhere else
 * it is a bug, shown as a generic failure.
 */
export function classifyChatError(
  error: unknown,
  stage: ChatFailureStage,
): ChatFailure {
  const beforeResponse = failedBeforeResponse(stage);
  if (error instanceof SseHttpError || error instanceof ApiError) {
    const kind = kindForStatus(error.status, stage);
    return { kind, retryable: RETRYABLE_KINDS.has(kind) };
  }
  const offline =
    browserOffline() || (beforeResponse && error instanceof TypeError);
  if (offline) {
    return { kind: CHAT_ERROR_KIND.OFFLINE, retryable: beforeResponse };
  }
  return { kind: CHAT_ERROR_KIND.GENERIC, retryable: false };
}

/**
 * The failure an SSE error event reports: "still finishing the previous
 * reply" (retryable once it is done) when the server says so, else generic.
 */
export function classifyStreamErrorEvent(code: unknown): ChatFailure {
  return code === CHAT_TURN_IN_FLIGHT_CODE
    ? { kind: CHAT_ERROR_KIND.BUSY, retryable: true }
    : { kind: CHAT_ERROR_KIND.GENERIC, retryable: false };
}
