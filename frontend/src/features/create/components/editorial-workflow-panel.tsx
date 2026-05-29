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
import { EditorialWorkflowArtifacts } from "@/features/create/components/editorial-workflow-artifacts";
import { EditorialPhaseReview } from "@/features/create/components/editorial-phase-review";
import { EditorialWorkflowProgress } from "@/features/create/components/editorial-workflow-progress";
import type { useEditorialWorkflow } from "@/features/create/hooks/use-editorial-workflow";

type EditorialWorkflowApi = ReturnType<typeof useEditorialWorkflow>;

interface EditorialWorkflowPanelProps {
  projectId: string;
  topic: string;
  audience: string;
  brief: string;
  sources?: Array<{ title: string; content: string; source_type?: string }>;
  autoStart?: boolean;
  onPublished?: () => void;
  workflow: EditorialWorkflowApi;
}

export function EditorialWorkflowPanel({
  projectId,
  topic,
  audience,
  brief,
  sources = [],
  autoStart = false,
  onPublished,
  workflow,
}: EditorialWorkflowPanelProps): React.JSX.Element {
  const t = useTranslations("editorialWorkflow");
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

  return (
    <div className="space-y-4 rounded-lg border p-4">
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

      <EditorialWorkflowProgress state={state} loading={loading} />

      <EditorialWorkflowArtifacts state={state} />

      {state && awaitingHumanReview && (
        <EditorialPhaseReview projectId={projectId} state={state} />
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
          {awaitingHumanReview && (
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
                    className="border-input bg-background w-full rounded-md border px-3 py-2 text-sm"
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
              <p className="text-muted-foreground text-xs">
                {t("actions.processing")}
              </p>
            )}
            <div className="flex gap-2">
              <NeonButton
                size="sm"
                disabled={
                  loading || !awaitingHumanReview || personaApproveBlocked
                }
                onClick={() => void approve()}
              >
                {loading ? t("actions.processing") : t("actions.approve")}
              </NeonButton>
              <NeonButton
                size="sm"
                variant="outline"
                disabled={loading || !awaitingHumanReview}
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
