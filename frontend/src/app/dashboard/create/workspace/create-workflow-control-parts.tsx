"use client";

import { useTranslations } from "next-intl";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import {
  FINAL_REVIEW_SEND_BACK_PHASES,
  type FinalReviewSendBackPhase,
} from "@/constants/editorial-workflow";
import type { CreateWorkflowControlsProps } from "@/modules/editorial";

export type FeedbackFieldsProps = Pick<
  CreateWorkflowControlsProps,
  | "feedback"
  | "setFeedback"
  | "feedbackError"
  | "setFeedbackError"
  | "sendBackTarget"
  | "setSendBackTarget"
> & { isFinalReviewGate: boolean };

/** Reviewer feedback (and, at final review, the phase to send back to). */
export function FeedbackFields({
  feedback,
  setFeedback,
  feedbackError,
  setFeedbackError,
  sendBackTarget,
  setSendBackTarget,
  isFinalReviewGate,
}: FeedbackFieldsProps): React.JSX.Element {
  const t = useTranslations("editorialWorkflow");
  return (
    <div className="space-y-2">
      {isFinalReviewGate && (
        <div className="space-y-1">
          <label
            className="block font-medium"
            htmlFor="editorial-send-back-phase"
          >
            {t("sendBack.label")}
          </label>
          <select
            id="editorial-send-back-phase"
            className="w-full rounded-md border px-3 py-2 text-sm"
            style={{
              border: "1px solid rgba(255,255,255,0.08)",
              background: "rgba(6,10,18,0.45)",
              color: "rgba(255,255,255,0.88)",
            }}
            value={sendBackTarget}
            onChange={(event) => {
              setSendBackTarget(event.target.value as FinalReviewSendBackPhase);
            }}
          >
            {FINAL_REVIEW_SEND_BACK_PHASES.map((phase) => (
              <option key={phase} value={phase}>
                {t(`sendBack.phases.${phase}`)}
              </option>
            ))}
          </select>
        </div>
      )}
      <label className="block font-medium" htmlFor="editorial-feedback">
        {t("feedback.label")}
      </label>
      <NeonTextarea
        id="editorial-feedback"
        value={feedback}
        onChange={(event) => {
          setFeedback(event.target.value);
          if (feedbackError && event.target.value.trim()) {
            setFeedbackError(null);
          }
        }}
        placeholder={t("feedback.placeholder")}
        rows={3}
      />
      {feedbackError && (
        <p className="text-destructive text-xs">{feedbackError}</p>
      )}
    </div>
  );
}

export type ControlNoticesProps = Pick<
  CreateWorkflowControlsProps,
  | "designReviseBlocked"
  | "personaApproveBlocked"
  | "personaShortfallDetail"
  | "presentationApproveBlocked"
  | "editBudgetBlocked"
  | "contentHasEdits"
  | "showPublishLink"
>;

/** Why approve/revise is blocked, unsaved edits, and the publish-ready note. */
export function ControlNotices({
  designReviseBlocked,
  personaApproveBlocked,
  personaShortfallDetail = null,
  presentationApproveBlocked,
  editBudgetBlocked,
  contentHasEdits,
  showPublishLink,
}: Readonly<ControlNoticesProps>): React.JSX.Element {
  const t = useTranslations("editorialWorkflow");
  return (
    <>
      {designReviseBlocked && (
        <p className="text-[var(--color-text-muted)] text-xs">
          {t("presentation.designReviseDisabled")}
        </p>
      )}
      {personaApproveBlocked && (
        <p className="text-destructive text-xs">
          {personaShortfallDetail ?? t("persona.belowThreshold")}
        </p>
      )}
      {presentationApproveBlocked && (
        <p className="text-destructive text-xs">
          {t("presentation.blockedApproval")}
        </p>
      )}
      {editBudgetBlocked && (
        <p className="text-destructive text-xs">
          {t("presentation.editBudgetBlocked")}
        </p>
      )}
      {contentHasEdits && !editBudgetBlocked && (
        <p className="text-[var(--color-text-muted)] text-xs">
          {t("presentation.unsavedEdits")}
        </p>
      )}
      {showPublishLink && (
        <p className="text-[var(--color-text-muted)] text-xs">
          {t("publishReady")}
        </p>
      )}
    </>
  );
}
