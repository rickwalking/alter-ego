import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  EDITORIAL_PHASES,
  EDITORIAL_WORKFLOW_STATUS,
  EDITORIAL_WORKFLOW_TRANSPORT_MODE,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import { CREATE_STEP_IDS } from "@/app/dashboard/create/step-ids";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
} from "@/modules/publishing";
import {
  approvalGates,
  revisionActions,
  stepVisibility,
  useContentEdits,
  useWorkflowFeedback,
  useWorkflowLifecycle,
  type CreateWorkflowApi,
} from "./create-workflow-panel-state";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

const baseState: EditorialWorkflowState = {
  project_id: "p1",
  current_phase: EDITORIAL_PHASES.CONTENT,
  phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
  research_findings: [],
  outline: [],
  slide_drafts: [{ slide_index: 1, slide_type: "hook", title: "Hook" }],
  status: "draft",
  lock_version: 3,
};

function buildWorkflow(
  overrides: Partial<CreateWorkflowApi> = {},
): CreateWorkflowApi {
  return {
    state: baseState,
    phaseEvents: [],
    loading: false,
    error: null,
    transportMode: EDITORIAL_WORKFLOW_TRANSPORT_MODE.SSE,
    reconnectLiveUpdates: vi.fn(),
    start: vi.fn(async () => baseState),
    resume: vi.fn(async () => baseState),
    refreshState: vi.fn(async () => baseState),
    approve: vi.fn(async () => baseState),
    revise: vi.fn(async () => baseState),
    awaitingHumanReview: true,
    hasActiveWorkflow: false,
    runningAction: null,
    ...overrides,
  };
}

function editedCopy(slides: LocalizedSlideReview[]): LocalizedSlideReview[] {
  return slides.map((slide) => ({
    ...slide,
    presentation_pt: { ...slide.presentation_pt, title: "Edited title" },
  }));
}

const startInput = { topic: "AI", audience: "devs", brief: "b" };

describe("useWorkflowLifecycle", () => {
  it("starts the workflow once when auto-start is on", () => {
    const workflow = buildWorkflow();
    const { rerender } = renderHook(() =>
      useWorkflowLifecycle(
        workflow,
        { autoStart: true, input: startInput },
        undefined,
      ),
    );
    rerender();
    expect(workflow.start).toHaveBeenCalledTimes(1);
    expect(workflow.start).toHaveBeenCalledWith({ ...startInput, sources: [] });
  });

  it("does not start when a workflow is already active", () => {
    const workflow = buildWorkflow({ hasActiveWorkflow: true });
    renderHook(() =>
      useWorkflowLifecycle(
        workflow,
        { autoStart: true, input: startInput },
        undefined,
      ),
    );
    expect(workflow.start).not.toHaveBeenCalled();
  });

  it("reports an approved publish", () => {
    const onPublished = vi.fn();
    const workflow = buildWorkflow({
      state: {
        ...baseState,
        workflow_status: EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH,
      },
    });
    renderHook(() =>
      useWorkflowLifecycle(workflow, { input: startInput }, onPublished),
    );
    expect(onPublished).toHaveBeenCalledTimes(1);
    expect(workflow.start).not.toHaveBeenCalled();
  });
});

describe("useContentEdits", () => {
  it("keeps edits while the lock version holds and drops them on a new one", () => {
    const { result, rerender } = renderHook(
      ({ state }) => useContentEdits(state),
      { initialProps: { state: baseState } },
    );
    expect(result.current.contentHasEdits).toBe(false);
    act(() => {
      result.current.setEditedContentSlides(
        editedCopy(result.current.contentSlides),
      );
    });
    expect(result.current.contentHasEdits).toBe(true);
    expect(result.current.contentSlides[0]?.presentation_pt.title).toBe(
      "Edited title",
    );

    rerender({ state: { ...baseState } });
    expect(result.current.contentHasEdits).toBe(true);

    rerender({ state: { ...baseState, lock_version: 4 } });
    expect(result.current.contentHasEdits).toBe(false);
    expect(result.current.contentSlides[0]?.presentation_pt.title).not.toBe(
      "Edited title",
    );
  });

  it("works with no state and with no lock version", () => {
    const { result, rerender } = renderHook(
      ({ state }) => useContentEdits(state),
      {
        initialProps: {
          state: null as EditorialWorkflowState | null,
        },
      },
    );
    expect(result.current.contentSlides).toEqual([]);
    rerender({ state: { ...baseState, lock_version: undefined } });
    expect(result.current.contentHasEdits).toBe(false);
    act(() => {
      result.current.setEditedContentSlides(
        editedCopy(result.current.contentSlides),
      );
    });
    expect(result.current.contentHasEdits).toBe(true);
  });
});

