"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import {
  EDITORIAL_PHASES,
  EDITORIAL_WORKFLOW_STATUS,
  PERSONA_VOICE_MATCH_MIN_SCORE,
  type FinalReviewSendBackPhase,
} from "@/constants/editorial-workflow";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
} from "@/modules/publishing";
import {
  hasBlockingPresentationViolations,
  localizedSlidesHaveBudgetViolations,
  resolveLocalizedSlides,
  slidesHaveCopyChanges,
  type useEditorialWorkflow,
} from "@/modules/editorial";
import {
  CREATE_STEP_IDS,
  CREATE_STEP_TO_EDITORIAL_PHASE,
  EDITORIAL_PHASE_TO_STEP,
  isHistoricalCreateStep,
  type CreateStepId,
} from "@/app/dashboard/create/step-ids";
import { shouldShowLiveWorkflowControls } from "@/app/dashboard/create/workspace/create-workflow-live-controls";
import { personaScoreShortfalls } from "@/app/dashboard/create/workspace/persona-score";

export type CreateWorkflowApi = ReturnType<typeof useEditorialWorkflow>;
type WorkflowState = EditorialWorkflowState | null;

const PHASE_REVIEW_STEPS: ReadonlySet<CreateStepId> = new Set([
  CREATE_STEP_IDS.RESEARCH,
  CREATE_STEP_IDS.OUTLINE,
  CREATE_STEP_IDS.CONTENT,
  CREATE_STEP_IDS.REVIEW,
]);

/** The start input of an auto-started workflow. */
export interface WorkflowStartInput {
  topic: string;
  audience: string;
  brief: string;
  sources?: WorkflowStartSource[];
}

type WorkflowStartSource = {
  title: string;
  content: string;
  source_type?: string;
};

const NO_SOURCES: WorkflowStartSource[] = [];

/** Start the workflow once when asked to; report an approved publish. */
export function useWorkflowLifecycle(
  workflow: CreateWorkflowApi,
  { autoStart, input }: { autoStart?: boolean; input: WorkflowStartInput },
  onPublished: (() => void) | undefined,
): void {
  const startedRef = useRef(false);
  const { hasActiveWorkflow, start } = workflow;
  const { topic, audience, brief } = input;
  const sources = input.sources ?? NO_SOURCES;
  useEffect(() => {
    if (!autoStart || startedRef.current || hasActiveWorkflow) {
      return;
    }
    startedRef.current = true;
    void start({ topic, audience, brief, sources });
  }, [autoStart, hasActiveWorkflow, topic, audience, brief, sources, start]);

  const workflowStatus = workflow.state?.workflow_status;
  useEffect(() => {
    if (
      workflowStatus === EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH &&
      onPublished
    ) {
      onPublished();
    }
  }, [workflowStatus, onPublished]);
}

/** Local content-slide edits, dropped when the upstream state advances. */
export function useContentEdits(state: WorkflowState): {
  contentSlides: LocalizedSlideReview[];
  contentHasEdits: boolean;
  setEditedContentSlides: (slides: LocalizedSlideReview[]) => void;
} {
  const baseline = useMemo(
    () => (state ? resolveLocalizedSlides(state) : []),
    [state],
  );
  const lockVersion = state?.lock_version;
  // Edits are keyed to the lock version they were made on: a newer version
  // (e.g. after an approval) resets them without an effect.
  const [edits, setEdits] = useState<{
    lockVersion: number | undefined;
    slides: LocalizedSlideReview[];
  } | null>(null);
  const edited =
    edits !== null && edits.lockVersion === lockVersion ? edits.slides : null;
  return {
    contentSlides: edited ?? baseline,
    contentHasEdits: edited !== null && slidesHaveCopyChanges(baseline, edited),
    setEditedContentSlides: (slides) => setEdits({ lockVersion, slides }),
  };
}

/** The revise feedback box and the final-review send-back target. */
export interface WorkflowFeedback {
  feedback: string;
  setFeedback: (value: string) => void;
  feedbackError: string | null;
  setFeedbackError: (value: string | null) => void;
  sendBackTarget: FinalReviewSendBackPhase;
  setSendBackTarget: (value: FinalReviewSendBackPhase) => void;
  handleRevise: () => void;
}

export function useWorkflowFeedback(
  state: WorkflowState,
  revise: CreateWorkflowApi["revise"],
): WorkflowFeedback {
  const t = useTranslations("editorialWorkflow");
  const [feedback, setFeedback] = useState("");
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [sendBackTarget, setSendBackTarget] =
    useState<FinalReviewSendBackPhase>(EDITORIAL_PHASES.CONTENT);

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

  return {
    feedback,
    setFeedback,
    feedbackError,
    setFeedbackError,
    sendBackTarget,
    setSendBackTarget,
    handleRevise,
  };
}

/** AE-0415 (B01): the slides below the persona bar, named, or null. */
export function usePersonaShortfallDetail(state: WorkflowState): {
  personaApproveBlocked: boolean;
  personaShortfallDetail: string | null;
} {
  const t = useTranslations("editorialWorkflow");
  // One 0-100 scale (a 0-10 answer reads x10) and unscored slides ignored,
  // as the backend gate does (AE-0407).
  const shortfalls =
    state?.current_phase === EDITORIAL_PHASES.CONTENT
      ? personaScoreShortfalls(state.persona_scores)
      : [];
  if (shortfalls.length === 0) {
    return { personaApproveBlocked: false, personaShortfallDetail: null };
  }
  const slides = shortfalls
    .map((item) =>
      t("persona.slideScore", {
        slide: item.slideNumber ?? item.key,
        score: item.score,
      }),
    )
    .join(", ");
  return {
    personaApproveBlocked: true,
    personaShortfallDetail: t("persona.belowThresholdSlides", {
      slides,
      threshold: PERSONA_VOICE_MATCH_MIN_SCORE,
    }),
  };
}

