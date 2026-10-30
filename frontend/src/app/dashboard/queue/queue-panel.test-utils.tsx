/** Shared queue-panel fixtures and rendering for focused RTL suites. */
import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement, ReactNode } from "react";
import { vi, type Mock } from "vitest";
import en from "@/i18n/locales/en.json";
import type { QueueBoard, QueueItem } from "@/schemas/generation-queue";
import { QueuePanel } from "./queue-panel";
import type { QueueActionHandler, QueuePanelProps } from "./types";

export function makeQueueItem(overrides: Partial<QueueItem> = {}): QueueItem {
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
    run_heartbeat_at: null,
    lock_version: null,
    error_code: null,
    staged: true,
    autopilot_run_id: "autopilot-1",
    priority: 0,
    can_reprocess: false,
    refusal_code: "normal_queued",
    stuck_kind: null,
    can_retry: false,
    can_discard: false,
    can_cancel: false,
    ...overrides,
  };
}

export function makeQueueBoard(
  overrides: Partial<QueueBoard> = {},
): QueueBoard {
  return {
    active: [],
    dead: [],
    backlog: [],
    average_drive_minutes: 15,
    ...overrides,
  };
}

export function queueActionName(action: string, theme: string): string {
  return `${action}: ${theme}`;
}

export function queueWrapper({
  children,
}: Readonly<{ children: ReactNode }>): ReactElement {
  return (
    <NextIntlClientProvider locale="en" messages={en} timeZone="UTC">
      {children}
    </NextIntlClientProvider>
  );
}

export function renderQueuePanel(
  value: QueueBoard | null,
  extra: Partial<QueuePanelProps> = {},
): Mock<QueueActionHandler> {
  const onAction = vi.fn<QueueActionHandler>();
  render(
    <QueuePanel
      board={value}
      error={null}
      pending={new Set<string>()}
      actionError={null}
      processPending={false}
      processError={null}
      onAction={onAction}
      onProcess={vi.fn()}
      {...extra}
    />,
    { wrapper: queueWrapper },
  );
  return onAction;
}
