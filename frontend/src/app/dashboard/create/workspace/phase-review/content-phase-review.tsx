"use client";

import { useMemo } from "react";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import { useTranslations } from "next-intl";

import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
} from "@/modules/publishing";
import {
  addressViolations,
  changedLocalizedSlides,
  hasBlockingContentGateValidation,
  hasBlockingPresentationViolations,
  listContentReviewViolations,
  resolveLocalizedSlides,
  slidesHaveCopyChanges,
  useSlideFieldErrors,
} from "@/modules/editorial";

import { ContentViolationList } from "./content-phase-violations";
import { contentEditHandlers } from "./content-edit-handlers";
import { useManualFixSubmission } from "./use-manual-fix-submission";
import {
  ContentReviewHeader,
  ContentSlideRow,
} from "./content-phase-review-parts";
import {
  ManualFixesFooter,
  type ContentManualFixesActions,
} from "./content-phase-manual-fixes";

export type { ContentManualFixesActions } from "./content-phase-manual-fixes";

export interface ContentPhaseReviewProps {
  state: EditorialWorkflowState;
  editable?: boolean;
  slides?: LocalizedSlideReview[];
  onSlidesChange?: (slides: LocalizedSlideReview[]) => void;
  manualFixes?: ContentManualFixesActions;
}

/** Whether the content gate, or any presentation check, blocks approval. */
function approvalBlocks(state: EditorialWorkflowState): {
  contentGateBlocked: boolean;
  approvalBlocked: boolean;
} {
  const contentGateBlocked = hasBlockingContentGateValidation(state);
  return {
    contentGateBlocked,
    approvalBlocked:
      contentGateBlocked || hasBlockingPresentationViolations(state),
  };
}

/** One validation run of the content gate (a resume bumps ``lock_version``). */
function validationStamp(state: EditorialWorkflowState): string {
  return [
    state.lock_version ?? "",
    state.presentation_validation?.validated_at ?? "",
    state.content_gate_validation?.validated_at ?? "",
  ].join("|");
}

export function ContentPhaseReview({
  state,
  editable = false,
  slides: controlledSlides,
  onSlidesChange,
  manualFixes,
}: ContentPhaseReviewProps): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const baselineSlides = useMemo(() => resolveLocalizedSlides(state), [state]);
  const localizedSlides = controlledSlides ?? baselineSlides;
  // AE-0309: merge violations arriving in the content interrupt/gate payload
  // with the presentation validation ones (de-duplicated).
  const violations = useMemo(() => listContentReviewViolations(state), [state]);
  const addressed = useMemo(() => addressViolations(violations), [violations]);
  const errors = useSlideFieldErrors(addressed, validationStamp(state));
  const { contentGateBlocked, approvalBlocked } = approvalBlocks(state);
  const hasChanges = slidesHaveCopyChanges(baselineSlides, localizedSlides);

  const handlers =
    editable && onSlidesChange
      ? contentEditHandlers(localizedSlides, onSlidesChange, errors.clearField)
      : null;

  const submitManualFixes = useManualFixSubmission(manualFixes, {
    addressed,
    runInProgress: state.phase_status === WORKFLOW_PHASE_STATUS.IN_PROGRESS,
    changedSlides: () =>
      changedLocalizedSlides(baselineSlides, localizedSlides),
  });

  if (localizedSlides.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-[var(--color-border)] p-3 text-[var(--color-text-muted)] text-sm">
        {t("emptyPhase")}
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
      <ContentReviewHeader
        policyVersion={state.presentation_policy_version}
        imagePrompts={state.slide_image_prompts}
        contentGateBlocked={contentGateBlocked}
        approvalBlocked={approvalBlocked}
      />

      <ContentViolationList violations={addressed} />

      <div className="space-y-3">
        {localizedSlides.map((slide) => {
          return (
            <ContentSlideRow
              key={`${slide.slide_index}-${slide.slide_type}`}
              slide={slide}
              policyVersion={state.presentation_policy_version}
              errors={errors}
              handlers={handlers}
            />
          );
        })}
      </div>

      {/* AE-0437: unsaved edits can always be saved without approving, also
          when the server is no longer blocking (prod carousel 5344b6c6: a
          late-added EN TL;DR edit could only be sent by approving). */}
      {handlers && manualFixes && (approvalBlocked || hasChanges) ? (
        <ManualFixesFooter
          errors={errors}
          blocked={approvalBlocked}
          canSubmit={hasChanges}
          manualFixes={manualFixes}
          onSubmit={submitManualFixes}
        />
      ) : null}
    </div>
  );
}
