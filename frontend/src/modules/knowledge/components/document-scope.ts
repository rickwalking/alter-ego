import {
  DOCUMENT_SCOPE,
  type DocumentScopeChoice,
} from "@/constants/knowledge";

const CHOICES: readonly DocumentScopeChoice[] = [
  DOCUMENT_SCOPE.PERSONAL,
  DOCUMENT_SCOPE.PUBLIC,
];

/**
 * A document's scope as the owner can choose it, or `null` for a system scope
 * (carousel, internal), which the owner can neither pick nor leave.
 */
export function scopeChoiceOf(scope: string): DocumentScopeChoice | null {
  return CHOICES.find((choice) => choice === scope) ?? null;
}

/** The scope a document's switch moves it to. */
export function otherScope(scope: DocumentScopeChoice): DocumentScopeChoice {
  return scope === DOCUMENT_SCOPE.PUBLIC
    ? DOCUMENT_SCOPE.PERSONAL
    : DOCUMENT_SCOPE.PUBLIC;
}
