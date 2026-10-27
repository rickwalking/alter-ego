"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import {
  CREATE_STEP_IDS,
  parseCreateStepId,
  resolveStepFromWorkflowPhase,
  type CreateStepId,
} from "@/app/dashboard/create/step-ids";
import {
  useCarouselProject,
  useEditorialWorkflow,
  useGenerationLog,
} from "@/modules/editorial";
import type { GenerationLogView } from "@/modules/editorial";
import type { ContentSource } from "@/modules/publishing";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import { createRetryWorkflowHandler } from "@/app/dashboard/create/[id]/create-retry-handler";
import { useFollowWorkflowStep } from "@/app/dashboard/create/use-follow-workflow-step";

/** Phases of a project whose editorial workflow never started. */
const NOT_STARTED_PHASES: ReadonlySet<string> = new Set(["", "brief"]);

type EditorialWorkflow = ReturnType<typeof useEditorialWorkflow>;
type CarouselProject = NonNullable<
  ReturnType<typeof useCarouselProject>["data"]
>;
interface WorkflowSource {
  title: string;
  content: string;
  source_type?: string;
}

/** Push / replace the workspace URL of one step (publish has its own page). */
export interface WorkspaceNavigation {
  /** Push a step's URL (publish included). */
  pushStep: (stepId: CreateStepId) => void;
  /** Push a step, sending publish to its own page. */
  goToStep: (stepId: CreateStepId) => void;
  replaceStep: (stepId: CreateStepId) => void;
  goToPublish: () => void;
}

function useWorkspaceNavigation(projectId: string): WorkspaceNavigation {
  const router = useRouter();
  const stepUrl = useCallback(
    (stepId: CreateStepId) =>
      `${DASHBOARD_ROUTES.CREATE_WORKSPACE(projectId)}?step=${stepId}`,
    [projectId],
  );
  const goToPublish = useCallback(
    () => router.push(DASHBOARD_ROUTES.CREATE_PUBLISH(projectId)),
    [projectId, router],
  );
  const pushStep = useCallback(
    (stepId: CreateStepId): void => router.push(stepUrl(stepId)),
    [router, stepUrl],
  );
  const goToStep = useCallback(
    (stepId: CreateStepId): void => {
      if (stepId === CREATE_STEP_IDS.PUBLISH) {
        goToPublish();
        return;
      }
      pushStep(stepId);
    },
    [goToPublish, pushStep],
  );
  const replaceStep = useCallback(
    (stepId: CreateStepId): void => router.replace(stepUrl(stepId)),
    [router, stepUrl],
  );
  return { pushStep, goToStep, replaceStep, goToPublish };
}

/** An active workflow never sits on the brief step: open its real step. */
function useLeaveBriefStep(
  activeStepId: CreateStepId,
  workflowStepId: CreateStepId,
  {
    hasActiveWorkflow,
    replaceStep,
  }: {
    hasActiveWorkflow: boolean;
    replaceStep: (stepId: CreateStepId) => void;
  },
): void {
  useEffect(() => {
    if (!hasActiveWorkflow || activeStepId !== CREATE_STEP_IDS.BRIEF) {
      return;
    }
    if (workflowStepId !== CREATE_STEP_IDS.BRIEF) {
      replaceStep(workflowStepId);
    }
  }, [activeStepId, hasActiveWorkflow, replaceStep, workflowStepId]);
}

/** Starting the workflow from the brief, and retrying a failed one. */
export interface WorkflowStarter {
  workflowStarted: boolean;
  handleStartWorkflow: (withMaterials: boolean) => Promise<void>;
  retrying: boolean;
  handleRetryWorkflow: () => Promise<void>;
}

/**
 * The retry is idempotent: duplicate clicks trigger a single restart, because
 * the `retrying` guard short-circuits in-flight clicks before the button's
 * disabled state propagates. On failure `retrying` resets, so the button
 * re-enables and the error card stays (see create-retry-handler.ts).
 */
function useRetryWorkflow(
  project: CarouselProject | undefined,
  start: EditorialWorkflow["start"],
  {
    sources,
    pushStep,
  }: {
    sources: WorkflowSource[];
    pushStep: WorkspaceNavigation["pushStep"];
  },
): Pick<WorkflowStarter, "retrying" | "handleRetryWorkflow"> {
  const [retrying, setRetrying] = useState(false);
  const handleRetryWorkflow = useCallback(
    (): Promise<void> =>
      createRetryWorkflowHandler({
        project,
        retrying,
        setRetrying,
        start,
        sources,
        navigateOnSuccess: () => pushStep(CREATE_STEP_IDS.OUTLINE),
      })(),
    [project, pushStep, retrying, sources, start],
  );

  return { retrying, handleRetryWorkflow };
}

