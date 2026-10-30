/** The generation queue on its own admin page. */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

import { QUEUE_API } from "@/constants/workflow";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import GenerationQueuePage from "./page";
import { queueWrapper as wrapper } from "./queue-panel.test-utils";

vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";

const mockFetch = vi.mocked(authenticatedFetch);
const labels = en.workflow.queue;

function queueResponse(): Promise<Response> {
  return Promise.resolve({
    ok: true,
    json: () =>
      Promise.resolve({
        active: [
          {
            id: "run-1",
            kind: "autopilot",
            status: "running",
            title: "Running theme",
            project_id: "proj-1",
            phase: "images",
            position: 1,
            eta: null,
            started_at: "2026-10-28T14:02:00Z",
            next_attempt_at: null,
            run_heartbeat_at: null,
            lock_version: 3,
            error_code: null,
            staged: true,
            autopilot_run_id: null,
            priority: 0,
            can_reprocess: false,
            refusal_code: "fresh_running",
            stuck_kind: null,
            can_retry: false,
            can_discard: false,
            can_cancel: false,
          },
        ],
        dead: [],
        backlog: [
          {
            candidate_id: "cand-1",
            title: "Backlog theme",
            created_at: "2026-10-20T10:00:00Z",
            expires_at: "2026-10-28T10:00:00Z",
          },
        ],
        average_drive_minutes: 13,
      }),
  } as unknown as Response);
}

function renderPage(): void {
  render(wrapper({ children: <GenerationQueuePage /> }));
}

describe("GenerationQueuePage", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockFetch.mockImplementation((url) =>
      url === QUEUE_API.BOARD
        ? queueResponse()
        : Promise.resolve({
            ok: true,
            json: () => Promise.resolve({}),
          } as unknown as Response),
    );
  });

  /** Scenario: The queue has its own page */
  it("shows the queue sections with their actions and a link back to the board", async () => {
    renderPage();
    expect(await screen.findByText("Running theme")).toBeInTheDocument();
    expect(screen.getByText(labels.active)).toBeInTheDocument();
    expect(screen.getByText(labels.backlog)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: labels.processNow }),
    ).toBeInTheDocument();
    expect(screen.getByText("Backlog theme")).toBeInTheDocument();
    const boardLink = screen.getByRole("link", {
      name: labels.boardLink,
    });
    expect(boardLink).toHaveAttribute("href", "/dashboard/workflow");
  });

  /** Scenario: Queue rows link to their carousels */
  it("links the run theme to its carousel detail page", async () => {
    renderPage();
    await screen.findByText("Running theme");
    const carousel = screen.getByRole("link", {
      name: `${labels.openCarousel}: Running theme`,
    });
    expect(carousel).toHaveAttribute("href", "/dashboard/create/proj-1");
  });
  it("has the queue page title in both languages", () => {
    expect(en.pageTitles).toHaveProperty("queue");
    expect(pt.pageTitles).toHaveProperty("queue");
  });

  /** Scenario: The Fila nav item is admin-only */
  it("tells non-admins the queue is admins-only when the API latches 403", async () => {
    mockFetch.mockImplementation((url) =>
      url === QUEUE_API.BOARD
        ? Promise.resolve({
            ok: false,
            status: 403,
            json: () => Promise.resolve({ detail: "forbidden" }),
          } as unknown as Response)
        : Promise.resolve({
            ok: true,
            json: () => Promise.resolve({}),
          } as unknown as Response),
    );
    renderPage();
    expect(await screen.findByText(labels.adminsOnly)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: labels.processNow }),
    ).not.toBeInTheDocument();
  });
});
