"use client";

import { useTranslations } from "next-intl";
import { QUOTE_SOURCE_PLATFORM } from "@/modules/editorial/workspace/lib/presentation-insight-quote";
import type { PresentationInsightQuoteCardProps } from "./types";

/** Read-only ``pov_news`` quote card (quote, name, ``@handle · X``). */
export function PresentationInsightQuoteCard({
  insight,
}: Readonly<PresentationInsightQuoteCardProps>): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  return (
    <figure
      aria-label={t("insightQuoteAria", { name: insight.name })}
      className="space-y-1 rounded-md border border-[var(--color-border)] p-2"
    >
      <blockquote className="whitespace-pre-wrap text-[var(--color-text)] text-xs italic">
        {insight.quote}
      </blockquote>
      <figcaption className="text-[var(--color-text-muted)] text-xs">
        <span className="font-medium text-[var(--color-text)]">
          {insight.name}
        </span>{" "}
        <span>
          {t("insightQuoteSource", {
            handle: insight.handle,
            platform: QUOTE_SOURCE_PLATFORM,
          })}
        </span>
      </figcaption>
    </figure>
  );
}
