/** The generation queue panel above the workflow board. */
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";

import { QUEUE_ACTION } from "@/constants/workflow";
import en from "@/i18n/locales/en.json";
import type { QueueBoard, QueueItem } from "@/schemas/generation-queue";
import { QueuePanel } from "./queue-panel";

const labels = en.workflow.queue;

function item(overrides: Partial<QueueItem> = {}): QueueItem {
  return {
    id: "gen-1",
    kind: "autopilot",
    status: "queued",
    title: "Agents that ship code",
    project_id: null,
    phase: null,
    position: 1,
    eta: null,
    started_at: null,
    next_attempt_at: null,
    error_code: null,
    can_retry: false,
    can_discard: false,
    can_cancel: false,
    ...overrides,
  };
}

function board(overrides: Partial<QueueBoard> = {}): QueueBoard {
  return {
    active: [],
    dead: [],
    backlog: [],
    average_drive_minutes: 15,
    ...overrides,
  };
}

function wrapper({ children }: { children: ReactNode }) {
  return (
    <NextIntlClientProvider locale="en" messages={en} timeZone="UTC">
      {children}
    </NextIntlClientProvider>
  );
}

function renderPanel(
  value: QueueBoard | null,
  extra: Partial<Parameters<typeof QueuePanel>[0]> = {},
) {
  const onAction = vi.fn();
  render(
    <QueuePanel
      board={value}
      error={null}
      pending={null}
      actionError={null}
      onAction={onAction}
      {...extra}
    />,
    { wrapper },
  );
  return onAction;
}

describe("QueuePanel", () => {
  /** Scenario: The panel shows the running and queued carousels in order */
  it("lists the active runs by position with phase and start estimate", () => {
    renderPanel(
      board({
        active: [
          item({ id: "run", status: "running", position: 1, phase: "images" }),
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
    expect(within(first).queryByRole("button")).toBeNull();
    expect(
      within(second).getByRole("button", { name: labels.cancel }),
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
            can_retry: true,
            can_discard: true,
          }),
        ],
      }),
    );
    expect(
      screen.getByText(labels.reason.run_budget_exhausted),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: labels.retry }));
    fireEvent.click(screen.getByRole("button", { name: labels.discard }));
    expect(onAction.mock.calls).toEqual([
      [QUEUE_ACTION.RETRY, "dead-1"],
      [QUEUE_ACTION.DISCARD, "dead-1"],
    ]);
  });

  /** Scenario: A parked dashboard run points to the editor */
  it("links a parked dashboard run to the editor", () => {
    renderPanel(
      board({
        dead: [
          item({
            id: "dead-2",
            kind: "dashboard",
            status: "dead_letter",
            project_id: "proj-9",
            error_code: "mystery",
          }),
        ],
      }),
    );
    expect(screen.queryByRole("button")).toBeNull();
    expect(
      screen.getByRole("link", { name: labels.openEditor }),
    ).toHaveAttribute("href", "/dashboard/create/proj-9");
    expect(screen.getByText("Queue error (mystery).")).toBeInTheDocument();
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
    fireEvent.click(screen.getByRole("button", { name: labels.generateNow }));
    expect(onAction).toHaveBeenCalledWith(QUEUE_ACTION.GENERATE_NOW, "cand-1");
  });

  /** Scenario: A failed button shows an error */
  it("shows the action error and disables the row in flight", () => {
    renderPanel(board({ active: [item({ id: "busy", can_cancel: true })] }), {
      pending: "busy",
      actionError: labels.actionFailed,
    });
    expect(screen.getByRole("alert")).toHaveTextContent(labels.actionFailed);
    expect(screen.getByRole("button", { name: labels.cancel })).toBeDisabled();
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
        pending={null}
        actionError={null}
        onAction={vi.fn()}
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
});
