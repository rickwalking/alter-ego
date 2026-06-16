"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { BG_CARD, TEXT_DIM } from "@/constants/neon";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { CreateProgressSteps } from "@/app/dashboard/create/create-progress-steps";
import { CreateWorkspaceSidebar } from "@/app/dashboard/create/create-workspace-sidebar";
import {
  CREATE_STEP_IDS,
  completedStepsBefore,
  parseCreateStepId,
  resolveStepFromWorkflowPhase,
  type CreateStepId,
} from "@/app/dashboard/create/step-ids";
import { WorkflowFailedCard } from "@/features/create/components/workflow-failed-card";
import { useCarouselProject } from "@/features/create/hooks";
import { useEditorialWorkflow } from "@/features/create/hooks/use-editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { ContentSource } from "@/modules/publishing";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import { BriefStepContent } from "@/app/dashboard/create/workspace/brief-step-content";
import { WorkflowStepContent } from "@/app/dashboard/create/workspace/workflow-step-content";
import { createRetryWorkflowHandler } from "@/app/dashboard/create/[id]/create-retry-handler";

const layoutGridStyle = {
  display: "grid",
  gridTemplateColumns: "1fr 360px",
  gap: "24px",
} as const;

const briefCardStyle = {
  background: BG_CARD,
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "20px",
};

