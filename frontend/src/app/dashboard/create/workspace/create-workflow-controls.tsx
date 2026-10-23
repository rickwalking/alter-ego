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

type BlockFlags = Pick<
  CreateWorkflowControlsProps,
  | "personaApproveBlocked"
  | "presentationApproveBlocked"
  | "editBudgetBlocked"
  | "designReviseBlocked"
  | "copyBlocked"
>;

/** Which of approve / revise are blocked, and by what. */
function blockedActions(flags: BlockFlags): {
  approveBlocked: boolean;
  reviseBlocked: boolean;
} {
  const copyBlocked = flags.copyBlocked === true;
  return {
    approveBlocked:
      flags.personaApproveBlocked ||
      flags.presentationApproveBlocked ||
      flags.editBudgetBlocked ||
      copyBlocked,
    reviseBlocked: flags.designReviseBlocked || copyBlocked,
  };
}

/** The final review's "save or discard the caption / LinkedIn edit" note. */
function CopyBlockedNotice({
  shown,
}: Readonly<{ shown: boolean }>): React.JSX.Element | null {
  const t = useTranslations("editorialWorkflow");
  if (!shown) {
    return null;
  }
  return (
    <p className="text-[var(--color-text-muted)] text-xs">
      {t("review.finalReview.copyBlocked")}
    </p>
  );
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
  copyBlocked,
}: Readonly<CreateWorkflowControlsProps>): React.JSX.Element {
  const t = useTranslations("editorialWorkflow");
  const isFinalReviewGate =
    state?.current_phase === EDITORIAL_PHASES.FINAL_REVIEW;
  const { approveBlocked, reviseBlocked } = blockedActions({
    personaApproveBlocked,
    presentationApproveBlocked,
    editBudgetBlocked,
    designReviseBlocked,
    copyBlocked,
  });

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
              approve(approveOptionsFor(state, contentHasEdits, contentSlides));
            }}
          >
            {t("actions.approve")}
          </NeonButton>
          <NeonButton
            size="sm"
            variant="outline"
            disabled={loading || !showLiveControls || reviseBlocked}
            onClick={handleRevise}
          >
            {t("actions.requestRevision")}
          </NeonButton>
        </div>
        <CopyBlockedNotice shown={copyBlocked === true} />
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
