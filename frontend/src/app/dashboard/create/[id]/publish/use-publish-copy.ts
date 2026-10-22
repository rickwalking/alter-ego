"use client";

import {
  useCopyHistory,
  useCopySave,
  type CopyHistory,
  type EditorialWorkflowState,
} from "@/modules/publishing";

type SaveCopy = ReturnType<typeof useCopySave>;

/** The publish page's caption / LinkedIn save and version history. */
export interface PublishCopy {
  saveCopy: SaveCopy;
  copyHistory: CopyHistory;
}

/**
 * Both send the loaded workflow lock version and refresh the page after a
 * save or a restore.
 */
export function usePublishCopy(
  projectId: string,
  workflowState: EditorialWorkflowState | null | undefined,
  refreshAll: () => Promise<unknown>,
): PublishCopy {
  const lockVersion = workflowState?.lock_version;
  return {
    saveCopy: useCopySave(projectId, lockVersion, refreshAll),
    copyHistory: useCopyHistory(projectId, lockVersion, refreshAll),
  };
}
