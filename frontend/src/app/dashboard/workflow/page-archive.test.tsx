/** The workflow board switches between the active and the archived carousels. */
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@/test/utils";
import { WORKFLOW_API } from "@/constants/workflow";
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
      navigation.params = new URLSearchParams(href.split("?")[1] ?? "");
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

function renderPage(): void {
  render(<WorkflowBoardPage />);
}

function viewSwitch(): HTMLElement {
  return screen.getByRole("radiogroup", { name: "board.viewGroup" });
}

describe("WorkflowBoardPage archived view", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    navigation.params = new URLSearchParams();
    navigation.replace.mockClear();
  });

  /** Scenario: A segmented control switches between active and archived */
  it("exposes Ativos and Arquivados as a radiogroup with a single tab stop", async () => {
    boards(board([ARCHIVED_TITLE]));
    renderPage();
    await screen.findByText(ACTIVE_TITLE);

    expect(viewSwitch()).toBeInTheDocument();
    const active = screen.getByRole("radio", { name: "archive.showActive" });
    const archivedRadio = screen.getByRole("radio", {
      name: "archive.showArchived",
    });
    expect(active).toHaveAttribute("aria-checked", "true");
    expect(active).toHaveAttribute("tabindex", "0");
    expect(archivedRadio).toHaveAttribute("aria-checked", "false");
    expect(archivedRadio).toHaveAttribute("tabindex", "-1");
    expect(
      screen.getByRole("heading", { level: 1, name: "board.title" }),
    ).toBeInTheDocument();
  });

  /** Scenario: The archived board lists archived carousels with restore */
  it("lists the archived carousels with restore and goes back to the active ones", async () => {
    boards(board([ARCHIVED_TITLE]));
    renderPage();
    expect(await screen.findByText(ACTIVE_TITLE)).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("radio", { name: "archive.showArchived" }),
    );

    expect(await screen.findByText(ARCHIVED_TITLE)).toBeInTheDocument();
    expect(screen.queryByText(ACTIVE_TITLE)).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "menuLabel" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 1, name: "archive.showArchived" }),
    ).toBeInTheDocument();
    expect(navigation.replace).toHaveBeenCalledWith(
      expect.stringContaining("archived=1"),
      expect.objectContaining({ scroll: false }),
    );
    expect(mockFetch).toHaveBeenCalledWith(
      WORKFLOW_API.WORKFLOW_BOARD_ARCHIVED,
    );

    fireEvent.click(screen.getByRole("radio", { name: "archive.showActive" }));

    expect(await screen.findByText(ACTIVE_TITLE)).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 1, name: "board.title" }),
    ).toBeInTheDocument();
    expect(navigation.replace).toHaveBeenLastCalledWith(
      "/dashboard/workflow",
      expect.objectContaining({ scroll: false }),
    );
  });

  /** Scenario: The new-carousel action is one link styled as a button */
  it("renders Novo carrossel as a link without a nested button", async () => {
    boards(board([ARCHIVED_TITLE]));
    renderPage();
    await screen.findByText(ACTIVE_TITLE);

    const link = screen.getByRole("link", { name: "board.newCard" });
    expect(link).toHaveAttribute("href", "/dashboard/create");
    expect(link.className).toContain("rounded-md");
    expect(within(link).queryByRole("button")).not.toBeInTheDocument();
  });

  /** Scenario: A segmented control switches between active and archived */
  it("moves through the segments with arrow keys", async () => {
    boards(board([ARCHIVED_TITLE]));
    renderPage();
    await screen.findByText(ACTIVE_TITLE);

    fireEvent.keyDown(viewSwitch(), { key: "ArrowRight" });

    expect(await screen.findByText(ARCHIVED_TITLE)).toBeInTheDocument();
    expect(
      screen.getByRole("radio", { name: "archive.showArchived" }),
    ).toHaveAttribute("aria-checked", "true");

    fireEvent.keyDown(viewSwitch(), { key: "ArrowLeft" });

    expect(await screen.findByText(ACTIVE_TITLE)).toBeInTheDocument();
  });

  /** Scenario: A segmented control switches between active and archived */
  it("keeps the other query params when switching the segment", async () => {
    navigation.params = new URLSearchParams("q=carousel&sort=title");
    boards(board([ARCHIVED_TITLE]));
    renderPage();
    await screen.findByText(ACTIVE_TITLE);

    fireEvent.click(
      screen.getByRole("radio", { name: "archive.showArchived" }),
    );

    expect(navigation.replace).toHaveBeenCalledWith(
      expect.stringContaining("q=carousel"),
      expect.anything(),
    );
    expect(navigation.replace).toHaveBeenCalledWith(
      expect.stringContaining("sort=title"),
      expect.anything(),
    );
    expect(await screen.findByText(ARCHIVED_TITLE)).toBeInTheDocument();
  });

  /** Scenario: The archived board says when it is empty */
  it("says when there are no archived carousels", async () => {
    boards(board([]));
    renderPage();
    await screen.findByText(ACTIVE_TITLE);

    fireEvent.click(
      screen.getByRole("radio", { name: "archive.showArchived" }),
    );

    expect(
      await screen.findByText("archive.emptyArchived"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 3 })).not.toBeInTheDocument();
  });

  /** Scenario: A refused card explains itself once, inside its menu */
  it("shows the refusal reason inside the card menu", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(board([ACTIVE_TITLE], "in_progress")),
    } as unknown as Response);
    renderPage();
    await screen.findByText(ACTIVE_TITLE);

    expect(screen.queryByText("inProgress")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "menuLabel" }));

    expect(screen.getByRole("menuitem", { name: "inProgress" })).toBeDisabled();
    expect(screen.getAllByText("inProgress")).toHaveLength(1);
  });
});
