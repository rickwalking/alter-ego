/**
 * Collaborative editing lock hook (UI-021, WF-005).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { WORKFLOW_API, LOCK_POLL_INTERVAL_MS } from "@/constants/workflow";
import { useAuth } from "@/hooks/use-auth";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { isLockedByAnotherUser } from "@/modules/editorial/workflow/utils/collaborative-lock";
import type { ContentLock } from "@/modules/editorial/workflow/types";

export type { ContentLock } from "@/modules/editorial/workflow/types";

export function useCollaborativeEdit(contentId: string, contentType: string) {
  const { user } = useAuth();
  const currentUserId = user?.id ?? null;
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

  const refreshLock = useCallback(async () => {
    const response = await authenticatedFetch(
      `${WORKFLOW_API.CONTENT_LOCK(contentId)}?content_type=${contentType}`,
    );
    if (response.status === 404 || response.status === 204) {
      applyLockState(null);
      return;
    }
    if (!response.ok) {
      return;
    }
    const lock = (await response.json()) as ContentLock | null;
    applyLockState(lock);
  }, [applyLockState, contentId, contentType]);

  const acquireLock = useCallback(async () => {
    const response = await authenticatedFetch(
      WORKFLOW_API.CONTENT_LOCK(contentId),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content_type: contentType }),
      },
    );
    if (response.status === 409) {
      await refreshLock();
      return false;
    }
    if (!response.ok) {
      return false;
    }
    const lock = (await response.json()) as ContentLock;
    applyLockState(lock);
    return true;
  }, [applyLockState, contentId, contentType, refreshLock]);

  const releaseLock = useCallback(async () => {
    await authenticatedFetch(
      `${WORKFLOW_API.CONTENT_LOCK(contentId)}?content_type=${contentType}`,
      { method: "DELETE" },
    );
    applyLockState(null);
  }, [applyLockState, contentId, contentType]);

  useEffect(() => {
    mountedRef.current = true;
    let cancelled = false;

    const bootstrap = async () => {
      const response = await authenticatedFetch(
        WORKFLOW_API.CONTENT_LOCK(contentId),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content_type: contentType }),
        },
      );
      if (cancelled) {
        return;
      }
      if (response.status === 409) {
        await refreshLock();
        return;
      }
      if (!response.ok) {
        return;
      }
      const lock = (await response.json()) as ContentLock;
      applyLockState(lock);
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
  }, [applyLockState, contentId, contentType, refreshLock, releaseLock]);

  return {
    activeLock,
    isLockedByOther,
    acquireLock,
    releaseLock,
    refreshLock,
  };
}
