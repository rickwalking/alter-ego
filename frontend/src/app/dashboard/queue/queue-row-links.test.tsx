/** Queue rows link to their carousel's detail page. */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import en from "@/i18n/locales/en.json";
import { QueueActiveRow, QueueDeadRow } from "./queue-panel-rows";
import { QueueBacklogRow } from "./queue-backlog-row";
import {
  makeQueueItem as item,
  queueWrapper as wrapper,
} from "./queue-panel.test-utils";

const labels = en.workflow.queue;
const openCarouselName = `${labels.openCarousel}: Agents that ship code`;
const noop = vi.fn();

describe("queue row carousel links", () => {
  /** Scenario: Queue rows link to their carousels */
  it("links an active row theme to its carousel", () => {
    render(
      wrapper({
        children: (
          <QueueActiveRow
            item={item({ project_id: "proj-42", status: "running" })}
            pending={new Set<string>()}
            onAction={noop}
          />
        ),
      }),
    );
    const link = screen.getByRole("link", { name: openCarouselName });
    expect(link).toHaveAttribute("href", "/dashboard/create/proj-42");
  });

  /** Scenario: Queue rows link to their carousels */
  it("keeps an active row without a carousel as plain text", () => {
    render(
      wrapper({
        children: (
          <QueueActiveRow
            item={item({ project_id: null })}
            pending={new Set<string>()}
            onAction={noop}
          />
        ),
      }),
    );
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText("Agents that ship code")).toBeInTheDocument();
  });

  /** Scenario: Queue rows link to their carousels */
  it("links a parked row theme to its carousel", () => {
    render(
      wrapper({
        children: (
          <QueueDeadRow
            item={item({ project_id: "proj-7" })}
            pending={new Set<string>()}
            onAction={noop}
          />
        ),
      }),
    );
    expect(
      screen.getByRole("link", { name: openCarouselName }),
    ).toHaveAttribute("href", "/dashboard/create/proj-7");
  });

  /** Scenario: Queue rows link to their carousels */
  it("keeps a backlog theme as plain text", () => {
    render(
      wrapper({
        children: (
          <QueueBacklogRow
            item={{
              candidate_id: "cand-1",
              title: "Backlog theme",
              created_at: "2026-10-20T10:00:00Z",
              expires_at: "2026-10-28T10:00:00Z",
            }}
            pending={new Set<string>()}
            onAction={noop}
          />
        ),
      }),
    );
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText("Backlog theme")).toBeInTheDocument();
  });
});
