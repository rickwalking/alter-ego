"use client";

import { useState } from "react";
import { ApiError } from "@/lib/api-client";
import { EDITORIAL_WORKFLOW_CONFLICT_CODES } from "@/constants/editorial-workflow";
import { copySaveErrorKey } from "@/modules/publishing/distribution/lib/copy-editor-state";
import type { CopyHistory, CopyRestoreStatus } from "./types";
import {
  useCarouselCopyVersions,
  useRestoreCopyVersion,
} from "./use-copy-versions";

const IDLE: CopyRestoreStatus = { kind: "idle" };

/** A restore refused because the page's lock version is stale. */
function isVersionConflict(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    error.detail === EDITORIAL_WORKFLOW_CONFLICT_CODES.VERSION_CONFLICT
  );
}

/**
 * The caption / LinkedIn history of a carousel and its restore. A restore
 * sends the page's loaded lock version and refreshes the page's data, whether
 * it worked or was refused as stale (so the next try sends the current lock
 * version); it stays "restoring" until that refetch is done. Without a loaded
 * lock version nothing can be restored.
 */
export function useCopyHistory(
  projectId: string,
  loadedLockVersion: number | undefined,
  refreshAll: () => Promise<unknown>,
): CopyHistory {
  const versions = useCarouselCopyVersions(projectId);
  const restoreVersion = useRestoreCopyVersion();
  const [status, setStatus] = useState<CopyRestoreStatus>(IDLE);
  const base = {
    versions: versions.data?.versions ?? [],
    loading: versions.isLoading,
    status,
  };
  if (loadedLockVersion === undefined) {
    return base;
  }
  const restore = async (versionNumber: number): Promise<void> => {
    setStatus({ kind: "restoring", versionNumber });
    try {
      await restoreVersion.mutateAsync({
        projectId,
        lockVersion: loadedLockVersion,
        versionNumber,
      });
      await Promise.allSettled([refreshAll()]);
      setStatus(IDLE);
    } catch (error) {
      if (isVersionConflict(error)) {
        await Promise.allSettled([refreshAll()]);
      }
      setStatus({ kind: "error", errorKey: copySaveErrorKey(error) });
    }
  };
  return { ...base, restore };
}
