/** The workflow board switches between the active and the archived carousels. */
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@/test/utils";
import { WORKFLOW_API } from "@/constants/workflow";
import type { WorkflowKanban } from "@/modules/editorial";

vi.mock("next-intl", () => {
  const translate = (key: string): string => key;
  return {
    NextIntlClientProvider: ({ children }: { children: ReactNode }) => children,
    useTranslations: () => translate,
  };
});

vi.mock("@/lib/authenticated-fetch", () => ({ authenticatedFetch: vi.fn() }));

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import WorkflowBoardPage from "./page";

const mockFetch = vi.mocked(authenticatedFetch);
const ACTIVE_TITLE = "Active carousel";
const ARCHIVED_TITLE = "Archived carousel";

function board(
  titles: string[],
  archiveRefusal: string | null = null,
): WorkflowKanban {
  return {
    columns: [
      {
        phase: "content",
        cards: titles.map((title, index) => ({
          id: `proj-${index}`,
          title,
          topic: "AI",
          current_phase: "content",
          phase_status: "awaiting_human",
          updated_at: null,
          can_archive: true,
          archive_refusal: archiveRefusal,
        })),
      },
    ],
  };
}

function boards(archived: WorkflowKanban): void {
  mockFetch.mockImplementation((url) =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve(
          url === WORKFLOW_API.WORKFLOW_BOARD_ARCHIVED
            ? archived
            : board([ACTIVE_TITLE]),
        ),
    } as unknown as Response),
  );
}

describe("WorkflowBoardPage archived view", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  /** Scenario: The archived board lists archived carousels with restore */
  it("lists the archived carousels with restore and goes back to the active ones", async () => {
    boards(board([ARCHIVED_TITLE]));
    render(<WorkflowBoardPage />);
    expect(await screen.findByText(ACTIVE_TITLE)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "archive" })).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "archive.showArchived" }),
    );

    expect(await screen.findByText(ARCHIVED_TITLE)).toBeInTheDocument();
    expect(screen.queryByText(ACTIVE_TITLE)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "restore" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "archive.showActive", pressed: true }),
    ).toBeInTheDocument();
    expect(mockFetch).toHaveBeenCalledWith(
      WORKFLOW_API.WORKFLOW_BOARD_ARCHIVED,
    );

    fireEvent.click(screen.getByRole("button", { name: "archive.showActive" }));

    expect(await screen.findByText(ACTIVE_TITLE)).toBeInTheDocument();
  });

  /** Scenario: The archived board says when it is empty */
  it("says when there are no archived carousels", async () => {
    boards(board([]));
    render(<WorkflowBoardPage />);
    await screen.findByText(ACTIVE_TITLE);

    fireEvent.click(
      screen.getByRole("button", { name: "archive.showArchived" }),
    );

    expect(
      await screen.findByText("archive.emptyArchived"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 3 })).not.toBeInTheDocument();
  });

  /** Scenario: A card in progress cannot be archived */
  it("disables archive on an in-progress card", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(board([ACTIVE_TITLE], "in_progress")),
    } as unknown as Response);
    render(<WorkflowBoardPage />);
    await screen.findByText(ACTIVE_TITLE);

    const archive = screen.getByRole("button", { name: "archive" });
    expect(archive).toBeDisabled();
    expect(archive).toHaveAccessibleDescription("inProgress");
  });
});
