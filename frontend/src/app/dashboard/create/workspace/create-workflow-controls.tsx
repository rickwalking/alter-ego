"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import type { CreateWorkflowControlsProps } from "@/modules/editorial";
import {
  ControlNotices,
  FeedbackFields,
} from "./create-workflow-control-parts";

/** Approving the content step sends the edited slides along. */
function approveOptionsFor(
  state: CreateWorkflowControlsProps["state"],
  contentHasEdits: boolean,
  contentSlides: CreateWorkflowControlsProps["contentSlides"],
): { editedLocalizedSlides: typeof contentSlides } | undefined {
  return state?.current_phase === EDITORIAL_PHASES.CONTENT && contentHasEdits
    ? { editedLocalizedSlides: contentSlides }
    : undefined;
}

export function CreateWorkflowControls({
  state,
  showLiveControls,
  loading,
  feedback,
  setFeedback,
  feedbackError,
  setFeedbackError,
  sendBackTarget,
  setSendBackTarget,
  handleRevise,
  approve,
  contentHasEdits,
  contentSlides,
  personaApproveBlocked,
  personaShortfallDetail,
  presentationApproveBlocked,
  editBudgetBlocked,
  designReviseBlocked,
  showPublishLink,
}: CreateWorkflowControlsProps): React.JSX.Element {
  const t = useTranslations("editorialWorkflow");
  const isFinalReviewGate =
    state?.current_phase === EDITORIAL_PHASES.FINAL_REVIEW;
  const approveBlocked =
    personaApproveBlocked || presentationApproveBlocked || editBudgetBlocked;

  return (
    <div className="space-y-2 text-sm">
      {showLiveControls && (
        <FeedbackFields
          feedback={feedback}
          setFeedback={setFeedback}
          feedbackError={feedbackError}
          setFeedbackError={setFeedbackError}
          sendBackTarget={sendBackTarget}
          setSendBackTarget={setSendBackTarget}
          isFinalReviewGate={isFinalReviewGate}
        />
      )}
      <div className="flex flex-col gap-2">
        {loading && (
          <p
            className="text-xs"
            role="status"
            style={{ color: "rgba(255,255,255,0.55)" }}
          >
            {t("actions.processing")}
          </p>
        )}
        <div className="flex gap-2">
          <NeonButton
            size="sm"
            disabled={loading || !showLiveControls || approveBlocked}
            onClick={() => {
              void approve(
                approveOptionsFor(state, contentHasEdits, contentSlides),
              );
            }}
          >
            {t("actions.approve")}
          </NeonButton>
          <NeonButton
            size="sm"
            variant="outline"
            disabled={loading || !showLiveControls || designReviseBlocked}
            onClick={handleRevise}
          >
            {t("actions.requestRevision")}
          </NeonButton>
        </div>
        <ControlNotices
          designReviseBlocked={designReviseBlocked}
          personaApproveBlocked={personaApproveBlocked}
          personaShortfallDetail={personaShortfallDetail}
          presentationApproveBlocked={presentationApproveBlocked}
          editBudgetBlocked={editBudgetBlocked}
          contentHasEdits={contentHasEdits}
          showPublishLink={showPublishLink}
        />
      </div>
    </div>
  );
}
