"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import { NeonBadge } from "@/components/atoms/neon-badge";
import {
  EDITORIAL_PHASES,
  EDITORIAL_WORKFLOW_STATUS,
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
  PERSONA_VOICE_MATCH_MIN_SCORE,
  type FinalReviewSendBackPhase,
} from "@/constants/editorial-workflow";
import { CreateWorkflowArtifacts } from "@/app/dashboard/create/workspace/create-workflow-artifacts";
import { CreatePhaseReview } from "@/app/dashboard/create/workspace/create-phase-review";
import { CreateStepHistoryPanel } from "@/app/dashboard/create/workspace/create-step-history-panel";
import { CreateWorkflowProgress } from "@/app/dashboard/create/workspace/create-workflow-progress";
import { CreateWorkflowControls } from "@/app/dashboard/create/workspace/create-workflow-controls";
import {
  CREATE_STEP_IDS,
  CREATE_STEP_TO_EDITORIAL_PHASE,
  EDITORIAL_PHASE_TO_STEP,
  isHistoricalCreateStep,
  type CreateStepId,
} from "@/app/dashboard/create/step-ids";
import { shouldShowLiveWorkflowControls } from "@/app/dashboard/create/workspace/create-workflow-live-controls";
import type { LocalizedSlideReview } from "@/features/blog/types-ai";
import {
  hasBlockingPresentationViolations,
  localizedSlidesHaveBudgetViolations,
  resolveLocalizedSlides,
  slidesHaveCopyChanges,
} from "@/features/create/lib/presentation-review-utils";
import { ImagePromptReview } from "@/features/create/components/image-prompt-review";
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
  const [editedContentSlides, setEditedContentSlides] = useState<
    LocalizedSlideReview[] | null
  >(null);
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

  const baselineContentSlides = useMemo(
    () => (state ? resolveLocalizedSlides(state) : []),
    [state],
  );

  const previousLockVersion = useRef(state?.lock_version);
  useEffect(() => {
    const current = state?.lock_version;
    if (previousLockVersion.current !== current) {
      previousLockVersion.current = current;
      // Reset local edits when upstream state advances (e.g., approval)
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setEditedContentSlides(null);
    }
  }, [state?.lock_version]);

  const contentSlides = editedContentSlides ?? baselineContentSlides;
  const contentHasEdits =
    editedContentSlides !== null &&
    slidesHaveCopyChanges(baselineContentSlides, editedContentSlides);

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
  const presentationApproveBlocked = hasBlockingPresentationViolations(state);
  const editBudgetBlocked =
    state?.current_phase === EDITORIAL_PHASES.CONTENT &&
    contentHasEdits &&
    localizedSlidesHaveBudgetViolations(
      contentSlides,
      state.presentation_policy_version,
    );
  const showPublishLink =
    state?.workflow_status === EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH;

  const viewPhase = CREATE_STEP_TO_EDITORIAL_PHASE[viewStepId];
  const isHistoricalStep =
    state !== null &&
    state !== undefined &&
    isHistoricalCreateStep(viewStepId, workflowStepId);
  const isLiveStep =
    viewPhase !== undefined &&
    state?.current_phase !== undefined &&
    EDITORIAL_PHASE_TO_STEP[state.current_phase] === viewStepId &&
    viewStepId === workflowStepId;
  const showLiveControls = shouldShowLiveWorkflowControls(
    state,
    viewStepId,
    workflowStepId,
    awaitingHumanReview,
  );
  const contentEditable =
    state?.current_phase === EDITORIAL_PHASES.CONTENT && showLiveControls;
  const showPhaseReview =
    Boolean(state) &&
    (isLiveStep || isHistoricalCreateStep(viewStepId, workflowStepId)) &&
    (viewStepId === CREATE_STEP_IDS.REVIEW ||
      viewStepId === CREATE_STEP_IDS.CONTENT);
  const showImagePromptReview =
    viewStepId === CREATE_STEP_IDS.IMAGES &&
    (state?.slide_image_prompts?.length ?? 0) > 0;

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
            <NeonBadge variant="outline">
              {t("transport.pollingFallback")}
            </NeonBadge>
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

      {showImagePromptReview && (
        <ImagePromptReview prompts={state?.slide_image_prompts} readOnly />
      )}

      {state && showPhaseReview && (
        <CreatePhaseReview
          projectId={projectId}
          state={state}
          contentEditable={contentEditable}
          contentSlides={contentSlides}
          onContentSlidesChange={setEditedContentSlides}
        />
      )}

      {state && (
        <CreateWorkflowControls
          state={state}
          showLiveControls={showLiveControls}
          loading={loading}
          feedback={feedback}
          setFeedback={setFeedback}
          feedbackError={feedbackError}
          setFeedbackError={setFeedbackError}
          sendBackTarget={sendBackTarget}
          setSendBackTarget={setSendBackTarget}
          handleRevise={handleRevise}
          approve={approve}
          contentHasEdits={contentHasEdits}
          contentSlides={contentSlides}
          personaApproveBlocked={personaApproveBlocked}
          presentationApproveBlocked={presentationApproveBlocked}
          editBudgetBlocked={editBudgetBlocked}
          showPublishLink={showPublishLink}
        />
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
