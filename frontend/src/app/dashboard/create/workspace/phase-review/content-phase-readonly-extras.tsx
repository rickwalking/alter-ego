"use client";

import { useTranslations } from "next-intl";
import {
  INSIGHT_QUOTE_EXTRA_KEY,
  isPresentationStructuredItemList,
  listPresentationIconNames,
  parsePresentationInsightQuote,
  PresentationIconPreview,
  PresentationInsightQuoteCard,
  PresentationStructuredItems,
} from "@/modules/editorial";

/** Extras with a translated label (any other key shows its raw name). */
const LABELLED_EXTRAS: ReadonlySet<string> = new Set([
  "tldr_strip",
  "creator_name",
  "creator_handle",
  "creator_website",
]);

/** AE-0414: "Nome do criador" instead of "Campo estruturado: creator_name". */
export function useStructuredExtraLabel(): (extraKey: string) => string {
  const t = useTranslations("editorialWorkflow.review");
  return (extraKey: string): string =>
    LABELLED_EXTRAS.has(extraKey)
      ? t(`copyField.extraLabels.${extraKey}`)
      : t("structuredExtra", { field: extraKey });
}

function formatStructuredValue(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function ReadOnlyExtraValue({
  value,
}: Readonly<{ value: unknown }>): React.ReactElement {
  const tCopy = useTranslations("editorialWorkflow.review.copyField");
  if (isPresentationStructuredItemList(value)) {
    return <PresentationStructuredItems items={value} />;
  }
  if (typeof value === "string") {
    // AE-0414: an empty value says so instead of showing a bare label.
    return (
      <p className="whitespace-pre-wrap text-[var(--color-text-muted)] text-xs">
        {value.trim() ? value : tCopy("emptyValue")}
      </p>
    );
  }
  return (
    <pre className="whitespace-pre-wrap font-mono text-[var(--color-text-muted)] text-xs">
      {formatStructuredValue(value)}
    </pre>
  );
}

/** AE-0407: a ``pov_news`` insight renders as a quote card, never raw JSON. */
export function ReadOnlyExtra({
  extraKey,
  value,
}: Readonly<{
  extraKey: string;
  value: unknown;
}>): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const extraLabel = useStructuredExtraLabel();
  const quote =
    extraKey === INSIGHT_QUOTE_EXTRA_KEY
      ? parsePresentationInsightQuote(value)
      : null;
  return (
    <div>
      <p className="font-medium text-[var(--color-text-muted)] text-xs">
        {quote ? t("insightQuoteLabel") : extraLabel(extraKey)}
      </p>
      {quote ? (
        <PresentationInsightQuoteCard insight={quote} />
      ) : (
        <ReadOnlyExtraValue value={value} />
      )}
    </div>
  );
}

export function IconRow({
  presentation,
  localeLabel,
}: Readonly<{
  presentation: Record<string, unknown>;
  localeLabel: string;
}>): React.ReactElement | null {
  const iconNames = listPresentationIconNames(presentation);
  if (iconNames.length === 0) {
    return null;
  }
  return (
    <div className="flex flex-wrap items-center gap-2 pt-1">
      {iconNames.map((iconName) => (
        <div
          key={`${localeLabel}-${iconName}`}
          className="inline-flex items-center gap-1 rounded border border-[var(--color-border)] px-2 py-1 text-xs"
        >
          <PresentationIconPreview
            iconName={iconName}
            className="h-3.5 w-3.5 text-[var(--color-text)]"
          />
          <span className="font-mono text-[var(--color-text-muted)]">
            {iconName}
          </span>
        </div>
      ))}
    </div>
  );
}
