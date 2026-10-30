/** The archive control behind a workflow board card overflow menu. */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";

import { WORKFLOW_API } from "@/constants/workflow";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import type { KanbanCard } from "@/schemas/neon-kanban";

vi.mock("@/lib/authenticated-fetch", () => ({ authenticatedFetch: vi.fn() }));

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { CardArchiveAction } from "./card-archive-action";

const mockFetch = vi.mocked(authenticatedFetch);
const labels = en.workflow.archive;
const CARD_TITLE = "Stale carousel";

function card(overrides: Partial<KanbanCard> = {}): KanbanCard {
  return {
    id: "proj-1",
    title: CARD_TITLE,
    description: "AI",
    phase: "content",
    phaseStatus: "awaiting_human",
    statusKey: "awaiting_human",
    archiveRefusal: null,
    canArchive: true,
    ...overrides,
  };
}

function wrapper({ children }: { children: ReactNode }) {
  return (
    <NextIntlClientProvider locale="en" messages={en}>
      {children}
    </NextIntlClientProvider>
  );
}

function renderAction(
  overrides: Partial<KanbanCard> = {},
  archived = false,
): ReturnType<typeof vi.fn> {
  const onChanged = vi.fn();
  render(
    <CardArchiveAction
      card={card(overrides)}
      archived={archived}
      onChanged={onChanged}
    />,
    { wrapper },
  );
  return onChanged;
}

function menuTrigger(): HTMLElement {
  return screen.getByRole("button", {
    name: labels.menuLabel.replace("{title}", CARD_TITLE),
  });
}

function openMenu(): void {
  fireEvent.click(menuTrigger());
}

function respond(ok: boolean): void {
  mockFetch.mockResolvedValue({
    ok,
    json: () => Promise.resolve({}),
  } as Response);
}

describe("CardArchiveAction", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  /** Scenario: The archive action lives behind a per-card overflow menu */
  it("renders a 28px overflow trigger labelled with the card title", () => {
    renderAction();
    const trigger = menuTrigger();
    expect(trigger).toHaveAttribute("aria-haspopup", "menu");
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(trigger.className).toContain("h-7");
    expect(trigger.className).toContain("w-7");
    expect(pt.workflow.archive.menuLabel).toBe("Mais ações: {title}");
  });

  /** Scenario: The archive action lives behind a per-card overflow menu */
  it("archives after the confirmation and refreshes the board", async () => {
    respond(true);
    const onChanged = renderAction();

    openMenu();
    expect(screen.getByRole("menu")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("menuitem", { name: labels.archive }));
    expect(screen.getByText(labels.confirm)).toBeInTheDocument();
    expect(mockFetch).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("menuitem", { name: labels.confirmYes }));

    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(mockFetch).toHaveBeenCalledWith(
      WORKFLOW_API.CAROUSEL_ARCHIVE("proj-1"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(pt.workflow.archive.confirm).toBe("Arquivar este carrossel?");
  });

  /** Scenario: The archive action lives behind a per-card overflow menu */
  it("archives nothing when the confirmation is cancelled", () => {
    renderAction();

    openMenu();
    fireEvent.click(screen.getByRole("menuitem", { name: labels.archive }));
    fireEvent.click(screen.getByRole("menuitem", { name: labels.cancel }));

    expect(screen.queryByText(labels.confirm)).not.toBeInTheDocument();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  /** Scenario: The archive action lives behind a per-card overflow menu */
  it("closes the menu and returns focus to the trigger on Escape", () => {
    renderAction();
    openMenu();
    const menu = screen.getByRole("menu");

    fireEvent.keyDown(menu, { key: "Escape" });

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(menuTrigger()).toHaveFocus();
  });

  /** Scenario: The archive action lives behind a per-card overflow menu */
  it("is not clipped by a scrolling column", () => {
    renderAction();
    openMenu();
    const menu = screen.getByRole("menu");
    expect(menu.className).toContain("fixed");
  });

  /** Scenario: A refused card explains itself once, inside its menu */
  it("shows the refusal reason once as disabled text in the menu", () => {
    renderAction({ archiveRefusal: "in_progress" });

    expect(screen.queryByText(labels.inProgress)).not.toBeInTheDocument();
    openMenu();
    const reason = screen.getByRole("menuitem", { name: labels.inProgress });
    expect(reason).toBeDisabled();
    expect(screen.getAllByText(labels.inProgress)).toHaveLength(1);
  });

  /** Scenario: A card an autopilot run still needs cannot be archived */
  it("shows the autopilot refusal reason in the menu", () => {
    renderAction({ archiveRefusal: "autopilot" });
    openMenu();
    expect(
      screen.getByRole("menuitem", { name: labels.autopilot }),
    ).toBeDisabled();
  });

  /** Scenario: A card without archive rights shows no control */
  it("shows no control to a caller who may not archive the card", () => {
    renderAction({ canArchive: false });
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  /** Scenario: A card without archive rights shows no control */
  it("shows no restore to a caller who may not archive the card", () => {
    renderAction({ canArchive: false }, true);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  /** Scenario: A card without archive rights shows no control */
  it("shows no control on a published card", () => {
    renderAction({ archiveRefusal: "published" });
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  /** Scenario: The archived board restores through the same menu */
  it("restores an archived carousel and refreshes the board", async () => {
    respond(true);
    const onChanged = renderAction({}, true);

    openMenu();
    fireEvent.click(screen.getByRole("menuitem", { name: labels.restore }));

    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(mockFetch).toHaveBeenCalledWith(
      WORKFLOW_API.CAROUSEL_RESTORE("proj-1"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(pt.workflow.archive.restore).toBe("Restaurar");
  });

  /** Scenario: A failed archive or restore says so on its card */
  it("says when the archive failed", async () => {
    respond(false);
    const onChanged = renderAction();

    openMenu();
    fireEvent.click(screen.getByRole("menuitem", { name: labels.archive }));
    fireEvent.click(screen.getByRole("menuitem", { name: labels.confirmYes }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      labels.archiveFailed,
    );
    expect(onChanged).not.toHaveBeenCalled();
  });

  /** Scenario: A failed archive or restore says so on its card */
  it("says when the restore failed", async () => {
    respond(false);
    const onChanged = renderAction({}, true);

    openMenu();
    fireEvent.click(screen.getByRole("menuitem", { name: labels.restore }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      labels.restoreFailed,
    );
    expect(onChanged).not.toHaveBeenCalled();
  });
});
