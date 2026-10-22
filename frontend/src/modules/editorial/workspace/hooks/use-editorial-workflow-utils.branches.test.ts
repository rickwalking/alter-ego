/**
 * Branch-level assertions for the editorial workflow utils: payload
 * resolution identity, progress normalisation and full-vs-partial merging.
 */

import { describe, it, expect } from "vitest";
import { EDITORIAL_WORKFLOW_SSE_EVENTS } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/editorial";
import type { WorkflowEventPayload } from "./types";
import {
  mergeWorkflowState,
  normalizeProgressPayload,
  resolveWorkflowEventPayload,
} from "./use-editorial-workflow-utils";

const PROJECT_ID = "project-1";

const previousState: EditorialWorkflowState = {
  project_id: PROJECT_ID,
  current_phase: "previous-phase",
  phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
  research_findings: [],
  outline: [],
  slide_drafts: [],
  phase_progress: { current: 2 },
  status: "draft",
};

const fullLists = {
  research_findings: [],
  outline: [],
  slide_drafts: [],
};

describe("normalizeProgressPayload branches", () => {
  // Scenario: a non-object phase_progress is not returned verbatim
  it("ignores a phase_progress that is not an object", () => {
    const payload = {
      phase_progress: "busy",
    } as unknown as WorkflowEventPayload;

    expect(normalizeProgressPayload(payload)).toBeUndefined();
  });

  // Scenario: a null phase_progress yields no progress
  it("returns undefined for a null phase_progress", () => {
    expect(normalizeProgressPayload({ phase_progress: null })).toBeUndefined();
  });

  // Scenario: a progress event without fields reports null progress
  it("returns null for a progress event that carries no progress fields", () => {
    expect(
      normalizeProgressPayload({
        event: EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
      }),
    ).toBeNull();
  });
});

describe("resolveWorkflowEventPayload identity", () => {
  // Scenario: artifact data on a non-artifact event is ignored
  it("returns the same payload for a non-artifact event carrying artifact data", () => {
    const payload: WorkflowEventPayload = {
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
      artifact_type: "outline",
      data: [{ title: "x" }],
    };

    expect(resolveWorkflowEventPayload(payload)).toBe(payload);
  });

  // Scenario: an unknown artifact type leaves the payload untouched
  it("returns the same payload for an unknown artifact type", () => {
    const payload: WorkflowEventPayload = {
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
      artifact_type: "unknown_artifact",
      data: [1],
    };

    expect(resolveWorkflowEventPayload(payload)).toBe(payload);
  });

  // Scenario: an artifact event without data leaves the payload untouched
  it("returns the same payload for a known artifact type without data", () => {
    const payload: WorkflowEventPayload = {
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.ARTIFACT,
      artifact_type: "outline",
    };

    expect(resolveWorkflowEventPayload(payload)).toBe(payload);
  });

  // Scenario: a gate payload is only merged for review-required events
  it("returns the same payload for a gate payload on another event", () => {
    const payload: WorkflowEventPayload = {
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
      gate_payload: { current_phase: "outline" },
    };

    expect(resolveWorkflowEventPayload(payload)).toBe(payload);
  });

  // Scenario: a review-required event without a gate payload is untouched
  it("returns the same payload for review_required without a gate payload", () => {
    const payload: WorkflowEventPayload = {
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
      gate_payload: null,
    };

    expect(resolveWorkflowEventPayload(payload)).toBe(payload);
  });

  // Scenario: a non-object gate payload is never spread into the payload
  it("returns the same payload for review_required with a non-object gate", () => {
    const payload = {
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.REVIEW_REQUIRED,
      gate_payload: "gate",
    } as unknown as WorkflowEventPayload;

    expect(resolveWorkflowEventPayload(payload)).toBe(payload);
  });
});

describe("mergeWorkflowState full versus partial payloads", () => {
  // Scenario: a full snapshot prefers current_phase over phase
  it.each([
    ["with a matching project id", { project_id: PROJECT_ID }],
    ["without a project id", {}],
  ])("prefers current_phase for a full snapshot %s", (_title, identity) => {
    const merged = mergeWorkflowState(PROJECT_ID, previousState, {
      ...identity,
      current_phase: "current",
      phase: "legacy",
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      ...fullLists,
    });

    expect(merged.current_phase).toBe("current");
  });

  // Scenario: a snapshot with no phase falls back to the previous phase
  it("keeps the previous phase when the snapshot carries no phase", () => {
    const merged = mergeWorkflowState(PROJECT_ID, previousState, {
      phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
      ...fullLists,
    });

    expect(merged.current_phase).toBe("previous-phase");
  });

  // Scenario: a snapshot with no phase status keeps the previous status
  it("keeps the previous phase status when the snapshot carries none", () => {
    const merged = mergeWorkflowState(PROJECT_ID, previousState, {
      current_phase: "current",
      ...fullLists,
    });

    expect(merged.phase_status).toBe(WORKFLOW_PHASE_STATUS.AWAITING_HUMAN);
  });

  // Scenario: partial events default missing lists to empty arrays
  it("defaults missing lists to empty arrays without previous state", () => {
    const merged = mergeWorkflowState(PROJECT_ID, null, {
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.PROGRESS,
    });

    expect(merged.research_findings).toEqual([]);
    expect(merged.outline).toEqual([]);
    expect(merged.slide_drafts).toEqual([]);
    expect(merged.current_phase).toBe("");
  });

  // Scenario: progress carries forward when the event brings none
  it("carries the previous phase_progress when the event has no progress", () => {
    const merged = mergeWorkflowState(PROJECT_ID, previousState, {
      event: EDITORIAL_WORKFLOW_SSE_EVENTS.PHASE_CHANGED,
    });

    expect(merged.phase_progress).toEqual({ current: 2 });
  });
});
