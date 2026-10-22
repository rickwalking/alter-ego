"use client";
import {
  NeonCard,
  NeonCardContent,
  NeonCardHeader,
  NeonCardTitle,
} from "@/components/molecules/neon-card";
import { NeonBadge } from "@/components/atoms/neon-badge";

import { useState } from "react";
import { FileText, RotateCcw, Trash2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { formatDate } from "@/lib/utils";
import {
  type DocumentCardProps,
  type DocumentRetryButtonProps,
  type DocumentStateRowProps,
} from "./types";
import {
  failureReasonKey,
  isKnownStatus,
  isStaleDocument,
  needsRetry,
} from "./document-state";

/** Status badge, failure reason and the stale notice of a document. */
function DocumentStateRow({
  document,
  now,
  badgeClassName,
}: Readonly<DocumentStateRowProps>): React.ReactElement {
  const t = useTranslations("knowledge.document");
  const statusLabel = isKnownStatus(document.status)
    ? t(`status.${document.status}`)
    : document.status;
  const failureReason = document.error_message
    ? t(`failure.${failureReasonKey(document.error_message)}`)
    : null;
  return (
    <>
      <NeonBadge variant="secondary" className={`text-xs ${badgeClassName}`}>
        {statusLabel}
      </NeonBadge>
      {failureReason && (
        <span
          className="text-xs text-[var(--color-destructive)] truncate"
          title={failureReason}
        >
          {failureReason}
        </span>
      )}
      {isStaleDocument(document, now) && (
        <span className="text-xs text-[var(--color-destructive)]">
          {t("stale")}
        </span>
      )}
    </>
  );
}

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

export function DocumentCard({
  document,
  onDelete,
  onRetry,
  retrying = false,
  retryFailed = false,
}: Readonly<DocumentCardProps>) {
  const locale = useLocale();
  const t = useTranslations("knowledge.document");
  const [now] = useState(Date.now);
  const meta = document.metadata as Record<string, unknown> | undefined;
  const tags = (meta?.tags as string[] | undefined) ?? [];
  const statusColors: Record<string, string> = {
    completed:
      "bg-success/20 text-success dark:bg-success/30 dark:text-success-foreground",
    processing: "bg-warning/20 text-warning-foreground dark:bg-warning/30",
    pending: "bg-info/20 text-info-foreground dark:bg-info/30",
    failed:
      "bg-destructive/20 text-destructive-foreground dark:bg-destructive/30",
  };

  return (
    <NeonCard className="transition-shadow hover:shadow-md">
      <NeonCardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--color-primary)]/10 text-[var(--color-primary)]">
              <FileText className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="flex-1 min-w-0">
              <NeonCardTitle className="text-lg truncate">
                {document.title}
              </NeonCardTitle>
              <div className="flex items-center gap-2 text-xs text-[var(--color-muted-foreground)] mt-1">
                <span>{formatDate(document.created_at, locale)}</span>
                <span>·</span>
                <span>{t("chunks", { count: document.chunk_count })}</span>
              </div>
            </div>
          </div>
          {onDelete && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="shrink-0 rounded-md p-1.5 text-[var(--color-muted-foreground)] hover:bg-[var(--color-destructive)]/10 hover:text-[var(--color-destructive)] transition-colors"
              aria-label={t("delete", { title: document.title })}
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </button>
          )}
        </div>
      </NeonCardHeader>
      <NeonCardContent>
        <div className="flex items-center gap-2 mb-3">
          <DocumentStateRow
            document={document}
            now={now}
            badgeClassName={statusColors[document.status] ?? ""}
          />
        </div>
        {onRetry && needsRetry(document, now) && (
          <DocumentRetryButton
            onRetry={onRetry}
            retrying={retrying}
            retryFailed={retryFailed}
          />
        )}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {tags.map((tag) => (
              <NeonBadge key={tag} variant="secondary" className="text-xs">
                {tag}
              </NeonBadge>
            ))}
          </div>
        )}
      </NeonCardContent>
    </NeonCard>
  );
}
