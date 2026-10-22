"use client";

import { useState } from "react";
import { ApiError } from "@/lib/api-client";
import { EDITORIAL_WORKFLOW_CONFLICT_CODES } from "@/constants/editorial-workflow";
import { useSaveCarouselCopy } from "./use-save-carousel-copy";
import type { CarouselCopyTexts } from "./types";

/** A save refused because the page's lock version is stale. */
function isVersionConflict(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    error.detail === EDITORIAL_WORKFLOW_CONFLICT_CODES.VERSION_CONFLICT
  );
}

/**
 * The caption / LinkedIn save of the publish page and the final review. Each
 * save sends the newest lock version the page knows (the loaded workflow state's, or the one the last
 * save returned, whichever is higher) and refreshes the page's data afterwards.
 * Without a loaded lock version there is nothing safe to send, so no save.
 * A save refused as ``version_conflict`` refetches the page so the next save
 * sends the current lock version; the drafts stay in the editor.
 */
export function useCopySave(
  projectId: string,
  loadedLockVersion: number | undefined,
  refreshAll: () => Promise<unknown>,
): ((texts: CarouselCopyTexts) => Promise<void>) | undefined {
  const saveCopy = useSaveCarouselCopy();
  const [savedLockVersion, setSavedLockVersion] = useState(0);
  if (loadedLockVersion === undefined) {
    return undefined;
  }
  const lockVersion = Math.max(loadedLockVersion, savedLockVersion);
  return async (texts: CarouselCopyTexts): Promise<void> => {
    try {
      const saved = await saveCopy.mutateAsync({
        projectId,
        lockVersion,
        texts,
      });
      setSavedLockVersion(saved.lock_version);
      void refreshAll();
    } catch (error) {
      if (isVersionConflict(error)) {
        void refreshAll();
      }
      throw error;
    }
  };
}
