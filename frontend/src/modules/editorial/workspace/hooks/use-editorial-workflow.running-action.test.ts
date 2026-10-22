/**
 * Review actions, the state read and the start call of the editorial workflow
 * hook: which action is running, a 404 read and a project change.
 */

import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { API_ENDPOINTS, HTTP_STATUS } from "@/constants/api";
import { EDITORIAL_REVIEW_ACTIONS } from "@/constants/blog-ai";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/editorial/workspace/types-ai";
import { useEditorialWorkflow } from "./use-editorial-workflow";

vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";

const mockFetch = vi.mocked(authenticatedFetch);

class IdleEventSource {
  addEventListener = vi.fn();
  removeEventListener = vi.fn();
  close = vi.fn();
}

const PROJECT_ID = "project-1";
const OTHER_PROJECT_ID = "project-2";

const researchState: EditorialWorkflowState = {
  project_id: PROJECT_ID,
  current_phase: "research",
  phase_status: WORKFLOW_PHASE_STATUS.IN_PROGRESS,
  research_findings: [],
  outline: [],
  slide_drafts: [],
  status: "draft",
  lock_version: 1,
};

function jsonResponse(
  body: unknown,
  init: { ok: boolean; status: number },
): Response {
  return { ...init, json: () => Promise.resolve(body) } as Response;
}

function answerRunInProgress(state: EditorialWorkflowState): void {
  mockFetch.mockImplementation((url, init) => {
    if (
      url === API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME(PROJECT_ID) &&
      init?.method === "POST"
    ) {
      return Promise.resolve(
        jsonResponse(
          { detail: "resume_already_in_progress" },
          { ok: false, status: HTTP_STATUS.CONFLICT },
        ),
      );
    }
    return Promise.resolve(
      jsonResponse(state, { ok: true, status: HTTP_STATUS.OK }),
    );
  });
}

beforeEach(() => {
  mockFetch.mockReset();
  vi.stubGlobal("EventSource", IdleEventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useEditorialWorkflow review actions", () => {
  // Scenario: The banner names a revise as the running action
  it("reports revise as the running action after a revise", async () => {
    answerRunInProgress(researchState);
    const { result } = renderHook(() => useEditorialWorkflow(PROJECT_ID));
    await waitFor(() => {
      expect(result.current.state?.current_phase).toBe("research");
    });

    await act(async () => {
      await result.current.revise("Rewrite it").catch(() => null);
    });

    expect(result.current.runningAction).toBe(EDITORIAL_REVIEW_ACTIONS.REVISE);
  });

  // Scenario: An action taken before any state exists is still recorded
  it("reports approve as the running action when approved before any state", async () => {
    answerRunInProgress({ ...researchState, current_phase: "" });
    const { result } = renderHook(() =>
      useEditorialWorkflow(PROJECT_ID, { initialFetch: false }),
    );
    expect(result.current.state).toBeNull();

    await act(async () => {
      await result.current.approve();
    });

    expect(result.current.runningAction).toBe(EDITORIAL_REVIEW_ACTIONS.APPROVE);
  });
});

describe("useEditorialWorkflow state read", () => {
  // Scenario: A 404 means the workflow does not exist yet
  it("keeps the state empty when the read answers 404", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(researchState, { ok: true, status: HTTP_STATUS.NOT_FOUND }),
    );
    const { result } = renderHook(() => useEditorialWorkflow(PROJECT_ID));

    let refreshed: EditorialWorkflowState | null | undefined;
    await act(async () => {
      refreshed = await result.current.refreshState();
    });

    expect(refreshed).toBeNull();
    expect(result.current.state).toBeNull();
  });
});

describe("useEditorialWorkflow start", () => {
  // Scenario: Starting after a project change targets the new project
  it("starts the workflow of the project of the latest render", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(
        { ...researchState, project_id: OTHER_PROJECT_ID },
        { ok: true, status: HTTP_STATUS.OK },
      ),
    );
    const { result, rerender } = renderHook(
      (projectId: string) =>
        useEditorialWorkflow(projectId, { initialFetch: false }),
      { initialProps: PROJECT_ID },
    );
    rerender(OTHER_PROJECT_ID);

    await act(async () => {
      await result.current.start({
        topic: "Security",
        audience: "Developers",
        brief: "Brief",
        sources: [],
      });
    });

    const startUrls = mockFetch.mock.calls.map(([url]) => url);
    expect(startUrls).toContain(
      API_ENDPOINTS.CAROUSEL_WORKFLOW_START(OTHER_PROJECT_ID),
    );
    expect(startUrls).not.toContain(
      API_ENDPOINTS.CAROUSEL_WORKFLOW_START(PROJECT_ID),
    );
  });
});
