"use client";

import { useCallback, useState } from "react";
import type { DocumentScopeChoice } from "@/constants/knowledge";
import { NO_IDS, withId, withoutId } from "./id-sets";
import type { DocumentScopeChange } from "./types";
import { useChangeDocumentScope } from "./use-documents";

/**
 * Changes document scopes and tracks each document on its own: switching A
 * then B keeps A disabled until A's own request settles, and a failed request
 * marks only its document.
 */
export function useDocumentScopeChange(): DocumentScopeChange {
  const { mutateAsync } = useChangeDocumentScope();
  const [changingScopeIds, setChangingScopeIds] = useState(NO_IDS);
  const [scopeChangeFailedIds, setScopeChangeFailedIds] = useState(NO_IDS);

  const changeScope = useCallback(
    (id: string, scope: DocumentScopeChoice) => {
      setChangingScopeIds((ids) => withId(ids, id));
      setScopeChangeFailedIds((ids) => withoutId(ids, id));
      void mutateAsync({ id, scope })
        .catch(() => setScopeChangeFailedIds((ids) => withId(ids, id)))
        .finally(() => setChangingScopeIds((ids) => withoutId(ids, id)));
    },
    [mutateAsync],
  );

  return { changeScope, changingScopeIds, scopeChangeFailedIds };
}
