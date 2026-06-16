/** Collaborative lock helpers (UI-021). */

import type { ContentLock } from "../types";

export function isLockedByAnotherUser(
  lock: ContentLock | null,
  currentUserId: string | null,
): boolean {
  if (!lock || !currentUserId) {
    return false;
  }
  return lock.user_id !== currentUserId;
}
