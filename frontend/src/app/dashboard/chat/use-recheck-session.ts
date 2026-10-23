"use client";

import { useEffect } from "react";
import { CHAT_ERROR_KIND, type ChatErrorKind } from "@/modules/conversation";

/**
 * A 404 on the user's own conversation means it is gone or the session
 * expired (the stream answers both the same way). Re-reading an authenticated
 * endpoint tells them apart: an expired session gets a 401, which the API
 * client turns into a redirect to the login page; otherwise the "no longer
 * available" message stands.
 */
export function useRecheckSessionOnNotFound(
  error: ChatErrorKind | null,
  recheck: () => unknown,
): void {
  useEffect(() => {
    if (error === CHAT_ERROR_KIND.NOT_FOUND) {
      recheck();
    }
  }, [error, recheck]);
}