export interface ApprovalGates {
  presentationApproveBlocked: boolean;
  editBudgetBlocked: boolean;
  designReviseBlocked: boolean;
  showPublishLink: boolean;
}

/** Approval blockers that do not depend on the persona scores. */
export function approvalGates(
  state: WorkflowState,
  content: { contentSlides: LocalizedSlideReview[]; contentHasEdits: boolean },
): ApprovalGates {
  const phase = state?.current_phase;
  return {
    presentationApproveBlocked: hasBlockingPresentationViolations(state),
    editBudgetBlocked:
      phase === EDITORIAL_PHASES.CONTENT &&
      content.contentHasEdits &&
      localizedSlidesHaveBudgetViolations(
        content.contentSlides,
        state?.presentation_policy_version,
      ),
    // AE-0310: blocking content-level violations at the design gate are only
    // resolvable by direct edits or a content send-back; a plain revise is a
    // provable no-op there, so it is disabled.
    designReviseBlocked:
      phase === EDITORIAL_PHASES.DESIGN &&
      (hasBlockingPresentationViolations(state) ||
        Boolean(state?.design_recovery_hint)),
    showPublishLink:
      state?.workflow_status === EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH,
  };
}

/** Which step is viewed, and what the panel shows for it. */
export interface StepView {
  viewStepId: CreateStepId;
  workflowStepId: CreateStepId;
}

function isLiveStep(state: WorkflowState, step: StepView): boolean {
  const phase = state?.current_phase;
  return (
    CREATE_STEP_TO_EDITORIAL_PHASE[step.viewStepId] !== undefined &&
    phase !== undefined &&
    EDITORIAL_PHASE_TO_STEP[phase] === step.viewStepId &&
    step.viewStepId === step.workflowStepId
  );
}

function isContentPhase(state: WorkflowState): boolean {
  return state?.current_phase === EDITORIAL_PHASES.CONTENT;
}

function hasImagePromptsToShow(
  state: WorkflowState,
  viewStepId: CreateStepId,
): boolean {
  return (
    viewStepId === CREATE_STEP_IDS.IMAGES &&
    (state?.slide_image_prompts?.length ?? 0) > 0
  );
}

export interface StepVisibility {
  isHistoricalStep: boolean;
  isLiveStep: boolean;
  showLiveControls: boolean;
  contentEditable: boolean;
  showPhaseReview: boolean;
  showImagePromptReview: boolean;
}

export function stepVisibility(
  state: WorkflowState,
  step: StepView,
  awaitingHumanReview: boolean,
): StepVisibility {
  const live = isLiveStep(state, step);
  const historical = isHistoricalCreateStep(
    step.viewStepId,
    step.workflowStepId,
  );
  const showLiveControls = shouldShowLiveWorkflowControls({
    state,
    ...step,
    awaitingHumanReview,
  });
  return {
    isHistoricalStep: state !== null && historical,
    isLiveStep: live,
    showLiveControls,
    contentEditable: showLiveControls && isContentPhase(state),
    // AE-0415 (B13): the research and outline gates show what is reviewed too.
    showPhaseReview:
      state !== null &&
      (live || historical) &&
      PHASE_REVIEW_STEPS.has(step.viewStepId),
    showImagePromptReview: hasImagePromptsToShow(state, step.viewStepId),
  };
}

/** Revise callbacks for the content manual fixes and the design recovery. */
export interface RevisionActions {
  actionsLocked: boolean;
  designRecovery: {
    onSubmitEditedSlides: (slides: LocalizedSlideReview[]) => void;
    onSendBackToContent: (feedback: string) => void;
    disabled: boolean;
  };
  contentManualFixes: {
    onSubmit: (slides: LocalizedSlideReview[]) => void;
    submitting: boolean;
  };
}

export function revisionActions(
  workflow: CreateWorkflowApi,
  showLiveControls: boolean,
): RevisionActions {
  const { revise } = workflow;
  // AE-0415 (B15): nothing that mutates the project while a run executes.
  const actionsLocked =
    workflow.loading ||
    workflow.state?.phase_status === WORKFLOW_PHASE_STATUS.IN_PROGRESS;
  const submitEditedSlides = (slides: LocalizedSlideReview[]): void => {
    void revise("", { editedLocalizedSlides: slides });
  };
  return {
    actionsLocked,
    // AE-0310: design-step recovery (direct edits or a content send-back).
    designRecovery: {
      onSubmitEditedSlides: submitEditedSlides,
      onSendBackToContent: (feedback: string): void => {
        void revise(feedback, { targetPhase: EDITORIAL_PHASES.CONTENT });
      },
      disabled: actionsLocked || !showLiveControls,
    },
    // AE-0403: the edits ARE the input, so an edits-only revise saves and
    // re-validates them without approving the content step (AE-0310).
    contentManualFixes: {
      onSubmit: submitEditedSlides,
      submitting: actionsLocked,
    },
  };
}
