// AE-0414 — Gherkin: frontend/tests/features/content-review-manual-fixes-ae0414.feature
// Scenario: A rejected manual fix shows a translated message and no page error
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { API_ENDPOINTS, HTTP_STATUS } from "@/constants/api";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
} from "@/modules/editorial/workspace/types-ai";
import { useEditorialWorkflow } from "./use-editorial-workflow";

vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";

const mockFetch = vi.mocked(authenticatedFetch);

class SilentEventSource {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;
  readyState = SilentEventSource.CONNECTING;
  onmessage: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onopen: (() => void) | null = null;
  addEventListener(): void {}
  removeEventListener(): void {}
  close(): void {
    this.readyState = SilentEventSource.CLOSED;
  }
}

const originalEventSource = globalThis.EventSource;

const contentState: EditorialWorkflowState = {
  project_id: "project-1",
  current_phase: "content",
  phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
  research_findings: [],
  outline: [],
  slide_drafts: [],
  status: "draft",
  lock_version: 3,
};

const editedSlide: LocalizedSlideReview = {
  slide_index: 1,
  slide_type: "intro",
  presentation_pt: { heading: "Título", body: "Corpo" },
  presentation_en: { heading: "Title", body: "Body" },
};

function answerResume(status: number, detail: string): void {
  mockFetch.mockImplementation(async (url, init) => {
    if (
      url === API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME("project-1") &&
      init?.method === "POST"
    ) {
      return {
        ok: false,
        status,
        json: async () => ({ detail }),
      } as Response;
    }
    return { ok: true, json: async () => contentState } as Response;
  });
}

beforeEach(() => {
  mockFetch.mockReset();
  // @ts-expect-error — swap in the mock for the duration of each test.
  globalThis.EventSource = SilentEventSource;
});

afterEach(() => {
  globalThis.EventSource = originalEventSource;
});

async function renderWorkflow(): Promise<
  ReturnType<
    typeof renderHook<ReturnType<typeof useEditorialWorkflow>, unknown>
  >
> {
  const hook = renderHook(() => useEditorialWorkflow("project-1"));
  await waitFor(() => {
    expect(hook.result.current.state).not.toBeNull();
  });
  return hook;
}

describe("useEditorialWorkflow manual fixes (AE-0414 B02)", () => {
  it("translates a 422 code and resolves an edits-only revise", async () => {
    answerResume(
      HTTP_STATUS.UNPROCESSABLE_ENTITY,
      "edited_localized_slides_phase_not_allowed",
    );
    const { result } = await renderWorkflow();

    let outcome: EditorialWorkflowState | null | undefined;
    await act(async () => {
      outcome = await result.current.revise("", {
        editedLocalizedSlides: [editedSlide],
      });
    });

    expect(outcome).toBeNull();
    expect(result.current.error).toBe(
      "Manual fixes cannot be submitted at this step right now. Your edits are still here; refresh the page and try again.",
    );
    expect(result.current.error).not.toContain("_");
  });

  it("still rejects a feedback revise so its caller keeps the feedback", async () => {
    answerResume(HTTP_STATUS.UNPROCESSABLE_ENTITY, "revise_feedback_required");
    const { result } = await renderWorkflow();

    await act(async () => {
      await expect(result.current.revise("Rewrite it")).rejects.toThrow(
        "Write your feedback before requesting a revision.",
      );
    });
  });

  it("keeps an unknown code as the message", async () => {
    answerResume(HTTP_STATUS.UNPROCESSABLE_ENTITY, "some_new_code");
    const { result } = await renderWorkflow();

    await act(async () => {
      await result.current.revise("", { editedLocalizedSlides: [editedSlide] });
    });

    expect(result.current.error).toBe("some_new_code");
  });
});
