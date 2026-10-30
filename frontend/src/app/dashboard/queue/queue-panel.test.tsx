/** The generation queue panel above the workflow board. */
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { QUEUE_ACTION, REPROCESS_REFUSAL } from "@/constants/workflow";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import { QueuePanel } from "./queue-panel";
import {
  makeQueueBoard as board,
  makeQueueItem as item,
  queueActionName,
  queueWrapper as wrapper,
  renderQueuePanel as renderPanel,
} from "./queue-panel.test-utils";

const labels = en.workflow.queue;
const reprocessLabels = en.workflow.reprocess;

describe("QueuePanel", () => {
  /** Scenario: The panel shows the running and queued carousels in order */
  it("lists the active runs by position with phase and start estimate", () => {
    renderPanel(
      board({
        active: [
          item({
            id: "run",
            status: "running",
            position: 1,
            phase: "images",
            refusal_code: "fresh_running",
          }),
          item({
            id: "next",
            title: "Second theme",
            position: 2,
            eta: "2026-10-24T14:30:00Z",
            can_cancel: true,
          }),
        ],
      }),
    );
    const rows = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    const [first, second] = rows as [HTMLElement, HTMLElement];
    expect(first).toHaveTextContent("#1");
    expect(first).toHaveTextContent("Generating · phase Images");
    expect(second).toHaveTextContent("#2");
    expect(second).toHaveTextContent("starts ~11:30");
    const runningReprocess = within(first).getByRole("button", {
      name: queueActionName(reprocessLabels.action, "Agents that ship code"),
    });
    expect(runningReprocess).toBeDisabled();
    expect(runningReprocess).toHaveAccessibleDescription(
      en.workflow.reprocess.refusals.fresh_running,
    );
    const queuedReprocess = within(second).getByRole("button", {
      name: queueActionName(reprocessLabels.action, "Second theme"),
    });
    expect(queuedReprocess).toBeDisabled();
    expect(queuedReprocess).toHaveAccessibleDescription(
      en.workflow.reprocess.refusals.normal_queued,
    );
    expect(
      within(second).getByRole("button", {
        name: queueActionName(labels.cancel, "Second theme"),
      }),
    ).toBeEnabled();
    expect(screen.getByText(/About 15 min per carousel/)).toBeInTheDocument();
  });

  /** Scenario: A parked autopilot run offers "Tentar de novo" and "Descartar" */
  it("offers retry and discard on a parked autopilot run", () => {
    const onAction = renderPanel(
      board({
        dead: [
          item({
            id: "dead-1",
            status: "dead_letter",
            error_code: "run_budget_exhausted",
            can_reprocess: true,
            refusal_code: null,
            stuck_kind: "dead_letter",
            can_retry: true,
            can_discard: true,
          }),
        ],
      }),
    );
    expect(
      screen.getByText(labels.reason.run_budget_exhausted),
    ).toBeInTheDocument();
    const retry = queueActionName(labels.retry, "Agents that ship code");
    const discard = queueActionName(labels.discard, "Agents that ship code");
    fireEvent.click(screen.getByRole("button", { name: retry }));
    fireEvent.click(screen.getByRole("button", { name: discard }));
    expect(onAction.mock.calls).toEqual([[QUEUE_ACTION.RETRY, "dead-1"]]);
    fireEvent.click(screen.getByRole("button", { name: discard }));
    expect(onAction.mock.calls).toEqual([
      [QUEUE_ACTION.RETRY, "dead-1"],
      [QUEUE_ACTION.DISCARD, "dead-1"],
    ]);
  });

  /** Scenario: Confirmation keeps keyboard focus and supports Escape */
  it("focuses the destructive confirmation when opened from the keyboard", async () => {
    const user = userEvent.setup();
    renderPanel(board({ active: [item({ can_cancel: true })] }));
    const name = queueActionName(labels.cancel, "Agents that ship code");
    const trigger = screen.getByRole("button", { name });
    trigger.focus();
    await user.keyboard("{Enter}");
    const confirmation = screen.getByRole("group");
    expect(within(confirmation).getByRole("button", { name })).toHaveFocus();
  });

  /** Scenario: Confirmation keeps keyboard focus and supports Escape */
  it("restores focus to a new trigger when Back closes confirmation", async () => {
    const user = userEvent.setup();
    const onAction = renderPanel(
      board({ active: [item({ can_cancel: true })] }),
    );
    const name = queueActionName(labels.cancel, "Agents that ship code");
    const trigger = screen.getByRole("button", { name });
    trigger.focus();
    await user.keyboard("{Enter}");
    await user.click(
      screen.getByRole("button", {
        name: queueActionName(labels.confirmBack, "Agents that ship code"),
      }),
    );
    const restored = screen.getByRole("button", { name });
    expect(restored).not.toBe(trigger);
    expect(restored).toHaveFocus();
    expect(onAction).not.toHaveBeenCalled();
  });

  /** Scenario: Confirmation keeps keyboard focus and supports Escape */
  it("closes on Escape from the group and restores trigger focus", async () => {
    const user = userEvent.setup();
    const onAction = renderPanel(
      board({ active: [item({ can_cancel: true })] }),
    );
    const name = queueActionName(labels.cancel, "Agents that ship code");
    screen.getByRole("button", { name }).focus();
    await user.keyboard("{Enter}");
    const confirmation = screen.getByRole("group");
    screen
      .getByRole("button", {
        name: queueActionName(labels.confirmBack, "Agents that ship code"),
      })
      .focus();
    await user.keyboard("{Escape}");
    expect(confirmation).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name })).toHaveFocus();
    expect(onAction).not.toHaveBeenCalled();
  });

  /** Scenario: Confirmation keeps keyboard focus and supports Escape */
  it("supports Discard confirmation focus and Escape", async () => {
    const user = userEvent.setup();
    const onAction = renderPanel(
      board({ dead: [item({ can_discard: true })] }),
    );
    const name = queueActionName(labels.discard, "Agents that ship code");
    screen.getByRole("button", { name }).focus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("button", { name })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.getByRole("button", { name })).toHaveFocus();
    expect(onAction).not.toHaveBeenCalled();
  });

  /** Scenario: A parked dashboard run points to the editor */
  it("links a parked dashboard run to the editor", () => {
    const onAction = renderPanel(
      board({
        dead: [
          item({
            id: "dead-2",
            kind: "dashboard",
            status: "dead_letter",
            project_id: "proj-9",
            error_code: "mystery",
            can_reprocess: true,
            refusal_code: null,
            stuck_kind: "dead_letter",
          }),
        ],
      }),
    );
    const reprocess = screen.getByRole("button", {
      name: queueActionName(reprocessLabels.action, "Agents that ship code"),
    });
    expect(reprocess).toBeEnabled();
    fireEvent.click(reprocess);
    expect(onAction).toHaveBeenCalledWith(QUEUE_ACTION.REPROCESS, "dead-2");
    expect(
      screen.getByRole("link", {
        name: queueActionName(labels.openEditor, "Agents that ship code"),
      }),
    ).toHaveAttribute("href", "/dashboard/create/proj-9");
    expect(screen.getByText("Queue error (mystery).")).toBeInTheDocument();
  });

  /** Scenario: Reprocess shows progress after acceptance */
  it("enables reprocess for an existing retry-wait generation row", () => {
    const onAction = renderPanel(
      board({
        active: [
          item({
            id: "retry-1",
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
    const reprocess = screen.getByRole("button", {
      name: queueActionName(reprocessLabels.action, "Agents that ship code"),
    });
    expect(reprocess).toBeEnabled();
    fireEvent.click(reprocess);
    expect(onAction).toHaveBeenCalledWith(QUEUE_ACTION.REPROCESS, "retry-1");
  });

  /** Scenario: Not stuck reasons are accessible */
  it("disables reprocess for an unsupported existing row", () => {
    const onAction = renderPanel(
      board({
        dead: [
          item({
            id: "cancelled-1",
            status: "cancelled",
            refusal_code: "unsupported",
          }),
        ],
      }),
    );
    const reprocess = screen.getByRole("button", {
      name: queueActionName(reprocessLabels.action, "Agents that ship code"),
    });
    expect(reprocess).toBeDisabled();
    expect(reprocess).toHaveAccessibleDescription(
      en.workflow.reprocess.refusals.unsupported,
    );
    fireEvent.click(reprocess);
    expect(onAction).not.toHaveBeenCalled();
  });

  /** Scenario: A waiting theme offers "Gerar agora" */
  it("offers generate now on a backlog theme and disables it while pending", () => {
    const onAction = renderPanel(
      board({
        backlog: [
          {
            candidate_id: "cand-1",
            title: "Waiting theme",
            created_at: "2026-10-20T10:00:00Z",
            expires_at: "2026-10-27T10:00:00Z",
          },
        ],
      }),
    );
    expect(screen.getByText("expires on 10/27")).toBeInTheDocument();
    const generate = queueActionName(labels.generateNow, "Waiting theme");
    fireEvent.click(screen.getByRole("button", { name: generate }));
    expect(onAction).toHaveBeenCalledWith(QUEUE_ACTION.GENERATE_NOW, "cand-1");
    expect(onAction).toHaveBeenCalledTimes(1);
    expect(
      screen.queryByRole("button", {
        name: queueActionName(reprocessLabels.action, "Waiting theme"),
      }),
    ).not.toBeInTheDocument();
  });

  /** Scenario: Process queue now is a panel action */
  it("calls the panel process action from the header", () => {
    const onProcess = vi.fn();
    renderPanel(board(), { onProcess });
    fireEvent.click(screen.getByRole("button", { name: labels.processNow }));
    expect(onProcess).toHaveBeenCalledTimes(1);
  });

  /** Scenario: Process queue now is a panel action */
  it("keeps process pending and error state independent from row actions", () => {
    renderPanel(board({ active: [item({ id: "busy", can_cancel: true })] }), {
      processPending: true,
      processError: labels.processFailed,
      actionError: labels.actionFailed,
    });
    expect(
      screen.getByRole("button", { name: labels.processNow }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", {
        name: queueActionName(labels.cancel, "Agents that ship code"),
      }),
    ).toBeEnabled();
    expect(screen.getByText(labels.processFailed)).toBeInTheDocument();
    expect(screen.getByText(labels.actionFailed)).toBeInTheDocument();
  });

  /** Scenario: A failed button shows an error */
  it("shows the action error and disables the row in flight", () => {
    renderPanel(board({ active: [item({ id: "busy", can_cancel: true })] }), {
      pending: new Set(["busy"]),
      actionError: labels.actionFailed,
    });
    expect(screen.getByRole("alert")).toHaveTextContent(labels.actionFailed);
    expect(
      screen.getByRole("button", {
        name: queueActionName(labels.cancel, "Agents that ship code"),
      }),
    ).toBeDisabled();
  });

  /** Scenario: An empty queue says so */
  it("says the queue is empty", () => {
    renderPanel(board());
    expect(screen.getByText(labels.empty)).toBeInTheDocument();
  });

  /** Scenario: The panel is hidden from editors */
  it("renders nothing without a board or an error", () => {
    const { container } = render(
      <QueuePanel
        board={null}
        error={null}
        pending={new Set<string>()}
        actionError={null}
        processPending={false}
        processError={null}
        onAction={vi.fn()}
        onProcess={vi.fn()}
      />,
      { wrapper },
    );
    expect(container).toBeEmptyDOMElement();
  });

  /** Scenario: A failed refresh keeps the last panel */
  it("shows the load error before the first board", () => {
    renderPanel(null, { error: labels.loadFailed });
    expect(screen.getByRole("alert")).toHaveTextContent(labels.loadFailed);
  });

  it.each(Object.values(REPROCESS_REFUSAL))(
    "has PT and EN copy for the %s refusal",
    (code) => {
      expect(en.workflow.reprocess.refusals[code]).toEqual(expect.any(String));
      expect(pt.workflow.reprocess.refusals[code]).toEqual(expect.any(String));
    },
  );

  it("has PT and EN copy for new row labels and confirmations", () => {
    for (const locale of [en, pt]) {
      expect(locale.workflow.queue.actionForTheme).toContain("{theme}");
      expect(locale.workflow.queue.startedAt).toContain("{time}");
      expect(locale.workflow.queue.heartbeatAge).toContain("{age}");
      expect(locale.workflow.queue.confirmCancel).toContain("{theme}");
      expect(locale.workflow.queue.confirmDiscard).toContain("{theme}");
      expect(locale.workflow.queue.confirmBack).toEqual(expect.any(String));
    }
  });
});
