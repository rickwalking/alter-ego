/**
 * Collaborative editing lock hook (UI-021, WF-005).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { HTTP_STATUS } from "@/constants/api";
import { WORKFLOW_API, LOCK_POLL_INTERVAL_MS } from "@/constants/workflow";
import { useAuth } from "@/modules/identity";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { isLockedByAnotherUser } from "@/modules/editorial/workflow/utils/collaborative-lock";
import type {
  ContentLock,
  LockActions,
  LockState,
  LockTarget,
} from "@/modules/editorial/workflow/types";

export type { ContentLock } from "@/modules/editorial/workflow/types";

type LockAttempt =
  | { outcome: "acquired"; lock: ContentLock }
  | { outcome: "conflict" }
  | { outcome: "failed" };

function lockUrl(contentId: string, contentType: string): string {
  return `${WORKFLOW_API.CONTENT_LOCK(contentId)}?content_type=${contentType}`;
}

/** The current lock: null when none, undefined when the read failed. */
async function fetchLock(
  contentId: string,
  contentType: string,
): Promise<ContentLock | null | undefined> {
  const response = await authenticatedFetch(lockUrl(contentId, contentType));
  if (
    response.status === HTTP_STATUS.NOT_FOUND ||
    response.status === HTTP_STATUS.NO_CONTENT
  ) {
    return null;
  }
  if (!response.ok) {
    return undefined;
  }
  return (await response.json()) as ContentLock | null;
}

async function postLock(
  contentId: string,
  contentType: string,
): Promise<LockAttempt> {
  const response = await authenticatedFetch(
    WORKFLOW_API.CONTENT_LOCK(contentId),
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content_type: contentType }),
    },
  );
  if (response.status === HTTP_STATUS.CONFLICT) {
    return { outcome: "conflict" };
  }
  if (!response.ok) {
    return { outcome: "failed" };
  }
  return { outcome: "acquired", lock: (await response.json()) as ContentLock };
}

/** The lock shown to this user; writes are dropped after unmount. */
function useLockState(currentUserId: string | null): LockState {
  const [activeLock, setActiveLock] = useState<ContentLock | null>(null);
  const [isLockedByOther, setIsLockedByOther] = useState(false);
  const mountedRef = useRef(true);
  const applyLockState = useCallback(
    (lock: ContentLock | null) => {
      if (!mountedRef.current) {
        return;
      }
      setActiveLock(lock);
      setIsLockedByOther(isLockedByAnotherUser(lock, currentUserId));
    },
    [currentUserId],
  );
  return { activeLock, isLockedByOther, applyLockState, mountedRef };
}

/** Take the lock on mount, poll it while mounted, release it on unmount. */
function useLockLifecycle(
  { contentId, contentType }: LockTarget,
  { applyLockState, mountedRef }: LockState,
  {
    refreshLock,
    releaseLock,
  }: Pick<LockActions, "refreshLock" | "releaseLock">,
): void {
  useEffect(() => {
    mountedRef.current = true;
    let cancelled = false;

    const bootstrap = async () => {
      const attempt = await postLock(contentId, contentType);
      if (cancelled) {
        return;
      }
      if (attempt.outcome === "conflict") {
        await refreshLock();
        return;
      }
      if (attempt.outcome === "acquired") {
        applyLockState(attempt.lock);
      }
    };

    void bootstrap();
    const interval = setInterval(() => {
      void refreshLock();
    }, LOCK_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      mountedRef.current = false;
      clearInterval(interval);
      void releaseLock();
    };
  }, [
    applyLockState,
    mountedRef,
    contentId,
    contentType,
    refreshLock,
    releaseLock,
  ]);
}

export function useCollaborativeEdit(contentId: string, contentType: string) {
  const { user } = useAuth();
  const lockState = useLockState(user?.id ?? null);
  const { applyLockState } = lockState;

  const refreshLock = useCallback(async () => {
    const lock = await fetchLock(contentId, contentType);
    if (lock !== undefined) {
      applyLockState(lock);
    }
  }, [applyLockState, contentId, contentType]);

  const acquireLock = useCallback(async () => {
    const attempt = await postLock(contentId, contentType);
    if (attempt.outcome === "conflict") {
      await refreshLock();
    }
    if (attempt.outcome !== "acquired") {
      return false;
    }
    applyLockState(attempt.lock);
    return true;
  }, [applyLockState, contentId, contentType, refreshLock]);

  const releaseLock = useCallback(async () => {
    await authenticatedFetch(lockUrl(contentId, contentType), {
      method: "DELETE",
    });
    applyLockState(null);
  }, [applyLockState, contentId, contentType]);

  useLockLifecycle({ contentId, contentType }, lockState, {
    refreshLock,
    releaseLock,
  });

  return {
    activeLock: lockState.activeLock,
    isLockedByOther: lockState.isLockedByOther,
    acquireLock,
    releaseLock,
    refreshLock,
  };
}
