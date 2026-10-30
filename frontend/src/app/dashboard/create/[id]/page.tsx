"use client";

import { useTranslations } from "next-intl";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { carouselDisplayTitle } from "@/lib/carousel-display-title";
import { CreateProgressSteps } from "@/app/dashboard/create/create-progress-steps";
import { CreateWorkspaceSidebar } from "@/app/dashboard/create/create-workspace-sidebar";
import {
  CREATE_STEP_IDS,
  completedStepsBefore,
} from "@/app/dashboard/create/step-ids";
import { useCreateWorkspace } from "./use-create-workspace";
import {
  WorkspaceLoading,
  WorkspaceNotFound,
  WorkspaceStepBody,
} from "./create-workspace-parts";
import { BoardSequenceNavigation } from "./board-sequence-navigation";

const LAYOUT_GRID_CLASS =
  "grid grid-cols-1 gap-6 md:grid-cols-[minmax(0,1fr)_360px]";

export default function CreateWorkspacePage(): React.ReactElement {
  const t = useTranslations("create");
  const workspace = useCreateWorkspace();
  const { projectQuery, editorialWorkflow, activeStepId, workflowStepId } =
    workspace;
  const project = projectQuery.data;

  if (projectQuery.isLoading) {
    return <WorkspaceLoading />;
  }
  if (projectQuery.isError || !project) {
    return <WorkspaceNotFound />;
  }

  const { hasActiveWorkflow } = editorialWorkflow;
  const progressActiveStep =
    hasActiveWorkflow && activeStepId === CREATE_STEP_IDS.BRIEF
      ? workflowStepId
      : activeStepId;

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: "Inter, system-ui, sans-serif" }}
    >
      <NeonTopBar
        title={t("topBar.title")}
        breadcrumb={[
          { label: t("topBar.projects"), href: DASHBOARD_ROUTES.WORKFLOW },
          { label: carouselDisplayTitle(project) },
        ]}
        actions={<BoardSequenceNavigation projectId={workspace.projectId} />}
      />

      <div className="p-7">
        <CreateProgressSteps
          activeStepId={progressActiveStep}
          onStepChange={workspace.navigation.goToStep}
          completedStepIds={
            hasActiveWorkflow ? completedStepsBefore(workflowStepId) : undefined
          }
        />

        <div className={LAYOUT_GRID_CLASS}>
          <div
            role="tabpanel"
            id={`create-step-${activeStepId}`}
            aria-labelledby={`create-tab-${activeStepId}`}
          >
            <WorkspaceStepBody workspace={workspace} project={project} />
          </div>

          <CreateWorkspaceSidebar
            project={project}
            workflowState={editorialWorkflow.state}
            activeStepId={activeStepId}
            projectId={workspace.projectId}
            generationLog={workspace.generationLog}
          />
        </div>
      </div>
    </div>
  );
}
