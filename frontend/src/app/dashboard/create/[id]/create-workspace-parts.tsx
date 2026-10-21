"use client";

import { useTranslations } from "next-intl";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { BG_CARD, TEXT_DIM } from "@/constants/neon";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import { CREATE_STEP_IDS } from "@/app/dashboard/create/step-ids";
import { WorkflowFailedCard } from "@/modules/editorial";
import { BriefStepContent } from "@/app/dashboard/create/workspace/brief-step-content";
import { WorkflowStepContent } from "@/app/dashboard/create/workspace/workflow-step-content";
import type { CreateWorkspace } from "./use-create-workspace";

const briefCardStyle = {
  background: BG_CARD,
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "20px",
};

const goToPublishButtonStyle = {
  marginTop: "16px",
  padding: "10px 16px",
  borderRadius: "6px",
  border: "none",
  background: "linear-gradient(135deg, #00d4ff 0%, #0090b0 100%)",
  color: "#060a12",
  fontWeight: 700,
  fontSize: "13px",
  cursor: "pointer",
};

export function WorkspaceLoading(): React.ReactElement {
  return (
    <div
      className="flex flex-1 items-center justify-center text-white"
      style={{ minHeight: "40vh" }}
    >
      <NeonSpinner />
    </div>
  );
}

export function WorkspaceNotFound(): React.ReactElement {
  const t = useTranslations("create");
  return (
    <div className="flex flex-1 flex-col p-7 text-white">
      <NeonTopBar
        title={t("topBar.title")}
        breadcrumb={[{ label: t("topBar.project") }]}
      />
      <p className="mt-6 text-red-400">{t("errors.projectNotFound")}</p>
    </div>
  );
}

function PublishStepCard({
  onGoToPublish,
}: {
  onGoToPublish: () => void;
}): React.ReactElement {
  const t = useTranslations("create");
  return (
    <div style={briefCardStyle}>
      <p style={{ fontSize: "13px", color: TEXT_DIM, marginTop: 0 }}>
        {t("publishStep.hint")}
      </p>
      <button
        type="button"
        onClick={onGoToPublish}
        style={goToPublishButtonStyle}
      >
        {t("publishStep.goToPublish")}
      </button>
    </div>
  );
}

type LoadedProject = NonNullable<CreateWorkspace["projectQuery"]["data"]>;

/** The active step's body: failed card, publish hand-off, brief or a phase. */
export function WorkspaceStepBody({
  workspace,
  project,
}: {
  workspace: CreateWorkspace;
  project: LoadedProject;
}): React.ReactElement {
  const { editorialWorkflow, activeStepId, projectId, starter } = workspace;
  const state = editorialWorkflow.state;
  if (state?.phase_status === WORKFLOW_PHASE_STATUS.FAILED) {
    return (
      <WorkflowFailedCard
        currentPhase={state.current_phase}
        errorMessage={state.error_message}
        onRetry={() => {
          void starter.handleRetryWorkflow();
        }}
        isRetrying={starter.retrying}
      />
    );
  }
  if (activeStepId === CREATE_STEP_IDS.PUBLISH) {
    return <PublishStepCard onGoToPublish={workspace.navigation.goToPublish} />;
  }
  if (activeStepId === CREATE_STEP_IDS.BRIEF) {
    return (
      <BriefStepContent
        project={project}
        projectId={projectId}
        sourceCount={workspace.projectSources.length}
        workflowStarted={starter.workflowStarted}
        onStartWorkflow={starter.handleStartWorkflow}
        onSourcesChange={workspace.setProjectSources}
        editorialWorkflow={editorialWorkflow}
      />
    );
  }
  return (
    <WorkflowStepContent
      project={project}
      projectId={projectId}
      activeStepId={activeStepId}
      sources={workspace.sources}
      workflowStarted={starter.workflowStarted}
      editorialWorkflow={editorialWorkflow}
      publishedProject={workspace.publishedProject}
      onPublished={workspace.setPublishedProject}
    />
  );
}