export default function CreateWorkspacePage(): React.ReactElement {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeStepId = parseCreateStepId(searchParams.get("step"));

  const { data: project, isLoading, isError } = useCarouselProject(projectId);
  const editorialWorkflow = useEditorialWorkflow(projectId);
  const [projectSources, setProjectSources] = useState<ContentSource[]>([]);
  const [workflowStarted, setWorkflowStarted] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [publishedProject, setPublishedProject] =
    useState<CarouselProjectResponse | null>(null);

  const workflowStepId = resolveStepFromWorkflowPhase(
    editorialWorkflow.state?.current_phase,
  );

  const progressActiveStep =
    editorialWorkflow.hasActiveWorkflow &&
    activeStepId === CREATE_STEP_IDS.BRIEF
      ? workflowStepId
      : activeStepId;

  const handleStepChange = useCallback(
    (stepId: CreateStepId): void => {
      if (stepId === CREATE_STEP_IDS.PUBLISH) {
        router.push(DASHBOARD_ROUTES.CREATE_PUBLISH(projectId));
        return;
      }
      router.push(
        `${DASHBOARD_ROUTES.CREATE_WORKSPACE(projectId)}?step=${stepId}`,
      );
    },
    [projectId, router],
  );

  useEffect(() => {
    if (
      !editorialWorkflow.hasActiveWorkflow ||
      activeStepId !== CREATE_STEP_IDS.BRIEF
    ) {
      return;
    }
    const derived = resolveStepFromWorkflowPhase(
      editorialWorkflow.state?.current_phase,
    );
    if (derived !== CREATE_STEP_IDS.BRIEF) {
      router.replace(
        `${DASHBOARD_ROUTES.CREATE_WORKSPACE(projectId)}?step=${derived}`,
      );
    }
  }, [
    activeStepId,
    editorialWorkflow.hasActiveWorkflow,
    editorialWorkflow.state?.current_phase,
    projectId,
    router,
  ]);

  const mappedSources = projectSources.map((source) => ({
    title: source.title,
    content: source.content,
    source_type: source.source_type,
  }));

  const handleStartWorkflow = useCallback(
    async (withMaterials: boolean): Promise<void> => {
      if (!project) {
        return;
      }
      setWorkflowStarted(true);
      try {
        await editorialWorkflow.start({
          topic: project.topic,
          audience: project.audience,
          brief: project.niche,
          sources: withMaterials ? mappedSources : [],
        });
        router.push(
          `${DASHBOARD_ROUTES.CREATE_WORKSPACE(projectId)}?step=${CREATE_STEP_IDS.OUTLINE}`,
        );
      } catch {
        setWorkflowStarted(false);
      }
    },
    [editorialWorkflow, mappedSources, project, projectId, router],
  );

  const isFailed =
    editorialWorkflow.state?.phase_status === WORKFLOW_PHASE_STATUS.FAILED;

  // Idempotent retry (AE-0009): duplicate clicks must trigger a single
  // restart. The `retrying` guard short-circuits in-flight clicks before the
  // button's disabled state propagates — previews the AE-0073 concurrency
  // contract intent (one restart per failure). On failure, `retrying` resets so
  // the button re-enables and the error card stays. See create-retry-handler.ts.
  const handleRetryWorkflow = useCallback(
    (): Promise<void> =>
      createRetryWorkflowHandler({
        project,
        retrying,
        setRetrying,
        start: editorialWorkflow.start,
        sources: mappedSources,
        navigateOnSuccess: () =>
          router.push(
            `${DASHBOARD_ROUTES.CREATE_WORKSPACE(projectId)}?step=${CREATE_STEP_IDS.OUTLINE}`,
          ),
      })(),
    [
      editorialWorkflow.start,
      mappedSources,
      project,
      projectId,
      retrying,
      router,
    ],
  );

  if (isLoading) {
    return (
      <div
        className="flex flex-1 items-center justify-center text-white"
        style={{ minHeight: "40vh" }}
      >
        <NeonSpinner />
      </div>
    );
  }

  if (isError || !project) {
    return (
      <div className="flex flex-1 flex-col p-7 text-white">
        <NeonTopBar
          title="Create Carousel"
          breadcrumb={[{ label: "project" }]}
        />
        <p className="mt-6 text-red-400">Project not found.</p>
      </div>
    );
  }

  const isBriefStep = activeStepId === CREATE_STEP_IDS.BRIEF;
  const isPublishStep = activeStepId === CREATE_STEP_IDS.PUBLISH;

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: "Inter, system-ui, sans-serif" }}
    >
      <NeonTopBar
        title="Create Carousel"
        breadcrumb={[
          { label: "projects", href: DASHBOARD_ROUTES.WORKFLOW },
          { label: project.topic },
        ]}
      />

      <div className="p-7">
        <CreateProgressSteps
          activeStepId={progressActiveStep}
          onStepChange={handleStepChange}
          completedStepIds={
            editorialWorkflow.hasActiveWorkflow
              ? completedStepsBefore(workflowStepId)
              : undefined
          }
        />

        <div style={layoutGridStyle}>
          <div
            role="tabpanel"
            id={`create-step-${activeStepId}`}
            aria-labelledby={`create-tab-${activeStepId}`}
          >
            {isFailed ? (
              <WorkflowFailedCard
                currentPhase={editorialWorkflow.state?.current_phase ?? ""}
                errorMessage={editorialWorkflow.state?.error_message}
                onRetry={handleRetryWorkflow}
                isRetrying={retrying}
              />
            ) : isPublishStep ? (
              <div style={briefCardStyle}>
                <p style={{ fontSize: "13px", color: TEXT_DIM, marginTop: 0 }}>
                  Final approval and distribution live on the Publish screen.
                </p>
                <button
                  type="button"
                  onClick={() =>
                    router.push(DASHBOARD_ROUTES.CREATE_PUBLISH(projectId))
                  }
                  style={{
                    marginTop: "16px",
                    padding: "10px 16px",
                    borderRadius: "6px",
                    border: "none",
                    background:
                      "linear-gradient(135deg, #00d4ff 0%, #0090b0 100%)",
                    color: "#060a12",
                    fontWeight: 700,
                    fontSize: "13px",
                    cursor: "pointer",
                  }}
                >
                  Go to Publish
                </button>
              </div>
            ) : isBriefStep ? (
              <BriefStepContent
                project={project}
                projectId={projectId}
                sourceCount={projectSources.length}
                workflowStarted={workflowStarted}
                onStartWorkflow={handleStartWorkflow}
                onSourcesChange={setProjectSources}
                editorialWorkflow={editorialWorkflow}
              />
            ) : (
              <WorkflowStepContent
                project={project}
                projectId={projectId}
                activeStepId={activeStepId}
                sources={mappedSources}
                workflowStarted={workflowStarted}
                editorialWorkflow={editorialWorkflow}
                publishedProject={publishedProject}
                onPublished={setPublishedProject}
              />
            )}
          </div>

          <CreateWorkspaceSidebar
            project={project}
            workflowState={editorialWorkflow.state}
            activeStepId={activeStepId}
            projectId={projectId}
          />
        </div>
      </div>
    </div>
  );
}
