import {
  DOCUMENT_SCOPE,
  type DocumentScopeChoice,
} from "@/constants/knowledge";

/** A document's scope as the owner sees it: public, or personal for any other. */
export function scopeChoiceOf(scope: string): DocumentScopeChoice {
  return scope === DOCUMENT_SCOPE.PUBLIC
    ? DOCUMENT_SCOPE.PUBLIC
    : DOCUMENT_SCOPE.PERSONAL;
}

/** The scope a document's switch moves it to. */
export function otherScope(scope: DocumentScopeChoice): DocumentScopeChoice {
  return scope === DOCUMENT_SCOPE.PUBLIC
    ? DOCUMENT_SCOPE.PERSONAL
    : DOCUMENT_SCOPE.PUBLIC;
}
