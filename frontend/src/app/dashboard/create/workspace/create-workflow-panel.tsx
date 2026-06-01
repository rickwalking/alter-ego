"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { NeonAlert, NeonAlertDescription } from "@/components/molecules/neon-alert";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import {
  EDITORIAL_PHASES,
  EDITORIAL_WORKFLOW_STATUS,
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
  FINAL_REVIEW_SEND_BACK_PHASES,
  PERSONA_VOICE_MATCH_MIN_SCORE,
  type FinalReviewSendBackPhase,
} from "@/constants/editorial-workflow";
import { CreateWorkflowArtifacts } from "@/app/dashboard/create/workspace/create-workflow-artifacts";
import { CreatePhaseReview } from "@/app/dashboard/create/workspace/create-phase-review";
import { CreateStepHistoryPanel } from "@/app/dashboard/create/workspace/create-step-history-panel";
import { CreateWorkflowProgress } from "@/app/dashboard/create/workspace/create-workflow-progress";
import {
  CREATE_STEP_IDS,
  CREATE_STEP_TO_EDITORIAL_PHASE,
  isHistoricalCreateStep,
  type CreateStepId,
} from "@/app/dashboard/create/step-ids";
import { shouldShowLiveWorkflowControls } from "@/app/dashboard/create/workspace/create-workflow-live-controls";
import type { useEditorialWorkflow } from "@/features/create/hooks/use-editorial-workflow";

type CreateWorkflowApi = ReturnType<typeof useEditorialWorkflow>;

interface CreateWorkflowPanelProps {
  projectId: string;
  topic: string;
  audience: string;
  brief: string;
  sources?: Array<{ title: string; content: string; source_type?: string }>;
  autoStart?: boolean;
  onPublished?: () => void;
  workflow: CreateWorkflowApi;
  viewStepId: CreateStepId;
  workflowStepId: CreateStepId;
}

export function CreateWorkflowPanel({
  projectId,
  topic,
  audience,
  brief,
  sources = [],
  autoStart = false,
  onPublished,
  workflow,
  viewStepId,
  workflowStepId,
}: CreateWorkflowPanelProps): React.JSX.Element {
  const t = useTranslations("editorialWorkflow");
  const tCreate = useTranslations("create.stepHistory");
  const startedRef = useRef(false);
  const [feedback, setFeedback] = useState("");
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [sendBackTarget, setSendBackTarget] =
    useState<FinalReviewSendBackPhase>(EDITORIAL_PHASES.CONTENT);
  const {
    state,
    phaseEvents,
    loading,
    error,
    transportMode,
    start,
    approve,
    revise,
    awaitingHumanReview,
    hasActiveWorkflow,
  } = workflow;

  useEffect(() => {
    if (!autoStart || startedRef.current || hasActiveWorkflow) {
      return;
    }
    startedRef.current = true;
    void start({ topic, audience, brief, sources });
  }, [autoStart, hasActiveWorkflow, topic, audience, brief, sources, start]);

  useEffect(() => {
    if (
      state?.workflow_status ===
        EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH &&
      onPublished
    ) {
      onPublished();
    }
  }, [state?.workflow_status, onPublished]);

  const handleRevise = (): void => {
    const trimmed = feedback.trim();
    if (!trimmed) {
      setFeedbackError(t("feedback.required"));
      return;
    }
    setFeedbackError(null);
    const reviseOptions =
      state?.current_phase === EDITORIAL_PHASES.FINAL_REVIEW
        ? { targetPhase: sendBackTarget }
        : undefined;
    void Promise.resolve(revise(trimmed, reviseOptions)).then(() => {
      setFeedback("");
    });
  };

  const isFinalReviewGate =
    state?.current_phase === EDITORIAL_PHASES.FINAL_REVIEW;

  const minPersonaScore =
    state?.current_phase === EDITORIAL_PHASES.CONTENT && state.persona_scores
      ? Math.min(
          ...Object.values(state.persona_scores).map((entry) => {
            if (entry && typeof entry === "object" && "overall" in entry) {
              const overall = (entry as { overall?: unknown }).overall;
              return typeof overall === "number"
                ? overall
                : Number(overall ?? 0);
            }
            return typeof entry === "number" ? entry : 0;
          }),
        )
      : null;
  const personaApproveBlocked =
    minPersonaScore !== null && minPersonaScore < PERSONA_VOICE_MATCH_MIN_SCORE;
  const showPublishLink =
    state?.workflow_status === EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH;

  const viewPhase = CREATE_STEP_TO_EDITORIAL_PHASE[viewStepId];
  const isHistoricalStep =
    state !== null &&
    state !== undefined &&
    isHistoricalCreateStep(viewStepId, workflowStepId);
  const isLiveStep =
    viewPhase !== undefined &&
    state?.current_phase === viewPhase &&
    viewStepId === workflowStepId;
  const showLiveControls = shouldShowLiveWorkflowControls(
    viewPhase,
    state,
    viewStepId,
    workflowStepId,
    awaitingHumanReview,
  );
  const showPhaseReview =
    viewStepId === CREATE_STEP_IDS.REVIEW &&
    Boolean(state) &&
    (isLiveStep || isHistoricalCreateStep(viewStepId, workflowStepId));

  if (isHistoricalStep && state) {
    return (
      <div
        className="space-y-4"
        style={{
          background: "var(--bg-card, #0d1324)",
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: "8px",
          padding: "20px",
        }}
      >
        <p className="text-sm" style={{ color: "rgba(255,255,255,0.55)" }}>
          {tCreate("historicalHint", { phase: viewPhase ?? viewStepId })}
        </p>
        <CreateStepHistoryPanel viewStepId={viewStepId} state={state} />
      </div>
    );
  }

  return (
    <div
      className="space-y-4"
      style={{
        background: "var(--bg-card, #0d1324)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: "8px",
        padding: "20px",
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-semibold">{t("title")}</h3>
        <div className="flex items-center gap-2">
          {transportMode ===
            EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK && (
            <NeonBadge variant="outline">{t("transport.pollingFallback")}</NeonBadge>
          )}
          {hasActiveWorkflow && (
            <NeonBadge variant="secondary">{state?.current_phase}</NeonBadge>
          )}
        </div>
      </div>

      {error && (
        <NeonAlert variant="destructive">
          <NeonAlertDescription>{error}</NeonAlertDescription>
        </NeonAlert>
      )}

      {isLiveStep ? (
        <CreateWorkflowProgress state={state} loading={loading} />
      ) : null}

      <CreateWorkflowArtifacts state={state} />

      {state && showPhaseReview && (
        <CreatePhaseReview projectId={projectId} state={state} />
      )}

      {state && (
        <div className="space-y-2 text-sm">
          <p>
            {t("currentPhase")}:{" "}
            <NeonBadge variant="secondary">{state.current_phase}</NeonBadge>
          </p>
          <p>
            {t("phaseStatus")}: <NeonBadge>{state.phase_status}</NeonBadge>
          </p>
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
                disabled={loading || !showLiveControls || personaApproveBlocked}
                onClick={() => void approve()}
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
            {showPublishLink && (
              <p className="text-[var(--color-text-muted)] text-xs">
                {t("publishReady")}
              </p>
            )}
          </div>
        </div>
      )}

      {phaseEvents.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {phaseEvents.map((phase) => (
            <NeonBadge
              key={phase}
              variant={phase === state?.current_phase ? "default" : "outline"}
            >
              {phase}
            </NeonBadge>
          ))}
        </div>
      )}
    </div>
  );
}
