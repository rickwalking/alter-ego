"use client";

import { useTranslations } from "next-intl";
import { ContentPhaseReview } from "@/app/dashboard/create/workspace/phase-review/content-phase-review";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import { TEXT_DIM } from "@/constants/neon";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import {
  resolveLocalizedSlides,
  resolveSlideDraftPreview,
  resolveSlideDraftTitle,
} from "@/features/create/lib/presentation-review-utils";
import {
  CREATE_STEP_IDS,
  CREATE_STEP_TO_EDITORIAL_PHASE,
  type CreateStepId,
} from "@/app/dashboard/create/step-ids";

interface CreateStepHistoryPanelProps {
  viewStepId: CreateStepId;
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

export function CreateStepHistoryPanel({
  viewStepId,
  state,
}: CreateStepHistoryPanelProps): React.JSX.Element {
  const t = useTranslations("create.stepHistory");
  const untitled = t("untitledSlide");
  const phase = CREATE_STEP_TO_EDITORIAL_PHASE[viewStepId];

  if (viewStepId === CREATE_STEP_IDS.RESEARCH) {
    const findings = state.research_findings ?? [];
    return (
      <div className="space-y-2 text-sm" style={{ color: TEXT_DIM }}>
        <p className="font-medium" style={{ color: "rgba(255,255,255,0.88)" }}>
          {t("researchTitle", { count: findings.length })}
        </p>
        <ul className="list-disc space-y-1 pl-5">
          {findings.map((item, index) => (
            <li key={`finding-${index}`}>
              {asString((item as Record<string, unknown>).source) || untitled}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  if (viewStepId === CREATE_STEP_IDS.OUTLINE) {
    const outline = state.outline ?? [];
    return (
      <div className="space-y-2 text-sm" style={{ color: TEXT_DIM }}>
        <p className="font-medium" style={{ color: "rgba(255,255,255,0.88)" }}>
          {t("outlineTitle", { count: outline.length })}
        </p>
        <ol className="list-decimal space-y-2 pl-5">
          {outline.map((slide, index) => {
            const record = slide as Record<string, unknown>;
            return (
              <li key={`outline-${index}`}>
                <span style={{ color: "rgba(255,255,255,0.88)" }}>
                  {outlineTitle(record, untitled)}
                </span>
              </li>
            );
          })}
        </ol>
      </div>
    );
  }

  if (viewStepId === CREATE_STEP_IDS.CONTENT) {
    const localizedSlides = resolveLocalizedSlides(state);
    if (localizedSlides.length > 0) {
      return <ContentPhaseReview state={state} editable={false} slides={localizedSlides} />;
    }

    const drafts = state.slide_drafts ?? [];
    return (
      <div className="space-y-2 text-sm" style={{ color: TEXT_DIM }}>
        <p className="font-medium" style={{ color: "rgba(255,255,255,0.88)" }}>
          {t("contentTitle", { count: drafts.length })}
        </p>
        <ol className="list-decimal space-y-3 pl-5">
          {drafts.map((slide, index) => {
            const record = slide as Record<string, unknown>;
            const text = resolveSlideDraftPreview(record);
            return (
              <li key={`draft-${index}`}>
                <p
                  className="font-medium"
                  style={{ color: "rgba(255,255,255,0.88)" }}
                >
                  {resolveSlideDraftTitle(record, untitled)}
                </p>
                {text ? (
                  <p className="mt-1 whitespace-pre-wrap">{text}</p>
                ) : null}
              </li>
            );
          })}
        </ol>
      </div>
    );
  }

  if (viewStepId === CREATE_STEP_IDS.IMAGES) {
    const count = state.image_assets?.length ?? 0;
    return (
      <p className="text-sm" style={{ color: TEXT_DIM }}>
        {t("imagesTitle", { count })}
        {state.design_applied ? ` · ${t("designApplied")}` : ""}
      </p>
    );
  }

  if (
    viewStepId === CREATE_STEP_IDS.REVIEW &&
    phase === EDITORIAL_PHASES.FINAL_REVIEW
  ) {
    return (
      <p className="text-sm" style={{ color: TEXT_DIM }}>
        {t("reviewHint")}
      </p>
    );
  }

  if (viewStepId === CREATE_STEP_IDS.PUBLISH) {
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
        {caption.trim() ? (
          <div>
            <p
              className="font-medium"
              style={{ color: "rgba(255,255,255,0.88)" }}
            >
              {t("publishCaptionLabel")}
            </p>
            <p className="mt-1 whitespace-pre-wrap">{caption}</p>
          </div>
        ) : null}
        {linkedinPt.trim() ? (
          <div>
            <p
              className="font-medium"
              style={{ color: "rgba(255,255,255,0.88)" }}
            >
              {t("publishLinkedInLabel")}
            </p>
            <p className="mt-1 whitespace-pre-wrap">{linkedinPt}</p>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <p className="text-sm" style={{ color: TEXT_DIM }}>
      {t("empty")}
    </p>
  );
}
