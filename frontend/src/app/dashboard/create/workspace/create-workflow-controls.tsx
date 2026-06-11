"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import {
  EDITORIAL_PHASES,
  FINAL_REVIEW_SEND_BACK_PHASES,
  type FinalReviewSendBackPhase,
} from "@/constants/editorial-workflow";
import type { CreateWorkflowControlsProps } from "@/features/create/types";

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
  presentationApproveBlocked,
  editBudgetBlocked,
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
                  setSendBackTarget(
                    event.target.value as FinalReviewSendBackPhase,
                  );
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
      )}
      <div className="flex flex-col gap-2">
        {loading && (
          <p className="text-xs" style={{ color: "rgba(255,255,255,0.55)" }}>
            {t("actions.processing")}
          </p>
        )}
        <div className="flex gap-2">
          <NeonButton
            size="sm"
            disabled={loading || !showLiveControls || approveBlocked}
            onClick={() => {
              const approveOptions =
                state?.current_phase === EDITORIAL_PHASES.CONTENT && contentHasEdits
                  ? { editedLocalizedSlides: contentSlides }
                  : undefined;
              void approve(approveOptions);
            }}
          >
            {loading ? t("actions.processing") : t("actions.approve")}
          </NeonButton>
          <NeonButton
            size="sm"
            variant="outline"
            disabled={loading || !showLiveControls}
            onClick={handleRevise}
          >
            {t("actions.requestRevision")}
          </NeonButton>
        </div>
        {personaApproveBlocked && (
          <p className="text-destructive text-xs">
            {t("persona.belowThreshold")}
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
      </div>
    </div>
  );
}
