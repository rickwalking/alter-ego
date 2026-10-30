import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@/test/utils";
import {
  QUEUE_API,
  WORKFLOW_API,
  WORKFLOW_BOARD_POLL_INTERVAL_MS,
} from "@/constants/workflow";
import type { WorkflowKanban } from "@/modules/editorial";

vi.mock("next-intl", () => {
  const translate = (key: string): string => key;
  return {
    NextIntlClientProvider: ({ children }: { children: ReactNode }) => children,
    useTranslations: () => translate,
    useLocale: () => "pt",
  };
});

const navigation = vi.hoisted(() => {
  const listeners = new Set<() => void>();
  return {
    params: new URLSearchParams(),
    replace: vi.fn((href: string): void => {
      const query = href.split("?")[1] ?? "";
      navigation.params = new URLSearchParams(query);
      listeners.forEach((listener) => listener());
    }),
    subscribe: (listener: () => void): (() => void) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
});

vi.mock("next/navigation", async () => {
  const { useSyncExternalStore } = await import("react");
  return {
    useSearchParams: (): URLSearchParams =>
      useSyncExternalStore(navigation.subscribe, () => navigation.params),
    useRouter: () => ({ replace: navigation.replace }),
    usePathname: () => "/dashboard/workflow",
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
    navigation.params = new URLSearchParams();
    navigation.replace.mockClear();
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

  /** Scenario: The board fits the screen and columns scroll independently */
  it("keeps the board view height fixed so the page never scrolls vertically", async () => {
    await renderLoadedBoard();
    const view = screen.getByTestId("workflow-board-view");
    expect(view.className).toContain("h-[calc(100dvh-3.5rem)]");
    expect(view.className).toContain("overflow-hidden");
  });
});

describe("WorkflowBoardPage toolbar", () => {
  beforeEach(() => {
    boardResponses = [];
    navigation.params = new URLSearchParams();
    navigation.replace.mockClear();
    mockFetch.mockReset();
    mockFetch.mockImplementation((url) =>
      url === WORKFLOW_API.WORKFLOW_BOARD
        ? jsonResponse(board(FIRST_TITLE))
        : jsonResponse({}),
    );
  });

  /** Scenario: Search narrows the board */
  it("writes the search query into the URL through the toolbar", async () => {
    boardResponses.push(jsonResponse(board(FIRST_TITLE)));
    render(<WorkflowBoardPage />);
    expect(await screen.findByText(FIRST_TITLE)).toBeInTheDocument();

    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "claude" },
    });

    expect(navigation.replace).toHaveBeenLastCalledWith(
      "/dashboard/workflow?q=claude",
      { scroll: false },
    );
  });
});

describe("WorkflowBoardPage queue summary", () => {
  function queueCalls(): number {
    return mockFetch.mock.calls.filter(([url]) => url === QUEUE_API.BOARD)
      .length;
  }

  function route(url: string): Promise<Response> {
    if (url === WORKFLOW_API.WORKFLOW_BOARD) {
      return jsonResponse(board(FIRST_TITLE));
    }
    if (url === WORKFLOW_API.WORKFLOW_BOARD_ARCHIVED) {
      return jsonResponse({ columns: [] });
    }
    if (url === QUEUE_API.BOARD) {
      return jsonResponse({
        active: [],
        dead: [],
        backlog: [],
        average_drive_minutes: 0,
      });
    }
    return jsonResponse({});
  }

  beforeEach(() => {
    navigation.params = new URLSearchParams();
    navigation.replace.mockClear();
    mockFetch.mockReset();
    mockFetch.mockImplementation(route);
  });

  /** Scenario: The board keeps only a queue summary */
  it("shows the summary chip without the full queue panel", async () => {
    render(<WorkflowBoardPage />);
    expect(await screen.findByTestId("queue-summary-link")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "queue.processNow" }),
    ).not.toBeInTheDocument();
  });

  /** Scenario: The board keeps only a queue summary */
  it("does not call the queue API on the archived board", async () => {
    render(<WorkflowBoardPage />);
    await screen.findByTestId("queue-summary-link");
    const callsBefore = queueCalls();

    fireEvent.click(
      screen.getByRole("radio", { name: "archive.showArchived" }),
    );

    expect(
      await screen.findByRole("radio", { name: "archive.showActive" }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("queue-summary-link")).not.toBeInTheDocument();
    expect(queueCalls()).toBe(callsBefore);
  });
});
