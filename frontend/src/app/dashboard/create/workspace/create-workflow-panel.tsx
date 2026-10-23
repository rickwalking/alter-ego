"use client";

import { useState } from "react";

import { CreateWorkflowArtifacts } from "@/app/dashboard/create/workspace/create-workflow-artifacts";
import { CreatePhaseReview } from "@/app/dashboard/create/workspace/create-phase-review";
import { CreateWorkflowProgress } from "@/app/dashboard/create/workspace/create-workflow-progress";
import { CreateWorkflowControls } from "@/app/dashboard/create/workspace/create-workflow-controls";
import type { CreateStepId } from "@/app/dashboard/create/step-ids";
import { ImagePromptReview } from "@/modules/editorial";
import {
  approvalGates,
  revisionActions,
  stepVisibility,
  useContentEdits,
  usePersonaShortfallDetail,
  useWorkflowFeedback,
  useWorkflowLifecycle,
  type CreateWorkflowApi,
} from "./create-workflow-panel-state";
import {
  HistoricalStepView,
  PhaseEventBadges,
  WorkflowPanelFrame,
  WorkflowErrorAlert,
  WorkflowPanelHeader,
  WorkflowRunNotices,
} from "./create-workflow-panel-parts";

interface CreateWorkflowPanelProps {
  projectId: string;
  topic: string;
  audience: string;
  brief: string;
  sources?: { title: string; content: string; source_type?: string }[];
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
  sources,
  autoStart,
  onPublished,
  workflow,
  viewStepId,
  workflowStepId,
}: Readonly<CreateWorkflowPanelProps>): React.JSX.Element {
  const { state, phaseEvents, loading, error, revise, refreshState } = workflow;
  useWorkflowLifecycle(
    workflow,
    { autoStart, input: { topic, audience, brief, sources } },
    onPublished,
  );
  const content = useContentEdits(state);
  const [copyBusy, setCopyBusy] = useState(false);
  const feedback = useWorkflowFeedback(state, revise);
  const persona = usePersonaShortfallDetail(state);
  const gates = approvalGates(state, content);
  const view = stepVisibility(
    state,
    { viewStepId, workflowStepId },
    workflow.awaitingHumanReview,
  );
  const { actionsLocked, designRecovery, contentManualFixes } = revisionActions(
    workflow,
    view.showLiveControls,
  );

  if (view.isHistoricalStep && state) {
    return (
      <HistoricalStepView
        workflow={workflow}
        viewStepId={viewStepId}
        state={state}
      />
    );
  }

  return (
    <WorkflowPanelFrame>
      <WorkflowPanelHeader workflow={workflow} />
      <WorkflowRunNotices workflow={workflow} />

      <WorkflowErrorAlert error={error} />

      {view.isLiveStep ? (
        <CreateWorkflowProgress state={state} loading={loading} />
      ) : null}

      <CreateWorkflowArtifacts state={state} />

      {view.showImagePromptReview && (
        <ImagePromptReview prompts={state?.slide_image_prompts} readOnly />
      )}

      {state && view.showPhaseReview && (
        <CreatePhaseReview
          projectId={projectId}
          state={state}
          contentEditable={view.contentEditable}
          contentSlides={content.contentSlides}
          onContentSlidesChange={content.setEditedContentSlides}
          contentManualFixes={contentManualFixes}
          designRecovery={designRecovery}
          onRepaired={() => void refreshState()}
          onCopySaved={refreshState}
          onCopyBusyChange={setCopyBusy}
          actionsLocked={actionsLocked}
        />
      )}

      {state && (
        <CreateWorkflowControls
          state={state}
          showLiveControls={view.showLiveControls}
          loading={loading}
          {...feedback}
          approve={(options) => {
            void workflow.approve(options);
          }}
          contentHasEdits={content.contentHasEdits}
          copyBlocked={copyBusy}
          contentSlides={content.contentSlides}
          {...persona}
          {...gates}
        />
      )}

      <PhaseEventBadges
        phaseEvents={phaseEvents}
        currentPhase={state?.current_phase}
      />
    </WorkflowPanelFrame>
  );
}
