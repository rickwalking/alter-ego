"use client";

import { useTranslations } from "next-intl";

import { NeonButton } from "@/components/atoms/neon-button";

import {
  BlockingSlidesNotice,
  focusInvalidField,
  type SlideFieldErrorState,
} from "@/modules/editorial";
import type { LocalizedSlideReview } from "@/modules/publishing";
import { CONTENT_REVIEW_ID_PREFIX } from "./content-phase-locale-fields";

/**
 * AE-0403: "submit manual fixes" at the content gate. Saves the edits through
 * an edits-only revise (apply + re-validate + re-interrupt); it never approves.
 * AE-0414 (B04): ``onSubmit`` receives only the slides the reviewer changed,
 * each exactly as edited (never clamped to a budget).
 */
export interface ContentManualFixesActions {
  onSubmit: (slides: LocalizedSlideReview[]) => void;
  submitting?: boolean;
}

export interface ManualFixesFooterProps {
  errors: SlideFieldErrorState;
  /** The server still blocks approval (shows the blocking-slides hint). */
  blocked: boolean;
  canSubmit: boolean;
  manualFixes: ContentManualFixesActions;
  onSubmit: () => void;
}

export function ManualFixesFooter({
  errors,
  blocked,
  canSubmit,
  manualFixes,
  onSubmit,
}: ManualFixesFooterProps): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  return (
    <div className="space-y-2 rounded-md border border-destructive/30 p-3">
      {blocked ? (
        <BlockingSlidesNotice
          message={t("fieldErrors.manualFixesHint")}
          slideIndexes={errors.slideIndexes}
          onSelectSlide={(slideIndex) =>
            focusInvalidField(
              CONTENT_REVIEW_ID_PREFIX,
              errors.fieldErrors,
              slideIndex,
            )
          }
        />
      ) : null}
      <NeonButton
        size="sm"
        disabled={!canSubmit || manualFixes.submitting === true}
        onClick={onSubmit}
      >
        {manualFixes.submitting === true
          ? t("fieldErrors.submittingManualFixes")
          : t("fieldErrors.submitManualFixes")}
      </NeonButton>
    </div>
  );
}
