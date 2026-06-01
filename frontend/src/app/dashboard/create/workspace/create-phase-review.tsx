"use client";

import { useTranslations } from "next-intl";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import { CreateFinalReviewTabs } from "./create-final-review-tabs";
import {
  asString,
  draftText,
  outlineTitle,
} from "./create-phase-review-helpers";

interface EditorialPhaseReviewProps {
  projectId: string;
  state: EditorialWorkflowState;
}

export function CreatePhaseReview({
  projectId,
  state,
}: EditorialPhaseReviewProps): React.JSX.Element | null {
  const t = useTranslations("editorialWorkflow.review");
  const untitledSlide = t("untitledSlide");
  const phase = state.current_phase;

  if (
    phase === EDITORIAL_PHASES.RESEARCH &&
    state.research_findings.length > 0
  ) {
    return (
      <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
        <p className="font-medium">{t("researchTitle")}</p>
        <ul className="space-y-2">
          {state.research_findings.map((finding, index) => {
            const source =
              asString(finding.source) ||
              t("findingFallback", { index: index + 1 });
            const points = Array.isArray(finding.key_points)
              ? finding.key_points.filter(
                  (p): p is string => typeof p === "string",
                )
              : [];
            return (
              <li key={source} className="space-y-1">
                <p className="font-medium text-[var(--color-text)]">{source}</p>
                {points.length > 0 ? (
                  <ul className="list-disc space-y-0.5 pl-4 text-[var(--color-text-muted)]">
                    {points.map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                ) : null}
              </li>
            );
          })}
        </ul>
      </div>
    );
  }

  if (phase === EDITORIAL_PHASES.OUTLINE && state.outline.length > 0) {
    return (
      <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
        <p className="font-medium">{t("outlineTitle")}</p>
        <ol className="list-decimal space-y-2 pl-4">
          {state.outline.map((slide, index) => {
            const title = outlineTitle(slide, untitledSlide);
            const key = `${asString(slide.slide_index) || index}-${title}`;
            const points = Array.isArray(slide.key_points)
              ? slide.key_points.filter(
                  (p): p is string => typeof p === "string",
                )
              : [];
            return (
              <li key={key} className="space-y-0.5">
                <p className="font-medium text-[var(--color-text)]">{title}</p>
                {points.length > 0 ? (
                  <p className="text-[var(--color-text-muted)] text-xs">
                    {points.join(" · ")}
                  </p>
                ) : null}
              </li>
            );
          })}
        </ol>
      </div>
    );
  }

  if (phase === EDITORIAL_PHASES.CONTENT && state.slide_drafts.length > 0) {
    return (
      <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
        <p className="font-medium">{t("contentTitle")}</p>
        <div className="space-y-3">
          {state.slide_drafts.map((slide, index) => {
            const title = outlineTitle(slide, untitledSlide);
            const text = draftText(slide);
            const key = `${asString(slide.slide_index) || index}-${title}`;
            return (
              <div
                key={key}
                className="space-y-1 border-[var(--color-border)] border-b pb-2 last:border-0"
              >
                <p className="font-medium text-[var(--color-text)]">{title}</p>
                {text ? (
                  <p className="whitespace-pre-wrap text-[var(--color-text-muted)] text-xs">
                    {text}
                  </p>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (phase === EDITORIAL_PHASES.DESIGN) {
    return (
      <div className="space-y-3 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
        <p className="font-medium">{t("designTitle")}</p>
        <p className="text-[var(--color-text-muted)]">
          {state.design_applied ? t("designReady") : t("designPending")}
        </p>
        {state.outline.length > 0 ? (
          <div className="space-y-2">
            <p className="font-medium text-[var(--color-text)] text-xs uppercase tracking-wide">
              {t("outlineTitle")}
            </p>
            <ol className="list-decimal space-y-1 pl-4 text-[var(--color-text-muted)]">
              {state.outline.map((slide, index) => {
                const title = outlineTitle(slide, untitledSlide);
                return <li key={`${index}-${title}`}>{title}</li>;
              })}
            </ol>
          </div>
        ) : null}
        {state.slide_drafts.length > 0 ? (
          <div className="space-y-2">
            <p className="font-medium text-[var(--color-text)] text-xs uppercase tracking-wide">
              {t("contentTitle")}
            </p>
            {state.slide_drafts.slice(0, 3).map((slide, index) => {
              const text = draftText(slide);
              if (!text) return null;
              return (
                <p
                  key={`draft-${index}`}
                  className="line-clamp-3 text-[var(--color-text-muted)] text-xs"
                >
                  {text}
                </p>
              );
            })}
          </div>
        ) : null}
      </div>
    );
  }

  if (
    phase === EDITORIAL_PHASES.IMAGES &&
    (state.image_assets?.length ?? 0) > 0
  ) {
    return (
      <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
        <p className="font-medium">{t("imagesTitle")}</p>
        <ul className="list-disc space-y-1 pl-4 text-[var(--color-text-muted)]">
          {state.image_assets?.map((asset) => (
            <li key={asset} className="break-all font-mono text-xs">
              {asset}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  if (phase === EDITORIAL_PHASES.FINAL_REVIEW) {
    return <CreateFinalReviewTabs projectId={projectId} state={state} />;
  }

  if (
    phase === EDITORIAL_PHASES.OUTLINE ||
    phase === EDITORIAL_PHASES.CONTENT
  ) {
    return (
      <div className="rounded-md border border-dashed border-[var(--color-border)] p-3 text-[var(--color-text-muted)] text-sm">
        {t("emptyPhase")}
      </div>
    );
  }

  return null;
}
