"use client";

import { RotateCcw } from "lucide-react";
import { useTranslations } from "next-intl";

import { needsRetry } from "./document-state";
import { otherScope, scopeChoiceOf } from "./document-scope";
import { ScopeSwitch } from "./scope-parts";
import type {
  DocumentCardActionsProps,
  DocumentRetryButtonProps,
} from "./types";

/** Reprocess a failed or stuck document. */
function DocumentRetryButton({
  onRetry,
  retrying,
  retryFailed,
}: Readonly<DocumentRetryButtonProps>): React.ReactElement {
  const t = useTranslations("knowledge.document");
  return (
    <>
      {retryFailed && (
        <p
          role="alert"
          className="mb-2 text-xs text-[var(--color-destructive)]"
        >
          {t("retryFailed")}
        </p>
      )}
      <button
        type="button"
        onClick={onRetry}
        disabled={retrying}
        className="mb-3 inline-flex items-center gap-1.5 rounded-md border border-[var(--color-border)] px-2.5 py-1 text-xs font-medium hover:bg-[var(--color-primary)]/10 disabled:opacity-50"
      >
        <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
        {retrying ? t("retrying") : t("retry")}
      </button>
    </>
  );
}

/** Retry (when the document needs it) and the scope switch of a card. */
export function DocumentCardActions({
  document,
  now,
  onRetry,
  retrying = false,
  retryFailed = false,
  onChangeScope,
  changingScope = false,
  scopeChangeFailed = false,
}: Readonly<DocumentCardActionsProps>): React.ReactElement {
  return (
    <>
      {onRetry && needsRetry(document, now) && (
        <DocumentRetryButton
          onRetry={onRetry}
          retrying={retrying}
          retryFailed={retryFailed}
        />
      )}
      {onChangeScope && (
        <ScopeSwitch
          scope={document.scope}
          onSwitch={() =>
            onChangeScope(otherScope(scopeChoiceOf(document.scope)))
          }
          changing={changingScope}
          failed={scopeChangeFailed}
        />
      )}
    </>
  );
}
