"use client";

import { useCallback, useState } from "react";
import type { DocumentRetries } from "./types";
import { useReprocessDocument } from "./use-documents";

const NO_IDS: ReadonlySet<string> = new Set();

function withId(ids: ReadonlySet<string>, id: string): ReadonlySet<string> {
  return new Set(ids).add(id);
}

function withoutId(ids: ReadonlySet<string>, id: string): ReadonlySet<string> {
  const next = new Set(ids);
  next.delete(id);
  return next;
}

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
