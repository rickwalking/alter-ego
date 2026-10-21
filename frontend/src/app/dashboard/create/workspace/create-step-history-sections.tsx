"use client";

import { useTranslations } from "next-intl";
import { ContentPhaseReview } from "@/app/dashboard/create/workspace/phase-review/content-phase-review";
import { TEXT_DIM } from "@/constants/neon";
import type { EditorialWorkflowState } from "@/modules/publishing";
import {
  resolveLocalizedSlides,
  resolveSlideDraftPreview,
  resolveSlideDraftTitle,
} from "@/modules/editorial";

const TITLE_COLOR = "rgba(255,255,255,0.88)";

/** What one step's read-only history view receives. */
export interface StepHistorySectionProps {
  state: EditorialWorkflowState;
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function outlineTitle(
  slide: Record<string, unknown>,
  fallback: string,
): string {
  return asString(slide.title) || asString(slide.heading) || fallback;
}

export function StepHistoryEmpty(): React.JSX.Element {
  const t = useTranslations("create.stepHistory");
  return (
    <p className="text-sm" style={{ color: TEXT_DIM }}>
      {t("empty")}
    </p>
  );
}

export function ResearchHistory({
  state,
}: Readonly<StepHistorySectionProps>): React.JSX.Element {
  const t = useTranslations("create.stepHistory");
  const findings = state.research_findings;
  return (
    <div className="space-y-2 text-sm" style={{ color: TEXT_DIM }}>
      <p className="font-medium" style={{ color: TITLE_COLOR }}>
        {t("researchTitle", { count: findings.length })}
      </p>
      <ul className="list-disc space-y-1 pl-5">
        {findings.map((item, index) => (
          <li key={`finding-${index}`}>
            {asString(item.source) || t("untitledSlide")}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function OutlineHistory({
  state,
}: Readonly<StepHistorySectionProps>): React.JSX.Element {
  const t = useTranslations("create.stepHistory");
  const outline = state.outline;
  return (
    <div className="space-y-2 text-sm" style={{ color: TEXT_DIM }}>
      <p className="font-medium" style={{ color: TITLE_COLOR }}>
        {t("outlineTitle", { count: outline.length })}
      </p>
      <ol className="list-decimal space-y-2 pl-5">
        {outline.map((slide, index) => (
          <li key={`outline-${index}`}>
            <span style={{ color: TITLE_COLOR }}>
              {outlineTitle(slide, t("untitledSlide"))}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** The localized review when present, else the raw slide drafts. */
export function ContentHistory({
  state,
}: Readonly<StepHistorySectionProps>): React.JSX.Element {
  const t = useTranslations("create.stepHistory");
  const localizedSlides = resolveLocalizedSlides(state);
  if (localizedSlides.length > 0) {
    return (
      <ContentPhaseReview
        state={state}
        editable={false}
        slides={localizedSlides}
      />
    );
  }
  const drafts = state.slide_drafts;
  return (
    <div className="space-y-2 text-sm" style={{ color: TEXT_DIM }}>
      <p className="font-medium" style={{ color: TITLE_COLOR }}>
        {t("contentTitle", { count: drafts.length })}
      </p>
      <ol className="list-decimal space-y-3 pl-5">
        {drafts.map((slide, index) => {
          const record = slide;
          const text = resolveSlideDraftPreview(record);
          return (
            <li key={`draft-${index}`}>
              <p className="font-medium" style={{ color: TITLE_COLOR }}>
                {resolveSlideDraftTitle(record, t("untitledSlide"))}
              </p>
              {text ? <p className="mt-1 whitespace-pre-wrap">{text}</p> : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function ImagesHistory({
  state,
}: Readonly<StepHistorySectionProps>): React.JSX.Element {
  const t = useTranslations("create.stepHistory");
  const count = state.image_assets?.length ?? 0;
  return (
    <p className="text-sm" style={{ color: TEXT_DIM }}>
      {t("imagesTitle", { count })}
      {state.design_applied ? ` · ${t("designApplied")}` : ""}
    </p>
  );
}

export function ReviewHistory(): React.JSX.Element {
  const t = useTranslations("create.stepHistory");
  return (
    <p className="text-sm" style={{ color: TEXT_DIM }}>
      {t("reviewHint")}
    </p>
  );
}

function PublishText({
  label,
  text,
}: Readonly<{
  label: string;
  text: string;
}>): React.JSX.Element | null {
  if (!text.trim()) {
    return null;
  }
  return (
    <div>
      <p className="font-medium" style={{ color: TITLE_COLOR }}>
        {label}
      </p>
      <p className="mt-1 whitespace-pre-wrap">{text}</p>
    </div>
  );
}

export function PublishHistory({
  state,
}: Readonly<StepHistorySectionProps>): React.JSX.Element {
  const t = useTranslations("create.stepHistory");
  const caption = state.caption ?? "";
  const linkedinPt = state.linkedin_post_pt ?? "";
  if (!caption.trim() && !linkedinPt.trim()) {
    return (
      <p className="text-sm" style={{ color: TEXT_DIM }}>
        {t("publishEmpty")}
      </p>
    );
  }
  return (
    <div className="space-y-2 text-sm" style={{ color: TEXT_DIM }}>
      <PublishText label={t("publishCaptionLabel")} text={caption} />
      <PublishText label={t("publishLinkedInLabel")} text={linkedinPt} />
    </div>
  );
}
