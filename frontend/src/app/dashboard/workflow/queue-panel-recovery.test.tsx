/** Queue-panel recovery, timing, accessibility and unstaged-row regressions. */
import { fireEvent, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QUEUE_ACTION } from "@/constants/workflow";
import en from "@/i18n/locales/en.json";
import {
  makeQueueBoard as board,
  makeQueueItem as item,
  queueActionName,
  renderQueuePanel as renderPanel,
} from "./queue-panel.test-utils";

const labels = en.workflow.queue;
const reprocessLabels = en.workflow.reprocess;

afterEach(() => vi.useRealTimers());

describe("QueuePanel recovery findings", () => {
  /** Scenario: Retry waits do not invent a queue position */
  it("renders no position for a retry-wait row with a null position", () => {
    renderPanel(
      board({
        active: [
          item({
            status: "retry_wait",
            position: null,
            next_attempt_at: "2026-10-24T14:30:00Z",
            can_reprocess: true,
            refusal_code: null,
            stuck_kind: "retry_wait",
          }),
        ],
      }),
    );
    const row = screen.getByRole("listitem");
    expect(row).not.toHaveTextContent("#0");
    expect(row).not.toHaveTextContent("#");
    expect(row).toHaveTextContent("Next try at 11:30");
  });

  /** Scenario: Running liveness uses only attributed timestamps */
  it("shows started time and heartbeat age for a running row", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-10-24T14:05:00Z"));
    renderPanel(
      board({
        active: [
          item({
            status: "running",
            started_at: "2026-10-24T14:00:00Z",
            run_heartbeat_at: "2026-10-24T14:00:00Z",
            refusal_code: "fresh_running",
          }),
        ],
      }),
    );
    const row = screen.getByRole("listitem");
    expect(row).toHaveTextContent("started 11:00");
    expect(row).toHaveTextContent("last heartbeat 5m ago");
    expect(row).not.toHaveTextContent("NaN");
  });

  /** Scenario: Running liveness uses only attributed timestamps */
  it("omits missing running heartbeat age and stale queued liveness", () => {
    renderPanel(
      board({
        active: [
          item({
            id: "running-null",
            status: "running",
            started_at: "2026-10-24T14:00:00Z",
            refusal_code: "fresh_running",
          }),
          item({
            id: "queued-stale",
            title: "Queued theme",
            started_at: "2026-10-24T14:00:00Z",
            run_heartbeat_at: "2026-10-24T14:00:00Z",
          }),
        ],
      }),
    );
    const [running, queued] = screen.getAllByRole("listitem") as [
      HTMLElement,
      HTMLElement,
    ];
    expect(running).toHaveTextContent("started 11:00");
    expect(running).not.toHaveTextContent("last heartbeat");
    expect(running).not.toHaveTextContent("NaN");
    expect(queued).not.toHaveTextContent("started 11:00");
    expect(queued).not.toHaveTextContent("last heartbeat");
    expect(queued).not.toHaveTextContent("NaN");
  });

  /** Scenario: Row actions are named and confirmed by theme */
  it("names every action and sends destructive actions only after confirmation", () => {
    const onAction = renderPanel(
      board({
        active: [
          item({
            id: "active-1",
            title: "Alpha",
            status: "retry_wait",
            position: null,
            can_reprocess: true,
            refusal_code: null,
            stuck_kind: "retry_wait",
            can_cancel: true,
          }),
        ],
        dead: [
          item({
            id: "dead-1",
            title: "Beta",
            status: "dead_letter",
            can_reprocess: true,
            refusal_code: null,
            stuck_kind: "dead_letter",
            can_retry: true,
            can_discard: true,
          }),
        ],
        backlog: [
          {
            candidate_id: "cand-1",
            title: "Gamma",
            created_at: "2026-10-20T10:00:00Z",
            expires_at: "2026-10-27T10:00:00Z",
          },
        ],
      }),
      { actionError: labels.actionFailed },
    );
    const cancel = queueActionName(labels.cancel, "Alpha");
    const discard = queueActionName(labels.discard, "Beta");
    expect(
      screen.getByRole("button", {
        name: queueActionName(reprocessLabels.action, "Alpha"),
      }),
    ).toBeEnabled();
    expect(
      screen.getByRole("button", {
        name: queueActionName(labels.retry, "Beta"),
      }),
    ).toBeEnabled();
    expect(
      screen.getByRole("button", {
        name: queueActionName(labels.generateNow, "Gamma"),
      }),
    ).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: cancel }));
    expect(screen.getByText("Cancel generation for Alpha?")).toBeVisible();
    expect(onAction).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(labels.actionFailed);
    fireEvent.click(
      screen.getByRole("button", {
        name: queueActionName(labels.confirmBack, "Alpha"),
      }),
    );
    fireEvent.click(screen.getByRole("button", { name: discard }));
    expect(screen.getByText("Discard Beta?")).toBeVisible();
    fireEvent.click(
      screen.getByRole("button", {
        name: queueActionName(labels.confirmBack, "Beta"),
      }),
    );
    expect(onAction).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(labels.actionFailed);

    fireEvent.click(screen.getByRole("button", { name: cancel }));
    fireEvent.click(screen.getByRole("button", { name: cancel }));
    fireEvent.click(screen.getByRole("button", { name: discard }));
    fireEvent.click(screen.getByRole("button", { name: discard }));
    fireEvent.click(
      screen.getByRole("button", {
        name: queueActionName(labels.retry, "Beta"),
      }),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: queueActionName(labels.generateNow, "Gamma"),
      }),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: queueActionName(reprocessLabels.action, "Alpha"),
      }),
    );
    expect(onAction.mock.calls).toEqual([
      [QUEUE_ACTION.CANCEL, "active-1"],
      [QUEUE_ACTION.DISCARD, "dead-1"],
      [QUEUE_ACTION.RETRY, "dead-1"],
      [QUEUE_ACTION.GENERATE_NOW, "cand-1"],
      [QUEUE_ACTION.REPROCESS, "active-1"],
    ]);
    expect(screen.getByRole("alert")).toHaveTextContent(labels.actionFailed);
  });

  /** Scenario: Row actions are named and confirmed by theme */
  it("uses the untitled fallback in action names and keeps safe error codes", () => {
    renderPanel(
      board({
        dead: [
          item({
            kind: "dashboard",
            status: "dead_letter",
            title: "",
            project_id: "proj-9",
            error_code: "safe_failure",
            can_reprocess: true,
            refusal_code: null,
            stuck_kind: "dead_letter",
          }),
        ],
      }),
    );
    expect(
      screen.getByRole("button", {
        name: queueActionName(reprocessLabels.action, labels.untitled),
      }),
    ).toBeEnabled();
    expect(
      screen.getByRole("link", {
        name: queueActionName(labels.openEditor, labels.untitled),
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Queue error (safe_failure).")).toBeVisible();
  });

  /** Scenario: Unstaged rows use safe recovery targets */
  it("renders unstaged details once without generation-run-only actions", () => {
    const onAction = renderPanel(
      board({
        active: [
          item({
            id: "synthetic-queued",
            title: "Unstaged queued",
            staged: false,
            position: 3,
            phase: "research",
            eta: "2026-10-24T14:30:00Z",
            refusal_code: "projectless_unstaged",
            can_cancel: true,
          }),
        ],
        dead: [
          item({
            id: "synthetic-dead",
            title: "Unstaged dead",
            status: "dead_letter",
            staged: false,
            refusal_code: "projectless_unstaged",
            can_retry: true,
            can_discard: true,
          }),
        ],
      }),
    );
    const row = screen.getByText("Unstaged queued").closest("li");
    expect(row).toHaveTextContent("#3");
    expect(row).toHaveTextContent("phase Research");
    expect(row).toHaveTextContent("starts ~11:30");
    expect(screen.getAllByText("Unstaged queued")).toHaveLength(1);
    expect(screen.getAllByText("#3")).toHaveLength(1);
    expect(screen.getAllByText(/starts ~11:30/)).toHaveLength(1);
    const reprocess = screen.getByRole("button", {
      name: queueActionName(reprocessLabels.action, "Unstaged queued"),
    });
    expect(reprocess).toBeDisabled();
    expect(reprocess).toHaveAccessibleDescription(
      reprocessLabels.refusals.projectless_unstaged,
    );
    fireEvent.click(reprocess);
    expect(
      screen.queryByRole("button", {
        name: queueActionName(labels.cancel, "Unstaged queued"),
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: queueActionName(labels.retry, "Unstaged dead"),
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: queueActionName(labels.discard, "Unstaged dead"),
      }),
    ).not.toBeInTheDocument();
    expect(onAction).not.toHaveBeenCalled();
  });

  /** Scenario: Unstaged rows use safe recovery targets */
  it("uses project and version for orphans and run id plus version when staged", () => {
    const onAction = renderPanel(
      board({
        active: [
          item({
            id: "synthetic-orphan",
            title: "Orphan",
            staged: false,
            project_id: "proj-1",
            lock_version: 4,
            can_reprocess: true,
            refusal_code: null,
            stuck_kind: "orphan",
          }),
          item({
            id: "run-real-1",
            title: "Staged",
            status: "retry_wait",
            position: null,
            lock_version: 7,
            can_reprocess: true,
            refusal_code: null,
            stuck_kind: "retry_wait",
          }),
        ],
      }),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: queueActionName(reprocessLabels.action, "Orphan"),
      }),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: queueActionName(reprocessLabels.action, "Staged"),
      }),
    );
    expect(onAction.mock.calls).toEqual([
      [
        QUEUE_ACTION.REPROCESS,
        "synthetic-orphan",
        { projectId: "proj-1", expectedVersion: 4 },
      ],
      [QUEUE_ACTION.REPROCESS, "run-real-1", { expectedVersion: 7 }],
    ]);
  });

  /** Scenario: Backend estimates remain authoritative */
  it("formats backend ETA without deriving one from running or retry timing", () => {
    renderPanel(
      board({
        average_drive_minutes: 99,
        active: [
          item({
            id: "running",
            status: "running",
            started_at: "2026-10-24T14:00:00Z",
            refusal_code: "fresh_running",
          }),
          item({
            id: "queued",
            title: "Backend ETA",
            position: 2,
            eta: "2026-10-24T15:17:00Z",
          }),
          item({
            id: "retry",
            title: "Retry timing",
            status: "retry_wait",
            position: null,
            next_attempt_at: "2026-10-24T14:30:00Z",
            can_reprocess: true,
            refusal_code: null,
            stuck_kind: "retry_wait",
          }),
        ],
      }),
    );
    const queued = screen.getByText("Backend ETA").closest("li");
    const retry = screen.getByText("Retry timing").closest("li");
    expect(queued).toHaveTextContent("starts ~12:17");
    expect(retry).toHaveTextContent("Next try at 11:30");
    expect(retry).not.toHaveTextContent("starts ~");
    expect(screen.getAllByText(/starts ~/)).toHaveLength(1);
  });
});
