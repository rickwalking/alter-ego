import { HTTP_STATUS } from "@/constants/api";
import { ApiError } from "@/lib/api-client";
import { SseHttpError } from "@/lib/sse-http-error";
import { CHAT_ERROR_KIND, type ChatErrorKind } from "./constants";

const KIND_BY_STATUS: Readonly<Record<number, ChatErrorKind>> = {
  [HTTP_STATUS.UNPROCESSABLE_ENTITY]: CHAT_ERROR_KIND.TOO_LONG,
  [HTTP_STATUS.TOO_MANY_REQUESTS]: CHAT_ERROR_KIND.LIMIT,
  [HTTP_STATUS.NOT_FOUND]: CHAT_ERROR_KIND.NOT_FOUND,
  [HTTP_STATUS.UNAUTHORIZED]: CHAT_ERROR_KIND.SESSION_EXPIRED,
};

function httpStatus(error: unknown): number | null {
  if (error instanceof SseHttpError || error instanceof ApiError) {
    return error.status;
  }
  return null;
}

function isOffline(error: unknown): boolean {
  const browserOffline = typeof navigator !== "undefined" && !navigator.onLine;
  return browserOffline || error instanceof TypeError;
}

/**
 * Map a failed chat request to what the visitor can do about it. Technical
 * detail (status text, exception messages) stays out of the UI.
 */
export function classifyChatError(error: unknown): ChatErrorKind {
  const status = httpStatus(error);
  if (status !== null) {
    return KIND_BY_STATUS[status] ?? CHAT_ERROR_KIND.GENERIC;
  }
  return isOffline(error) ? CHAT_ERROR_KIND.OFFLINE : CHAT_ERROR_KIND.GENERIC;
}
