/** The archive control under a workflow board card. */
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

function card(overrides: Partial<KanbanCard> = {}): KanbanCard {
  return {
    id: "proj-1",
    title: "Stale carousel",
    description: "AI",
    phase: "content",
    phaseStatus: "awaiting_human",
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

  /** Scenario: Archiving a card asks for a confirmation first */
  it("archives after the confirmation and refreshes the board", async () => {
    respond(true);
    const onChanged = renderAction();

    fireEvent.click(screen.getByRole("button", { name: labels.archive }));
    expect(screen.getByText(labels.confirm)).toBeInTheDocument();
    expect(mockFetch).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: labels.confirmYes }));

    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(mockFetch).toHaveBeenCalledWith(
      WORKFLOW_API.CAROUSEL_ARCHIVE("proj-1"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(pt.workflow.archive.confirm).toBe("Arquivar este carrossel?");
  });

  /** Scenario: Archiving a card asks for a confirmation first */
  it("archives nothing when the confirmation is cancelled", () => {
    renderAction();

    fireEvent.click(screen.getByRole("button", { name: labels.archive }));
    fireEvent.click(screen.getByRole("button", { name: labels.cancel }));

    expect(screen.queryByText(labels.confirm)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: labels.archive })).toBeEnabled();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  /** Scenario: A card in progress cannot be archived */
  it("disables archive with the reason while the phase is in progress", () => {
    renderAction({ archiveRefusal: "in_progress" });

    const button = screen.getByRole("button", { name: labels.archive });
    expect(button).toBeDisabled();
    expect(button).toHaveAccessibleDescription(labels.inProgress);
  });

  /** Scenario: A reviewer sees no archive control */
  it("shows no control to a caller who may not archive the card", () => {
    renderAction({ canArchive: false });
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  /** Scenario: A reviewer sees no archive control */
  it("shows no restore to a caller who may not archive the card", () => {
    renderAction({ canArchive: false }, true);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  /** Scenario: A card an autopilot run still needs cannot be archived */
  it("disables archive with the reason while an autopilot run needs the card", () => {
    renderAction({ archiveRefusal: "autopilot" });

    const button = screen.getByRole("button", { name: labels.archive });
    expect(button).toBeDisabled();
    expect(button).toHaveAccessibleDescription(labels.autopilot);
  });

  /** Scenario: A published card has no archive control */
  it("shows no control on a published card", () => {
    renderAction({ archiveRefusal: "published" });

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  /** Scenario: The archived board lists archived carousels with restore */
  it("restores an archived carousel and refreshes the board", async () => {
    respond(true);
    const onChanged = renderAction({}, true);

    fireEvent.click(screen.getByRole("button", { name: labels.restore }));

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

    fireEvent.click(screen.getByRole("button", { name: labels.archive }));
    fireEvent.click(screen.getByRole("button", { name: labels.confirmYes }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      labels.archiveFailed,
    );
    expect(onChanged).not.toHaveBeenCalled();
  });

  /** Scenario: A failed archive or restore says so on its card */
  it("says when the restore failed", async () => {
    respond(false);
    const onChanged = renderAction({}, true);

    fireEvent.click(screen.getByRole("button", { name: labels.restore }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      labels.restoreFailed,
    );
    expect(onChanged).not.toHaveBeenCalled();
  });
});
