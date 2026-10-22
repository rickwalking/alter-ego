import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@/test/utils";
import {
  WORKFLOW_API,
  WORKFLOW_BOARD_POLL_INTERVAL_MS,
} from "@/constants/workflow";
import type { WorkflowKanban } from "@/modules/editorial";

vi.mock("next-intl", () => {
  const translate = (key: string): string => key;
  return {
    NextIntlClientProvider: ({ children }: { children: ReactNode }) => children,
    useTranslations: () => translate,
  };
});

vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import WorkflowBoardPage from "./page";

const mockFetch = vi.mocked(authenticatedFetch);
const FIRST_TITLE = "Carousel about agents";
const UPDATED_TITLE = "Carousel about agents, revised";

let boardResponses: Promise<Response>[] = [];

function board(title: string): WorkflowKanban {
  return {
    columns: [
      {
        phase: "research",
        cards: [
          {
            id: "proj-1",
            title,
            topic: "AI",
            current_phase: "research",
            phase_status: "in_progress",
            updated_at: null,
          },
        ],
      },
    ],
  };
}

function jsonResponse(body: unknown, ok = true): Promise<Response> {
  return Promise.resolve({
    ok,
    json: () => Promise.resolve(body),
  } as unknown as Response);
}

function deferred(): {
  promise: Promise<Response>;
  resolve: (value: WorkflowKanban) => void;
} {
  let resolve!: (value: WorkflowKanban) => void;
  const promise = new Promise<WorkflowKanban>((res) => {
    resolve = res;
  }).then((body) => jsonResponse(body));
  return { promise, resolve };
}

function boardCalls(): number {
  return mockFetch.mock.calls.filter(
    ([url]) => url === WORKFLOW_API.WORKFLOW_BOARD,
  ).length;
}

async function renderLoadedBoard(): Promise<HTMLElement> {
  boardResponses.push(jsonResponse(board(FIRST_TITLE)));
  render(<WorkflowBoardPage />);
  return screen.findByText(FIRST_TITLE);
}

describe("WorkflowBoardPage refresh", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
    boardResponses = [];
    mockFetch.mockReset();
    mockFetch.mockImplementation((url) =>
      url === WORKFLOW_API.WORKFLOW_BOARD
        ? (boardResponses.shift() ?? new Promise<Response>(() => undefined))
        : jsonResponse({}),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // Scenario: A poll refresh keeps the mounted board
  it("keeps the same board nodes across a poll and shows the new data", async () => {
    const cardTitle = await renderLoadedBoard();
    const columnHeading = screen.getByRole("heading", { level: 3 });
    const pending = deferred();
    boardResponses.push(pending.promise);

    act(() => {
      vi.advanceTimersByTime(WORKFLOW_BOARD_POLL_INTERVAL_MS);
    });

    expect(boardCalls()).toBe(2);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(cardTitle.isConnected).toBe(true);

    await act(async () => {
      pending.resolve(board(UPDATED_TITLE));
      await pending.promise;
    });

    expect(await screen.findByText(UPDATED_TITLE)).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3 })).toBe(columnHeading);
  });

  // Scenario: A focus refresh keeps the mounted board
  it("keeps the same board nodes across a focus refetch", async () => {
    const cardTitle = await renderLoadedBoard();
    const columnHeading = screen.getByRole("heading", { level: 3 });
    const pending = deferred();
    boardResponses.push(pending.promise);

    act(() => {
      window.dispatchEvent(new Event("focus"));
    });

    expect(boardCalls()).toBe(2);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(cardTitle.isConnected).toBe(true);

    await act(async () => {
      pending.resolve(board(FIRST_TITLE));
      await pending.promise;
    });

    expect(screen.getByRole("heading", { level: 3 })).toBe(columnHeading);
    expect(screen.getByText(FIRST_TITLE)).toBe(cardTitle);
  });

  // Scenario: A failed refresh keeps the last board on screen
  it("shows the error with retry and keeps the last board mounted", async () => {
    const cardTitle = await renderLoadedBoard();
    boardResponses.push(jsonResponse({}, false));

    act(() => {
      vi.advanceTimersByTime(WORKFLOW_BOARD_POLL_INTERVAL_MS);
    });

    expect(await screen.findByText("loadBoardFailed")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "kanban.retry" }),
    ).toBeInTheDocument();
    expect(screen.getByText(FIRST_TITLE)).toBe(cardTitle);
  });

  // Scenario: The first load shows the spinner until the board arrives
  it("shows the spinner and no board while the first request runs", () => {
    render(<WorkflowBoardPage />);

    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 3 })).not.toBeInTheDocument();
  });
});
