"use client";

import { useCallback } from "react";
import type { DocumentScopeChoice } from "@/constants/knowledge";
import type { DocumentScopeChange } from "./types";
import { useChangeDocumentScope } from "./use-documents";

/** Changes a document's scope and names the document in flight or failed. */
export function useDocumentScopeChange(): DocumentScopeChange {
  const { mutate, isPending, isError, variables } = useChangeDocumentScope();
  const changeScope = useCallback(
    (id: string, scope: DocumentScopeChoice) => mutate({ id, scope }),
    [mutate],
  );
  const id = variables?.id ?? null;
  return {
    changeScope,
    changingScopeId: isPending ? id : null,
    scopeChangeFailedId: isError ? id : null,
  };
}
