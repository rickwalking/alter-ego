/**
 * Gherkin: tests/features/last-active-admin-guard-ae0585.feature
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import { EditUserDialog } from "./edit-user-dialog";
import { UserTable } from "./user-table";

const ADMIN = {
  id: "a1",
  email: "admin@example.com",
  full_name: "Only Admin",
  role: "admin",
  is_active: true,
  created_at: "2026-10-01T00:00:00Z",
};
const EDITOR = {
  ...ADMIN,
  id: "e1",
  email: "editor@example.com",
  full_name: "Some Editor",
  role: "editor",
};
const LOCKED = en.admin.lastActiveAdminLocked;
const LAST_ADMIN_API_DETAIL = "Cannot deactivate the last active admin";

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** The role select and active checkbox of the open edit dialog. */
function controls(): { role: HTMLElement; active: HTMLElement } {
  const dialog = within(screen.getByRole("dialog"));
  return {
    role: dialog.getByLabelText("Role"),
    active: dialog.getByLabelText("Active"),
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("edit dialog of the last active admin", () => {
  // Scenario: The role and active controls are locked for the last active admin
  it("disables the role and active controls and explains why", () => {
    render(
      <EditUserDialog
        user={ADMIN}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
        isLastActiveAdmin
      />,
    );

    const { role, active } = controls();
    const hint = screen.getByText(LOCKED);
    expect(role).toBeDisabled();
    expect(active).toBeDisabled();
    expect(role).toHaveAttribute("aria-describedby", hint.id);
    expect(active).toHaveAttribute("aria-describedby", hint.id);
    expect(screen.getByLabelText("Full name")).toBeEnabled();
  });

  // Scenario: The role and active controls are locked for the last active admin
  it("has the explanation in Portuguese too", () => {
    expect(pt.admin.lastActiveAdminLocked).toBeTruthy();
    expect(pt.admin.lastActiveAdminLocked).not.toBe(LOCKED);
    expect(pt.admin.lastAdminError).toBeTruthy();
  });

  // Scenario: The controls stay enabled when another admin is active
  it("keeps the controls enabled when the user is not the last active admin", () => {
    render(
      <EditUserDialog user={ADMIN} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );

    const { role, active } = controls();
    expect(role).toBeEnabled();
    expect(active).toBeEnabled();
    expect(role).not.toHaveAttribute("aria-describedby");
    expect(screen.queryByText(LOCKED)).not.toBeInTheDocument();
  });

  // Scenario: A last-admin refusal from the API shows a translated message
  it("shows the translated last-admin message for a 409, never the API text", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse(
            { detail: LAST_ADMIN_API_DETAIL, code: "last_admin" },
            409,
          ),
        ),
    );
    const user = userEvent.setup();
    render(
      <EditUserDialog user={ADMIN} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );

    await user.click(screen.getByLabelText("Active"));
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(
      await screen.findByText(en.admin.lastAdminError),
    ).toBeInTheDocument();
    expect(screen.queryByText(LAST_ADMIN_API_DETAIL)).not.toBeInTheDocument();
  });
});

describe("users table and page", () => {
  // Scenario: The role and active controls are locked for the last active admin
  it("locks the dialog of the row whose id is the last active admin", async () => {
    const user = userEvent.setup();
    render(
      <UserTable
        users={[ADMIN, EDITOR]}
        onRefresh={vi.fn()}
        lastActiveAdminId={ADMIN.id}
      />,
    );

    const adminRow = screen.getByText("Only Admin").closest("tr");
    expect(adminRow).not.toBeNull();
    await user.click(
      within(adminRow as HTMLElement).getByRole("button", { name: "Edit" }),
    );

    expect(controls().role).toBeDisabled();
    expect(controls().active).toBeDisabled();
  });

  // Scenario: Other users keep their controls
  it("leaves the dialog of an editor unlocked", async () => {
    const user = userEvent.setup();
    render(
      <UserTable
        users={[ADMIN, EDITOR]}
        onRefresh={vi.fn()}
        lastActiveAdminId={ADMIN.id}
      />,
    );

    const editorRow = screen.getByText("Some Editor").closest("tr");
    await user.click(
      within(editorRow as HTMLElement).getByRole("button", { name: "Edit" }),
    );

    expect(controls().role).toBeEnabled();
    expect(controls().active).toBeEnabled();
    expect(screen.queryByText(LOCKED)).not.toBeInTheDocument();
  });
});
