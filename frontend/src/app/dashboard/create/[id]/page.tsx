"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { BG_CARD, TEXT_DIM } from "@/constants/neon";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { CreateProgressSteps } from "@/app/dashboard/create/create-progress-steps";
import { CreateWorkspaceSidebar } from "@/app/dashboard/create/create-workspace-sidebar";
import {
  CREATE_STEP_IDS,
  completedStepsBefore,
  isFutureCreateStep,
  parseCreateStepId,
  resolveStepFromWorkflowPhase,
  type CreateStepId,
} from "@/app/dashboard/create/step-ids";
import {
  CarouselPreview,
  CreateDraftBlogPreview,
  CreateMaterialsGate,
  CreateSourceMaterials,
  CreateWorkflowPanel,
} from "@/app/dashboard/create/workspace";
import { useCarouselProject } from "@/features/create/hooks";
import { useEditorialWorkflow } from "@/features/create/hooks/use-editorial-workflow";
import type { ContentSource } from "@/features/blog/types-ai";
import type { CarouselProjectResponse } from "@/schemas/carousel";

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

function BriefStepContent({
  project,
  projectId,
  sourceCount,
  workflowStarted,
  onStartWorkflow,
  onSourcesChange,
  editorialWorkflow,
}: {
  project: CarouselProjectResponse;
  projectId: string;
  sourceCount: number;
  workflowStarted: boolean;
  onStartWorkflow: (withMaterials: boolean) => Promise<void>;
  onSourcesChange: (sources: ContentSource[]) => void;
  editorialWorkflow: ReturnType<typeof useEditorialWorkflow>;
}): React.ReactElement {
  const showGate =
    !workflowStarted && !editorialWorkflow.hasActiveWorkflow;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={briefCardStyle}>
        <h3 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "12px" }}>
          Topic & Brief
        </h3>
        <p style={{ fontSize: "15px", fontWeight: 600, margin: "0 0 8px" }}>
          {project.topic}
        </p>
        <p style={{ fontSize: "13px", color: TEXT_DIM, margin: "0 0 12px" }}>
          {project.audience}
        </p>
        <p style={{ fontSize: "13px", margin: 0, lineHeight: 1.5 }}>
          {project.niche}
        </p>
      </div>

      <CreateDraftBlogPreview projectId={projectId} />

      <CreateSourceMaterials
        projectId={projectId}
        onSourcesChange={onSourcesChange}
      />

      {showGate && (
        <CreateMaterialsGate
          sourceCount={sourceCount}
          loading={editorialWorkflow.loading}
          onStartWithMaterials={() => void onStartWorkflow(true)}
          onStartWithoutMaterials={() => void onStartWorkflow(false)}
        />
      )}

      {workflowStarted && editorialWorkflow.loading && (
        <p
          style={{ fontSize: "13px", color: TEXT_DIM, margin: 0 }}
          role="status"
          data-testid="workflow-starting"
        >
          Starting editorial workflow…
        </p>
      )}

      {editorialWorkflow.error && (
        <p style={{ fontSize: "13px", color: "#f87171", margin: 0 }} role="alert">
          {editorialWorkflow.error}
        </p>
      )}
    </div>
  );
}

function WorkflowStepContent({
  project,
  projectId,
  activeStepId,
  sources,
  workflowStarted,
  editorialWorkflow,
  publishedProject,
  onPublished,
}: {
  project: CarouselProjectResponse;
  projectId: string;
  activeStepId: CreateStepId;
  sources: Array<{ title: string; content: string; source_type?: string }>;
  workflowStarted: boolean;
  editorialWorkflow: ReturnType<typeof useEditorialWorkflow>;
  publishedProject: CarouselProjectResponse | null;
  onPublished: (project: CarouselProjectResponse) => void;
}): React.ReactElement {
  const t = useTranslations("create");
  const workflowStepId = resolveStepFromWorkflowPhase(
    editorialWorkflow.state?.current_phase,
  );
  const showWorkflow =
    workflowStarted || editorialWorkflow.hasActiveWorkflow;
  const isFutureStep = isFutureCreateStep(activeStepId, workflowStepId);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {showWorkflow && isFutureStep ? (
        <p
          style={{
            fontSize: "13px",
            color: TEXT_DIM,
            margin: 0,
            padding: "12px 16px",
            background: BG_CARD,
            borderRadius: "8px",
            border: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          {t("futureStep", {
            phase: editorialWorkflow.state?.current_phase ?? "—",
          })}
        </p>
      ) : null}

      {showWorkflow && !isFutureStep ? (
        <CreateWorkflowPanel
          projectId={projectId}
          topic={project.topic}
          audience={project.audience}
          brief={project.niche}
          sources={sources}
          autoStart={
            workflowStarted && !editorialWorkflow.hasActiveWorkflow
          }
          onPublished={() => onPublished(project)}
          workflow={editorialWorkflow}
          viewStepId={activeStepId}
          workflowStepId={workflowStepId}
        />
      ) : (
        <p style={{ fontSize: "13px", color: TEXT_DIM }}>
          {t("startWorkflowHint")}
        </p>
      )}

      {publishedProject && <CarouselPreview project={publishedProject} />}
    </div>
  );
}

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
  const [publishedProject, setPublishedProject] =
    useState<CarouselProjectResponse | null>(null);

  const workflowStepId = resolveStepFromWorkflowPhase(
    editorialWorkflow.state?.current_phase,
  );

  const progressActiveStep =
    editorialWorkflow.hasActiveWorkflow && activeStepId === CREATE_STEP_IDS.BRIEF
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
        <NeonTopBar title="Create Carousel" breadcrumb={[{ label: "project" }]} />
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
            {isPublishStep ? (
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
                    background: "linear-gradient(135deg, #00d4ff 0%, #0090b0 100%)",
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