describe("useWorkflowFeedback", () => {
  it("requires feedback before revising", () => {
    const revise = vi.fn(async () => baseState);
    const { result } = renderHook(() => useWorkflowFeedback(baseState, revise));
    act(() => result.current.handleRevise());
    expect(result.current.feedbackError).toBe("feedback.required");
    expect(revise).not.toHaveBeenCalled();
  });

  it("sends feedback back to the chosen phase at final review", async () => {
    const revise = vi.fn(async () => baseState);
    const state = {
      ...baseState,
      current_phase: EDITORIAL_PHASES.FINAL_REVIEW,
    };
    const { result } = renderHook(() => useWorkflowFeedback(state, revise));
    act(() => result.current.setFeedback("  tighten slide 2  "));
    await act(async () => result.current.handleRevise());
    expect(revise).toHaveBeenCalledWith("tighten slide 2", {
      targetPhase: EDITORIAL_PHASES.CONTENT,
    });
    expect(result.current.feedback).toBe("");
    expect(result.current.feedbackError).toBeNull();
  });

  it("revises without a target phase outside final review", async () => {
    const revise = vi.fn(async () => baseState);
    const { result } = renderHook(() => useWorkflowFeedback(baseState, revise));
    act(() => result.current.setFeedback("shorter"));
    await act(async () => result.current.handleRevise());
    expect(revise).toHaveBeenCalledWith("shorter", undefined);
  });
});

describe("approvalGates", () => {
  const content = { contentSlides: [], contentHasEdits: false };

  it("blocks a design revise on a recovery hint", () => {
    const gates = approvalGates(
      {
        ...baseState,
        current_phase: EDITORIAL_PHASES.DESIGN,
        design_recovery_hint: "edit slide 3",
      },
      content,
    );
    expect(gates.designReviseBlocked).toBe(true);
    expect(gates.editBudgetBlocked).toBe(false);
  });

  it("shows the publish link once approved for publish", () => {
    const gates = approvalGates(
      {
        ...baseState,
        workflow_status: EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH,
      },
      content,
    );
    expect(gates.showPublishLink).toBe(true);
    expect(gates.designReviseBlocked).toBe(false);
  });
});

describe("stepVisibility", () => {
  it("marks the live content step editable", () => {
    const view = stepVisibility(
      baseState,
      {
        viewStepId: CREATE_STEP_IDS.CONTENT,
        workflowStepId: CREATE_STEP_IDS.CONTENT,
      },
      true,
    );
    expect(view).toMatchObject({
      isHistoricalStep: false,
      isLiveStep: true,
      showLiveControls: true,
      contentEditable: true,
      showPhaseReview: true,
      showImagePromptReview: false,
    });
  });

  it("shows a past step read-only", () => {
    const view = stepVisibility(
      baseState,
      {
        viewStepId: CREATE_STEP_IDS.RESEARCH,
        workflowStepId: CREATE_STEP_IDS.CONTENT,
      },
      true,
    );
    expect(view.isHistoricalStep).toBe(true);
    expect(view.isLiveStep).toBe(false);
    expect(view.contentEditable).toBe(false);
  });

  it("shows nothing to review before a workflow exists", () => {
    const view = stepVisibility(
      null,
      {
        viewStepId: CREATE_STEP_IDS.IMAGES,
        workflowStepId: CREATE_STEP_IDS.IMAGES,
      },
      false,
    );
    expect(view.isHistoricalStep).toBe(false);
    expect(view.showPhaseReview).toBe(false);
    expect(view.showImagePromptReview).toBe(false);
  });
});

describe("revisionActions", () => {
  it("locks actions while a run executes", () => {
    const workflow = buildWorkflow({
      state: { ...baseState, phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS },
    });
    const actions = revisionActions(workflow, true);
    expect(actions.actionsLocked).toBe(true);
    expect(actions.designRecovery.disabled).toBe(true);
    expect(actions.contentManualFixes.submitting).toBe(true);
  });

  it("disables design recovery off the live controls", () => {
    const actions = revisionActions(buildWorkflow(), false);
    expect(actions.actionsLocked).toBe(false);
    expect(actions.designRecovery.disabled).toBe(true);
  });

  it("revises with the edited slides or a content send-back", () => {
    const workflow = buildWorkflow();
    const actions = revisionActions(workflow, true);
    actions.contentManualFixes.onSubmit([]);
    actions.designRecovery.onSendBackToContent("redo");
    expect(workflow.revise).toHaveBeenCalledWith("", {
      editedLocalizedSlides: [],
    });
    expect(workflow.revise).toHaveBeenCalledWith("redo", {
      targetPhase: EDITORIAL_PHASES.CONTENT,
    });
  });
});