/** After a start it opens the gate the workflow is really on. */
function useWorkflowStarter(
  project: CarouselProject | undefined,
  editorialWorkflow: EditorialWorkflow,
  {
    sources,
    navigation,
  }: {
    sources: WorkflowSource[];
    navigation: WorkspaceNavigation;
  },
): WorkflowStarter {
  const [workflowStarted, setWorkflowStarted] = useState(false);
  const { start } = editorialWorkflow;
  const { pushStep } = navigation;

  const handleStartWorkflow = useCallback(
    async (withMaterials: boolean): Promise<void> => {
      if (!project) {
        return;
      }
      setWorkflowStarted(true);
      try {
        const started = await start({
          topic: project.topic,
          audience: project.audience,
          brief: project.niche,
          sources: withMaterials ? sources : [],
        });
        pushStep(resolveStepFromWorkflowPhase(started.current_phase));
      } catch {
        setWorkflowStarted(false);
      }
    },
    [project, pushStep, sources, start],
  );

  const { retrying, handleRetryWorkflow } = useRetryWorkflow(project, start, {
    sources,
    pushStep,
  });

  return {
    workflowStarted,
    handleStartWorkflow,
    retrying,
    handleRetryWorkflow,
  };
}

function toWorkflowSources(sources: ContentSource[]): WorkflowSource[] {
  return sources.map((source) => ({
    title: source.title,
    content: source.content,
    source_type: source.source_type,
  }));
}

/** Everything the create workspace page renders from. */
export interface CreateWorkspace {
  projectId: string;
  activeStepId: CreateStepId;
  workflowStepId: CreateStepId;
  projectQuery: ReturnType<typeof useCarouselProject>;
  editorialWorkflow: EditorialWorkflow;
  generationLog: GenerationLogView;
  projectSources: ContentSource[];
  setProjectSources: (sources: ContentSource[]) => void;
  sources: WorkflowSource[];
  publishedProject: CarouselProjectResponse | null;
  setPublishedProject: (project: CarouselProjectResponse | null) => void;
  navigation: WorkspaceNavigation;
  starter: WorkflowStarter;
}

/**
 * A fresh project has no workflow state (GET answers 404), so its workflow is
 * not fetched on mount.
 */
export function useCreateWorkspace(): CreateWorkspace {
  const projectId = useParams<{ id: string }>().id;
  const activeStepId = parseCreateStepId(useSearchParams().get("step"));
  const projectQuery = useCarouselProject(projectId);
  const project = projectQuery.data;
  const editorialWorkflow = useEditorialWorkflow(projectId, {
    initialFetch:
      project !== undefined &&
      !NOT_STARTED_PHASES.has(project.current_phase ?? ""),
  });
  const generationLog = useGenerationLog(projectId, editorialWorkflow.state);
  const [projectSources, setProjectSources] = useState<ContentSource[]>([]);
  const [publishedProject, setPublishedProject] =
    useState<CarouselProjectResponse | null>(null);
  const navigation = useWorkspaceNavigation(projectId);
  const { hasActiveWorkflow } = editorialWorkflow;
  const workflowStepId = resolveStepFromWorkflowPhase(
    editorialWorkflow.state?.current_phase,
  );
  useFollowWorkflowStep({
    activeStepId,
    workflowStepId,
    hasActiveWorkflow,
    onFollow: navigation.replaceStep,
  });
  useLeaveBriefStep(activeStepId, workflowStepId, {
    hasActiveWorkflow,
    replaceStep: navigation.replaceStep,
  });
  const sources = toWorkflowSources(projectSources);
  const starter = useWorkflowStarter(project, editorialWorkflow, {
    sources,
    navigation,
  });

  return {
    projectId,
    activeStepId,
    workflowStepId,
    projectQuery,
    editorialWorkflow,
    generationLog,
    projectSources,
    setProjectSources,
    sources,
    publishedProject,
    setPublishedProject,
    navigation,
    starter,
  };
}
