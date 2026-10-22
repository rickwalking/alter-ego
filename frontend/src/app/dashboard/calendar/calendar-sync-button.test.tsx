/**
 * Scenarios: tests/features/calendar-sync.feature.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import pt from "@/i18n/locales/pt.json";
import { CalendarSyncButton } from "./calendar-sync-button";

describe("CalendarSyncButton", () => {
  // Scenario: Sync is labelled in the active locale
  it("has Portuguese labels", () => {
    expect(pt.workflow.calendar.sync).toEqual({
      button: "Sincronizar",
      syncing: "Sincronizando…",
      syncedAt: "Sincronizado às {time}",
    });
  });

  it("syncs on press", async () => {
    const onSync = vi.fn();
    render(
      <CalendarSyncButton syncing={false} syncedAt={null} onSync={onSync} />,
    );
    await userEvent.setup().click(screen.getByRole("button", { name: "Sync" }));
    expect(onSync).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
  });

  // Scenario: Sync shows that it is running
  it("is busy and disabled while syncing", () => {
    render(<CalendarSyncButton syncing syncedAt={null} onSync={vi.fn()} />);
    const button = screen.getByRole("button", { name: "Syncing…" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });

  // Scenario: A finished sync shows when it happened
  it("shows the local time of the last sync", () => {
    render(
      <CalendarSyncButton
        syncing={false}
        syncedAt={new Date(2026, 9, 22, 14, 5)}
        onSync={vi.fn()}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Synced at 2:05 PM");
  });
});
