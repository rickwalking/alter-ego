/**
 * The create workspace page (AE-0446: behavior pinned before the page was
 * split into a workspace hook and parts). Covers the loading / not-found
 * states, the step routing, starting and retrying the workflow (AE-0009,
 * AE-0415 B26/B30) and the publish-step hand-off.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import type { EditorialWorkflowState } from "@/modules/publishing";
import CreateWorkspacePage from "./page";

const nav = vi.hoisted(() => ({
  push: vi.fn(),
  replace: vi.fn(),
  step: null as string | null,
}));
const hooks = vi.hoisted(() => ({
  project: vi.fn(),
  workflow: vi.fn(),
  workflowOptions: vi.fn(),
  follow: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "p1" }),
  useRouter: () => ({ push: nav.push, replace: nav.replace }),
  useSearchParams: () => ({ get: () => nav.step }),
}));
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));
vi.mock("@/components/atoms/neon-spinner", () => ({
  NeonSpinner: () => <div>spinner</div>,
}));
vi.mock("@/components/organisms/neon-top-bar", () => ({
  NeonTopBar: ({ title }: { title: string }) => <h1>{title}</h1>,
}));
vi.mock("@/modules/editorial", () => ({
  useCarouselProject: () => hooks.project(),
  useEditorialWorkflow: (_id: string, options: unknown) => {
    hooks.workflowOptions(options);
    return hooks.workflow();
  },
  WorkflowFailedCard: ({ onRetry }: { onRetry: () => void }) => (
    <button type="button" onClick={onRetry}>
      retry-card
    </button>
  ),
}));
vi.mock("@/app/dashboard/create/use-follow-workflow-step", () => ({
  useFollowWorkflowStep: (options: unknown) => hooks.follow(options),
}));
vi.mock("@/app/dashboard/create/create-progress-steps", () => ({
  CreateProgressSteps: ({
    activeStepId,
    onStepChange,
    completedStepIds,
  }: {
    activeStepId: string;
    onStepChange: (id: string) => void;
    completedStepIds?: string[];
  }) => (
    <div>
      <span>progress:{activeStepId}</span>
      <span>completed:{completedStepIds?.join(",") ?? "none"}</span>
      <button type="button" onClick={() => onStepChange("publish")}>
        step-publish
      </button>
      <button type="button" onClick={() => onStepChange("outline")}>
        step-outline
      </button>
    </div>
  ),
}));
vi.mock("@/app/dashboard/create/create-workspace-sidebar", () => ({
  CreateWorkspaceSidebar: () => <aside>sidebar</aside>,
}));
vi.mock("@/app/dashboard/create/workspace/brief-step-content", () => ({
  BriefStepContent: ({
    workflowStarted,
    onStartWorkflow,
    onSourcesChange,
    sourceCount,
  }: {
    workflowStarted: boolean;
    onStartWorkflow: (withMaterials: boolean) => Promise<void>;
    onSourcesChange: (sources: unknown[]) => void;
    sourceCount: number;
  }) => (
    <div>
      <span>brief started:{String(workflowStarted)}</span>
      <span>sources:{sourceCount}</span>
      <button
        type="button"
        onClick={() =>
          onSourcesChange([
            { title: "S", content: "C", source_type: "note", id: "x" },
          ])
        }
      >
        add-source
      </button>
      <button type="button" onClick={() => void onStartWorkflow(true)}>
        start-with
      </button>
      <button type="button" onClick={() => void onStartWorkflow(false)}>
        start-without
      </button>
    </div>
  ),
}));
vi.mock("@/app/dashboard/create/workspace/workflow-step-content", () => ({
  WorkflowStepContent: ({ activeStepId }: { activeStepId: string }) => (
    <div>workflow-step:{activeStepId}</div>
  ),
}));

const project = {
  id: "p1",
  topic: "AI",
  audience: "devs",
  niche: "brief text",
  current_phase: "brief",
};

function workflowState(
  overrides: Partial<EditorialWorkflowState> = {},
): EditorialWorkflowState {
  return {
    project_id: "p1",
    current_phase: EDITORIAL_PHASES.CONTENT,
    phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    research_findings: [],
    outline: [],
    slide_drafts: [],
    status: "draft",
    ...overrides,
  };
}

function setWorkflow(
  state: EditorialWorkflowState | null,
  start = vi.fn(async () => workflowState({ current_phase: "research" })),
) {
  hooks.workflow.mockReturnValue({
    state,
    hasActiveWorkflow: state !== null,
    start,
  });
  return start;
}

beforeEach(() => {
  vi.clearAllMocks();
  nav.step = null;
  hooks.project.mockReturnValue({
    data: project,
    isLoading: false,
    isError: false,
  });
  setWorkflow(null);
});

describe("CreateWorkspacePage", () => {
  it("shows a spinner while the project loads", () => {
    hooks.project.mockReturnValue({ isLoading: true, isError: false });
    render(<CreateWorkspacePage />);
    expect(screen.getByText("spinner")).toBeInTheDocument();
  });

  it("shows not-found when the project fails to load", () => {
    hooks.project.mockReturnValue({ isLoading: false, isError: true });
    render(<CreateWorkspacePage />);
    expect(screen.getByText("errors.projectNotFound")).toBeInTheDocument();
  });

  it("does not fetch workflow state for a project that never started", () => {
    render(<CreateWorkspacePage />);
    expect(hooks.workflowOptions).toHaveBeenCalledWith({ initialFetch: false });
  });

  it("fetches workflow state once the project has a phase", () => {
    hooks.project.mockReturnValue({
      data: { ...project, current_phase: "content" },
      isLoading: false,
      isError: false,
    });
    render(<CreateWorkspacePage />);
    expect(hooks.workflowOptions).toHaveBeenCalledWith({ initialFetch: true });
  });

  it("starts with the materials and opens the step the workflow is on", async () => {
    const start = setWorkflow(null);
    render(<CreateWorkspacePage />);
    expect(screen.getByText("progress:brief")).toBeInTheDocument();
    expect(screen.getByText("completed:none")).toBeInTheDocument();
    fireEvent.click(screen.getByText("add-source"));
    expect(screen.getByText("sources:1")).toBeInTheDocument();
    fireEvent.click(screen.getByText("start-with"));
    expect(screen.getByText("brief started:true")).toBeInTheDocument();
    await waitFor(() =>
      expect(nav.push).toHaveBeenCalledWith(
        "/dashboard/create/p1?step=research",
      ),
    );
    expect(start).toHaveBeenCalledWith({
      topic: "AI",
      audience: "devs",
      brief: "brief text",
      sources: [{ title: "S", content: "C", source_type: "note" }],
    });
  });

  it("starts without materials when asked", async () => {
    const start = setWorkflow(null);
    render(<CreateWorkspacePage />);
    fireEvent.click(screen.getByText("add-source"));
    fireEvent.click(screen.getByText("start-without"));
    await waitFor(() => expect(start).toHaveBeenCalled());
    expect(start).toHaveBeenCalledWith(
      expect.objectContaining({ sources: [] }),
    );
  });

  it("re-enables the start when it fails", async () => {
    setWorkflow(
      null,
      vi.fn(async () => {
        throw new Error("boom");
      }),
    );
    render(<CreateWorkspacePage />);
    fireEvent.click(screen.getByText("start-with"));
    await waitFor(() =>
      expect(screen.getByText("brief started:false")).toBeInTheDocument(),
    );
    expect(nav.push).not.toHaveBeenCalled();
  });

  it("moves an active workflow off the brief step", () => {
    setWorkflow(workflowState());
    render(<CreateWorkspacePage />);
    expect(screen.getByText("progress:content")).toBeInTheDocument();
    expect(
      screen.getByText("completed:brief,research,outline"),
    ).toBeInTheDocument();
    expect(nav.replace).toHaveBeenCalledWith(
      "/dashboard/create/p1?step=content",
    );
    expect(hooks.follow).toHaveBeenCalledWith(
      expect.objectContaining({
        activeStepId: "brief",
        workflowStepId: "content",
        hasActiveWorkflow: true,
      }),
    );
  });

  it("follows the workflow with a replace", () => {
    setWorkflow(workflowState());
    nav.step = "content";
    render(<CreateWorkspacePage />);
    expect(nav.replace).not.toHaveBeenCalled();
    const { onFollow } = hooks.follow.mock.calls[0]?.[0] as {
      onFollow: (id: string) => void;
    };
    onFollow("images");
    expect(nav.replace).toHaveBeenCalledWith(
      "/dashboard/create/p1?step=images",
    );
  });

  it("routes step changes, sending publish to its own page", () => {
    setWorkflow(workflowState());
    nav.step = "content";
    render(<CreateWorkspacePage />);
    expect(screen.getByText("workflow-step:content")).toBeInTheDocument();
    fireEvent.click(screen.getByText("step-publish"));
    expect(nav.push).toHaveBeenCalledWith("/dashboard/create/p1/publish");
    fireEvent.click(screen.getByText("step-outline"));
    expect(nav.push).toHaveBeenCalledWith("/dashboard/create/p1?step=outline");
  });

  it("hands the publish step off to the publish page", () => {
    setWorkflow(workflowState());
    nav.step = "publish";
    render(<CreateWorkspacePage />);
    expect(screen.getByText("publishStep.hint")).toBeInTheDocument();
    fireEvent.click(screen.getByText("publishStep.goToPublish"));
    expect(nav.push).toHaveBeenCalledWith("/dashboard/create/p1/publish");
  });

  it("retries a failed workflow and opens the outline", async () => {
    const start = setWorkflow(
      workflowState({ phase_status: WORKFLOW_PHASE_STATUS.FAILED }),
    );
    nav.step = "content";
    render(<CreateWorkspacePage />);
    fireEvent.click(screen.getByText("retry-card"));
    await waitFor(() =>
      expect(nav.push).toHaveBeenCalledWith(
        "/dashboard/create/p1?step=outline",
      ),
    );
    expect(start).toHaveBeenCalledTimes(1);
  });
});
