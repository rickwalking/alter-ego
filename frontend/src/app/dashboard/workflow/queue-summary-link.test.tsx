/** The board's compact queue summary linking to the queue page. */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { QUEUE_STATUS } from "@/constants/workflow";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import {
  QueueSummaryLink,
  queueSummaryCounts,
} from "@/app/dashboard/workflow/queue-summary-link";
import {
  makeQueueBoard as board,
  makeQueueItem as item,
  queueWrapper as wrapper,
} from "@/app/dashboard/queue/queue-panel.test-utils";

const labels = en.workflow.queue.summary;

function renderSummary(
  value: Parameters<typeof QueueSummaryLink>[0]["board"],
): ReturnType<typeof render> {
  return render(wrapper({ children: <QueueSummaryLink board={value} /> }));
}

describe("queueSummaryCounts", () => {
  it("splits the active list into running and queued", () => {
    const counts = queueSummaryCounts(
      board({
        active: [
          item({ id: "a", status: QUEUE_STATUS.RUNNING }),
          item({ id: "b", status: QUEUE_STATUS.QUEUED }),
          item({ id: "c", status: QUEUE_STATUS.RETRY_WAIT }),
        ],
        dead: [item({ id: "d" })],
      }),
    );
    expect(counts).toEqual({ running: 1, queued: 2, dead: 1 });
  });
});

describe("QueueSummaryLink", () => {
  /** Scenario: The board keeps only a queue summary */
  it("links to the queue page with the live segments", () => {
    renderSummary(
      board({
        active: [
          item({ id: "a", status: QUEUE_STATUS.RUNNING }),
          item({ id: "b", status: QUEUE_STATUS.QUEUED }),
          item({ id: "c", status: QUEUE_STATUS.QUEUED }),
        ],
        dead: [item({ id: "d" })],
      }),
    );
    const link = screen.getByTestId("queue-summary-link");
    expect(link).toHaveAttribute("href", "/dashboard/queue");
    expect(link).toHaveTextContent("1 generating");
    expect(link).toHaveTextContent("2 queued");
    expect(link).toHaveTextContent("1 stuck");
  });

  /** Scenario: The board keeps only a queue summary */
  it("reads Fila vazia when the queue is empty", () => {
    renderSummary(board());
    expect(screen.getByTestId("queue-summary-link")).toHaveTextContent(
      labels.empty,
    );
  });

  /** Scenario: The board keeps only a queue summary */
  it("renders nothing without queue data (non-admin)", () => {
    const { container } = renderSummary(null);
    expect(container).toBeEmptyDOMElement();
  });

  it("has summary strings in both languages", () => {
    for (const key of ["label", "empty", "running", "queued", "dead"]) {
      expect(labels).toHaveProperty(key);
      expect(pt.workflow.queue.summary).toHaveProperty(key);
    }
  });
});
