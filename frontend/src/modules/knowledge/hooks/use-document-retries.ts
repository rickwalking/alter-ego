"use client";

import { useCallback, useState } from "react";
import type { DocumentRetries } from "./types";
import { NO_IDS, withId, withoutId } from "./id-sets";
import { useReprocessDocument } from "./use-documents";

/**
 * Reprocesses documents and tracks each one on its own: retrying A then B
 * keeps A disabled until A's own request settles, and a failed request marks
 * only its document.
 */
export function useDocumentRetries(): DocumentRetries {
  const { mutateAsync } = useReprocessDocument();
  const [retryingIds, setRetryingIds] = useState(NO_IDS);
  const [retryFailedIds, setRetryFailedIds] = useState(NO_IDS);

  const retry = useCallback(
    (id: string) => {
      setRetryingIds((ids) => withId(ids, id));
      setRetryFailedIds((ids) => withoutId(ids, id));
      void mutateAsync(id)
        .catch(() => setRetryFailedIds((ids) => withId(ids, id)))
        .finally(() => setRetryingIds((ids) => withoutId(ids, id)));
    },
    [mutateAsync],
  );

  return { retryingIds, retryFailedIds, retry };
}
