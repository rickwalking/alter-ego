"use client";

import { useState } from "react";
import {
  useSaveCarouselCopy,
  type CarouselCopyTexts,
} from "@/modules/publishing";

/**
 * The publish page's caption / LinkedIn save. Each save sends the newest lock
 * version the page knows (the loaded workflow state's, or the one the last
 * save returned, whichever is higher) and refreshes the page afterwards.
 * Without a loaded lock version there is nothing safe to send, so no save.
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
    const saved = await saveCopy.mutateAsync({ projectId, lockVersion, texts });
    setSavedLockVersion(saved.lock_version);
    void refreshAll();
  };
}
